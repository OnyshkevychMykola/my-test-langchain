"""
Геоутиліти для розрахунку відстаней та фільтрації аптек за радіусом.
Використовує формулу haversine для точного розрахунку відстані.
"""
import math
from typing import List, Dict, Optional, Tuple

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Розрахунок відстані між двома точками за формулою haversine
    
    Args:
        lat1, lng1: Координати першої точки
        lat2, lng2: Координати другої точки
        
    Returns:
        Відстань у метрах
    """
    if None in (lat1, lng1, lat2, lng2):
        return float('inf')  # Якщо координати відсутні
    
    # Радіус Землі в метрах
    R = 6371000
    
    # Перетворення градусів у радіани
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    # Формула haversine
    a = (math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lng / 2) * math.sin(delta_lng / 2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance

def filter_pharmacies_by_distance(
    pharmacies: List[Dict], 
    user_lat: float, 
    user_lng: float,
    max_distance_km: float = 2
) -> List[Dict]:
    """
    Фільтрація аптек за радіусом від користувача
    
    Args:
        pharmacies: Список аптек з координатами
        user_lat, user_lng: Координати користувача
        max_distance_km: Максимальна відстань в кілометрах
        
    Returns:
        Відфільтрований список аптек з додатковим полем distance_m
    """
    max_distance_m = max_distance_km * 1000
    filtered_pharmacies = []
    
    for pharmacy in pharmacies:
        if not pharmacy.get('latitude') or not pharmacy.get('longitude'):
            # Аптеки без координат додаємо в кінець зі спеціальною відміткою
            pharmacy['distance_m'] = float('inf')
            pharmacy['distance_note'] = 'координати невідомі'
            continue
            
        distance = calculate_distance(
            user_lat, user_lng,
            pharmacy['latitude'], pharmacy['longitude']
        )
        
        if distance <= max_distance_m:
            pharmacy['distance_m'] = round(distance)
            pharmacy['distance_km'] = round(distance / 1000, 2)
            filtered_pharmacies.append(pharmacy)
    
    # Сортуємо за відстанню
    filtered_pharmacies.sort(key=lambda x: x['distance_m'])
    
    return filtered_pharmacies

def sort_pharmacies_by_distance_and_price(pharmacies: List[Dict]) -> List[Dict]:
    """
    Розумне сортування аптек: спочатку за відстанню, потім за ціною
    
    Args:
        pharmacies: Список аптек з distance_m та price
        
    Returns:
        Відсортований список
    """
    def sort_key(pharmacy):
        distance = pharmacy.get('distance_m', float('inf'))
        price = pharmacy.get('price', float('inf'))
        
        # Пріоритет: відстань до 1км - найвищий
        if distance <= 1000:
            priority = 1
        elif distance <= 2000:
            priority = 2
        else:
            priority = 3
            
        return (priority, distance, price)
    
    return sorted(pharmacies, key=sort_key)

def get_pharmacy_locations_summary(pharmacies: List[Dict], user_lat: float, user_lng: float) -> Dict:
    """
    Підсумкова інформація про розташування аптек
    
    Returns:
        Dict з статистикою локацій
    """
    total = len(pharmacies)
    with_coordinates = len([p for p in pharmacies if p.get('latitude') and p.get('longitude')])
    
    distances = []
    for pharmacy in pharmacies:
        if pharmacy.get('latitude') and pharmacy.get('longitude'):
            dist = calculate_distance(
                user_lat, user_lng,
                pharmacy['latitude'], pharmacy['longitude']
            )
            distances.append(dist)
    
    if distances:
        avg_distance = sum(distances) / len(distances)
        min_distance = min(distances)
        max_distance = max(distances)
    else:
        avg_distance = min_distance = max_distance = 0
    
    return {
        'total_pharmacies': total,
        'with_coordinates': with_coordinates,
        'without_coordinates': total - with_coordinates,
        'avg_distance_m': round(avg_distance),
        'min_distance_m': round(min_distance),
        'max_distance_m': round(max_distance),
        'avg_distance_km': round(avg_distance / 1000, 2),
        'min_distance_km': round(min_distance / 1000, 2),
        'max_distance_km': round(max_distance / 1000, 2)
    }

def format_distance(distance_m: float) -> str:
    """Форматування відстані для показу користувачу"""
    if distance_m == float('inf'):
        return "відстань невідома"
    elif distance_m < 1000:
        return f"{int(distance_m)} м"
    else:
        return f"{distance_m / 1000:.1f} км"

def is_within_kyiv_bounds(lat: float, lng: float) -> bool:
    """
    Перевірка чи координати в межах Києва (приблизно)
    
    Args:
        lat, lng: Координати для перевірки
        
    Returns:
        True якщо в межах Києва
    """
    # Приблизні межі Києва
    KYIV_BOUNDS = {
        'north': 50.590,
        'south': 50.213,
        'east': 30.825,
        'west': 30.239
    }
    
    return (KYIV_BOUNDS['south'] <= lat <= KYIV_BOUNDS['north'] and
            KYIV_BOUNDS['west'] <= lng <= KYIV_BOUNDS['east'])

def suggest_search_expansion(pharmacies: List[Dict], user_lat: float, user_lng: float) -> Optional[str]:
    """
    Пропозиції для розширення пошуку якщо мало результатів
    
    Returns:
        Текстова рекомендація або None
    """
    if not pharmacies:
        return "Спробуйте більш загальну назву препарату або зверніться до популярних аптечних мереж"
    
    nearby_count = len([p for p in pharmacies if p.get('distance_m', float('inf')) <= 2000])
    
    if nearby_count == 0:
        return "У радіусі 2км аптек не знайдено. Рекомендуємо звернутися до великих аптечних мереж"
    elif nearby_count < 3:
        return "Знайдено мало аптек поруч. Можливо, варто розглянути доставку або розширити радіус пошуку"
    
    return None