import { useEffect, useState, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet'
import { RefreshCw, MapPin, Clock, Phone } from 'lucide-react'
import L from 'leaflet'

delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const pharmacyIcon = new L.Icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

interface Pharmacy {
  id: number
  lat: number
  lon: number
  tags: {
    name?: string
    'addr:street'?: string
    'addr:housenumber'?: string
    opening_hours?: string
    phone?: string
  }
}

interface UserLocation {
  lat: number
  lon: number
}

function RecenterMap({ lat, lon }: { lat: number; lon: number }) {
  const map = useMap()
  useEffect(() => { map.setView([lat, lon], 15) }, [lat, lon, map])
  return null
}

const LOCATION_CACHE_KEY = 'pharma_user_location'
const LOCATION_CACHE_TTL = 15 * 60 * 1000

function getCachedLocation(): UserLocation | null {
  try {
    const raw = localStorage.getItem(LOCATION_CACHE_KEY)
    if (!raw) return null
    const { lat, lon, ts } = JSON.parse(raw) as { lat: number; lon: number; ts: number }
    if (Date.now() - ts > LOCATION_CACHE_TTL) { localStorage.removeItem(LOCATION_CACHE_KEY); return null }
    return { lat, lon }
  } catch { return null }
}

function setCachedLocation(lat: number, lon: number) {
  try { localStorage.setItem(LOCATION_CACHE_KEY, JSON.stringify({ lat, lon, ts: Date.now() })) } catch { /* noop */ }
}

export default function PharmaciesPage() {
  const [location, setLocation] = useState<UserLocation | null>(null)
  const [pharmacies, setPharmacies] = useState<Pharmacy[]>([])
  const [loadingGeo, setLoadingGeo] = useState(false)
  const [loadingPharm, setLoadingPharm] = useState(false)
  const [geoError, setGeoError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const markerRefs = useRef<Map<number, L.Marker>>(new Map())

  const fetchPharmacies = async (lat: number, lon: number) => {
    setLoadingPharm(true)
    try {
      const query = `[out:json];node["amenity"="pharmacy"](around:2000,${lat},${lon});out body;`
      const res = await fetch('https://overpass-api.de/api/interpreter', { method: 'POST', body: query })
      if (!res.ok) throw new Error('Не вдалося отримати дані аптек')
      const data = await res.json()
      setPharmacies(data.elements || [])
    } catch { setPharmacies([]) }
    finally { setLoadingPharm(false) }
  }

  const getLocation = (forceRefresh = false) => {
    if (!forceRefresh) {
      const cached = getCachedLocation()
      if (cached) { setLocation(cached); fetchPharmacies(cached.lat, cached.lon); return }
    }
    if (!navigator.geolocation) { setGeoError('Ваш браузер не підтримує геолокацію.'); return }
    setLoadingGeo(true)
    setGeoError(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords
        setCachedLocation(latitude, longitude)
        setLocation({ lat: latitude, lon: longitude })
        setLoadingGeo(false)
        fetchPharmacies(latitude, longitude)
      },
      (err) => {
        setLoadingGeo(false)
        setGeoError(err.code === 1
          ? 'Доступ до геолокації заборонено. Дозвольте доступ у налаштуваннях браузера.'
          : 'Не вдалося визначити ваше місцезнаходження.')
      },
      { enableHighAccuracy: true, timeout: 10000 }
    )
  }

  useEffect(() => { getLocation() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const getPharmacyName = (p: Pharmacy) => p.tags?.name || 'Аптека'
  const getPharmacyAddress = (p: Pharmacy) => {
    const street = p.tags?.['addr:street']
    const num = p.tags?.['addr:housenumber']
    if (street && num) return `${street}, ${num}`
    if (street) return street
    return null
  }

  const handleListItemClick = (p: Pharmacy) => {
    setSelectedId(p.id)
    markerRefs.current.get(p.id)?.openPopup()
  }

  const isLoading = loadingGeo || loadingPharm

  return (
    <div className="flex h-full bg-base">
      {/* Sidebar */}
      <aside className="w-72 shrink-0 flex flex-col bg-surface border-r border-white/5">
        {/* Header */}
        <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-white">Аптеки поруч</h2>
            {location && !loadingPharm && (
              <p className="text-xs text-slate-500 mt-0.5">
                Знайдено: {pharmacies.length} у радіусі 2 км
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() => getLocation(true)}
            disabled={isLoading}
            title="Оновити локацію"
            className="p-2 rounded-xl text-slate-400 hover:text-accent hover:bg-accent/10
                       disabled:opacity-30 disabled:cursor-not-allowed
                       transition-colors duration-200 cursor-pointer
                       focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {isLoading && (
            <div className="flex flex-col items-center justify-center gap-3 py-12 text-slate-500">
              <span className="w-7 h-7 rounded-full border-2 border-white/10 border-t-accent animate-spin" aria-hidden />
              <p className="text-xs">{loadingGeo ? 'Визначаємо місцезнаходження...' : 'Шукаємо аптеки...'}</p>
            </div>
          )}

          {geoError && !loadingGeo && (
            <div className="m-3 p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
              <p className="text-xs text-red-400 leading-relaxed">{geoError}</p>
              <button
                type="button"
                onClick={() => getLocation()}
                className="mt-2 text-xs text-accent hover:underline cursor-pointer focus:outline-none"
              >
                Спробувати знову
              </button>
            </div>
          )}

          {!isLoading && !geoError && pharmacies.length === 0 && location && (
            <div className="flex flex-col items-center gap-2 py-12 text-slate-500 px-4 text-center">
              <MapPin className="w-8 h-8 opacity-40" />
              <p className="text-xs">Аптек поруч не знайдено (у радіусі 2 км)</p>
            </div>
          )}

          {!isLoading && pharmacies.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => handleListItemClick(p)}
              className={`w-full text-left px-4 py-3 border-b border-white/5
                          transition-colors duration-150 cursor-pointer
                          focus:outline-none focus:ring-2 focus:ring-accent focus:ring-inset
                          ${selectedId === p.id
                            ? 'bg-amber-500/15 border-l-2 border-l-amber-400'
                            : 'hover:bg-white/5'
                          }`}
            >
              <p className={`text-sm font-medium truncate ${selectedId === p.id ? 'text-amber-400' : 'text-white'}`}>
                {getPharmacyName(p)}
              </p>
              {getPharmacyAddress(p) && (
                <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1 truncate">
                  <MapPin className="w-3 h-3 shrink-0" />
                  {getPharmacyAddress(p)}
                </p>
              )}
              {p.tags?.opening_hours && (
                <p className="text-xs text-slate-600 mt-0.5 flex items-center gap-1 truncate">
                  <Clock className="w-3 h-3 shrink-0" />
                  {p.tags.opening_hours}
                </p>
              )}
              {p.tags?.phone && (
                <p className="text-xs text-slate-600 mt-0.5 flex items-center gap-1 truncate">
                  <Phone className="w-3 h-3 shrink-0" />
                  {p.tags.phone}
                </p>
              )}
            </button>
          ))}
        </div>
      </aside>

      {/* Map */}
      <div className="flex-1 relative min-w-0">
        {!location && !loadingGeo && !geoError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-base z-10">
            <MapPin className="w-12 h-12 text-slate-600" />
            <p className="text-slate-400 text-sm text-center max-w-xs">
              Дозвольте доступ до геолокації, щоб побачити аптеки поруч
            </p>
            <button
              type="button"
              onClick={() => getLocation()}
              className="px-5 py-2.5 rounded-xl text-white text-sm font-medium
                         focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-base
                         transition-all duration-200 cursor-pointer hover:opacity-90 active:scale-95"
              style={{ background: 'linear-gradient(135deg, #0EA5E9 0%, #06B6D4 100%)' }}
            >
              Визначити моє місцезнаходження
            </button>
          </div>
        )}

        {location && (
          <MapContainer
            center={[location.lat, location.lon]}
            zoom={15}
            style={{ height: '100%', width: '100%' }}
            className="z-0"
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <RecenterMap lat={location.lat} lon={location.lon} />

            <Circle
              center={[location.lat, location.lon]}
              radius={30}
              pathOptions={{ color: '#0EA5E9', fillColor: '#0EA5E9', fillOpacity: 0.9 }}
            />
            <Circle
              center={[location.lat, location.lon]}
              radius={2000}
              pathOptions={{ color: '#0EA5E9', fillColor: '#0EA5E9', fillOpacity: 0.04, weight: 1, dashArray: '6 4' }}
            />

            {pharmacies.map((p) => (
              <Marker
                key={p.id}
                position={[p.lat, p.lon]}
                icon={pharmacyIcon}
                ref={(ref) => {
                  if (ref) markerRefs.current.set(p.id, ref)
                  else markerRefs.current.delete(p.id)
                }}
                eventHandlers={{ click: () => setSelectedId(p.id) }}
              >
                <Popup>
                  <div className="min-w-[160px]">
                    <p className="font-semibold text-sm">{getPharmacyName(p)}</p>
                    {getPharmacyAddress(p) && (
                      <p className="text-xs text-slate-400 mt-1">{getPharmacyAddress(p)}</p>
                    )}
                    {p.tags?.opening_hours && (
                      <p className="text-xs text-slate-400 mt-1">
                        <span className="font-medium text-slate-300">Години: </span>
                        {p.tags.opening_hours}
                      </p>
                    )}
                    {p.tags?.phone && (
                      <p className="text-xs text-slate-400 mt-1">
                        <span className="font-medium text-slate-300">Тел: </span>
                        {p.tags.phone}
                      </p>
                    )}
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        )}

        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-base/70 backdrop-blur-sm z-20">
            <div className="flex flex-col items-center gap-3 glass rounded-2xl px-8 py-6 shadow-card">
              <span className="w-8 h-8 rounded-full border-2 border-white/10 border-t-accent animate-spin" aria-hidden />
              <p className="text-slate-400 text-sm">
                {loadingGeo ? 'Визначаємо місцезнаходження...' : 'Шукаємо аптеки...'}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
