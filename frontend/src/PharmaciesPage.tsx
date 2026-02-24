import { useEffect, useState, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet'
import L from 'leaflet'

// Fix default marker icons broken by Vite/webpack bundling
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
  useEffect(() => {
    map.setView([lat, lon], 15)
  }, [lat, lon, map])
  return null
}

function IconRefresh({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  )
}

function IconMapPin({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  )
}

function IconClock({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )
}

function IconPhone({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
    </svg>
  )
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
      const res = await fetch('https://overpass-api.de/api/interpreter', {
        method: 'POST',
        body: query,
      })
      if (!res.ok) throw new Error('Не вдалося отримати дані аптек')
      const data = await res.json()
      setPharmacies(data.elements || [])
    } catch {
      setPharmacies([])
    } finally {
      setLoadingPharm(false)
    }
  }

  const getLocation = () => {
    if (!navigator.geolocation) {
      setGeoError('Ваш браузер не підтримує геолокацію.')
      return
    }
    setLoadingGeo(true)
    setGeoError(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords
        setLocation({ lat: latitude, lon: longitude })
        setLoadingGeo(false)
        fetchPharmacies(latitude, longitude)
      },
      (err) => {
        setLoadingGeo(false)
        if (err.code === err.PERMISSION_DENIED) {
          setGeoError('Доступ до геолокації заборонено. Дозвольте доступ у налаштуваннях браузера.')
        } else {
          setGeoError('Не вдалося визначити ваше місцезнаходження.')
        }
      },
      { enableHighAccuracy: true, timeout: 10000 }
    )
  }

  useEffect(() => {
    getLocation()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
    const marker = markerRefs.current.get(p.id)
    if (marker) {
      marker.openPopup()
    }
  }

  return (
    <div className="flex h-full bg-slate-100">
      {/* Sidebar */}
      <aside className="w-72 shrink-0 flex flex-col bg-white border-r border-slate-200 shadow-sm">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-slate-800">Аптеки поруч</h2>
            {location && !loadingPharm && (
              <p className="text-xs text-slate-500 mt-0.5">
                Знайдено: {pharmacies.length} у радіусі 2 км
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={getLocation}
            disabled={loadingGeo || loadingPharm}
            title="Оновити"
            className="p-2 rounded-xl text-slate-500 hover:text-primary-600 hover:bg-primary-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <IconRefresh className={`w-4 h-4 ${(loadingGeo || loadingPharm) ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto min-h-0">
          {(loadingGeo || loadingPharm) && (
            <div className="flex flex-col items-center justify-center gap-3 py-12 text-slate-400">
              <span className="w-7 h-7 rounded-full border-2 border-slate-200 border-t-primary-500 animate-spin" />
              <p className="text-xs">{loadingGeo ? 'Визначаємо місцезнаходження...' : 'Шукаємо аптеки...'}</p>
            </div>
          )}

          {geoError && !loadingGeo && (
            <div className="m-3 p-3 bg-red-50 border border-red-100 rounded-xl">
              <p className="text-xs text-red-600 leading-relaxed">{geoError}</p>
              <button
                type="button"
                onClick={getLocation}
                className="mt-2 text-xs text-primary-600 hover:underline cursor-pointer focus:outline-none"
              >
                Спробувати знову
              </button>
            </div>
          )}

          {!loadingGeo && !loadingPharm && !geoError && pharmacies.length === 0 && location && (
            <div className="flex flex-col items-center justify-center gap-2 py-12 text-slate-400 px-4 text-center">
              <IconMapPin className="w-8 h-8 text-slate-300" />
              <p className="text-xs">Аптек поруч не знайдено (у радіусі 2 км)</p>
            </div>
          )}

          {!loadingGeo && !loadingPharm && pharmacies.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => handleListItemClick(p)}
              className={`w-full text-left px-4 py-3 border-b border-slate-50 transition-colors duration-150 cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-inset ${
                selectedId === p.id ? 'bg-primary-50' : 'hover:bg-slate-50'
              }`}
            >
              <p className={`text-sm font-medium truncate ${selectedId === p.id ? 'text-primary-700' : 'text-slate-800'}`}>
                {getPharmacyName(p)}
              </p>
              {getPharmacyAddress(p) && (
                <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1 truncate">
                  <IconMapPin className="w-3 h-3 shrink-0" />
                  {getPharmacyAddress(p)}
                </p>
              )}
              {p.tags?.opening_hours && (
                <p className="text-xs text-slate-400 mt-0.5 flex items-center gap-1 truncate">
                  <IconClock className="w-3 h-3 shrink-0" />
                  {p.tags.opening_hours}
                </p>
              )}
              {p.tags?.phone && (
                <p className="text-xs text-slate-400 mt-0.5 flex items-center gap-1 truncate">
                  <IconPhone className="w-3 h-3 shrink-0" />
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
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-slate-50 z-10">
            <IconMapPin className="w-12 h-12 text-slate-300" />
            <p className="text-slate-500 text-sm">Дозвольте доступ до геолокації, щоб побачити аптеки поруч</p>
            <button
              type="button"
              onClick={getLocation}
              className="px-4 py-2 rounded-xl bg-primary-500 text-white text-sm font-medium hover:bg-primary-600 transition-colors duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
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

            {/* User position */}
            <Circle
              center={[location.lat, location.lon]}
              radius={30}
              pathOptions={{ color: '#3b82f6', fillColor: '#3b82f6', fillOpacity: 0.8 }}
            />
            <Circle
              center={[location.lat, location.lon]}
              radius={2000}
              pathOptions={{ color: '#3b82f6', fillColor: '#3b82f6', fillOpacity: 0.04, weight: 1, dashArray: '6 4' }}
            />

            {/* Pharmacy markers */}
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
                    <p className="font-semibold text-slate-800 text-sm">{getPharmacyName(p)}</p>
                    {getPharmacyAddress(p) && (
                      <p className="text-xs text-slate-500 mt-1">{getPharmacyAddress(p)}</p>
                    )}
                    {p.tags?.opening_hours && (
                      <p className="text-xs text-slate-400 mt-1">
                        <span className="font-medium text-slate-500">Години: </span>
                        {p.tags.opening_hours}
                      </p>
                    )}
                    {p.tags?.phone && (
                      <p className="text-xs text-slate-400 mt-1">
                        <span className="font-medium text-slate-500">Тел: </span>
                        {p.tags.phone}
                      </p>
                    )}
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        )}

        {(loadingGeo || loadingPharm) && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-50/70 z-20">
            <div className="flex flex-col items-center gap-3 bg-white rounded-2xl shadow-lg px-8 py-6">
              <span className="w-8 h-8 rounded-full border-2 border-slate-200 border-t-primary-500 animate-spin" />
              <p className="text-slate-500 text-sm">{loadingGeo ? 'Визначаємо місцезнаходження...' : 'Шукаємо аптеки...'}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
