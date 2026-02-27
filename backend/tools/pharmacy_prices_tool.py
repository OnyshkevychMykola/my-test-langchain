"""
LangChain інструмент для пошуку цін препаратів в аптеках через tabletki.ua.
Інтегрується з медичним агентом для надання інформації про ціни та доступність ліків.
"""
import json
import logging
from typing import Optional, Dict, List

from langchain.tools import tool

from scraping.tabletki_scraper import scraper
from utils.geo_utils import (
    filter_pharmacies_by_distance,
    sort_pharmacies_by_distance_and_price,
    format_distance,
    suggest_search_expansion,
    get_pharmacy_locations_summary
)
from utils.fallback_data import (
    get_fallback_recommendations,
    log_fallback_usage,
    should_suggest_emergency_contacts,
    get_emergency_contacts
)

logger = logging.getLogger(__name__)

@tool
def pharmacy_prices_lookup(
    drug_name: str, 
    user_latitude: Optional[float] = None, 
    user_longitude: Optional[float] = None
) -> str:
    """
    Знайти ціни препарату в аптеках поруч з користувачем (до 2км від локації).
    
    Args:
        drug_name: Назва препарату для пошуку (наприклад: "амізон", "парацетамол")
        user_latitude: Широта користувача (опціонально для геофільтрації)  
        user_longitude: Довгота користувача (опціонально для геофільтрації)
        
    Returns:
        Структурована інформація про ціни препарату в аптеках у форматі JSON
    """
    try:
        # Логування запиту
        logger.info(f"Пошук цін для препарату: {drug_name}")
        
        # Пошук препарату та отримання цін
        drug_url, pharmacies = scraper.search_drug_with_prices(drug_name)
        
        if not drug_url:
            return _format_not_found_response(drug_name)
        
        if not pharmacies:
            return _format_no_prices_response(drug_name)
        
        # Фільтрація за геолокацією якщо є координати
        if user_latitude and user_longitude:
            nearby_pharmacies = filter_pharmacies_by_distance(
                pharmacies, user_latitude, user_longitude, max_distance_km=2
            )
            
            if not nearby_pharmacies:
                # Якщо поруч нічого немає - повертаємо fallback
                return _format_fallback_response(drug_name, user_latitude, user_longitude)
            
            # Сортуємо за відстанню та ціною
            pharmacies = sort_pharmacies_by_distance_and_price(nearby_pharmacies)
            
            # Обмежуємо до топ-5
            pharmacies = pharmacies[:5]
            
            return _format_success_response(
                drug_name, pharmacies, user_latitude, user_longitude, 
                nearby_search=True
            )
        else:
            # Без геолокації - просто топ-5 за ціною
            pharmacies = sorted([p for p in pharmacies if p.get('price')], 
                              key=lambda x: x['price'])[:5]
            
            return _format_success_response(
                drug_name, pharmacies, None, None, nearby_search=False
            )
            
    except Exception as e:
        logger.error(f"Помилка пошуку цін для {drug_name}: {e}")
        return _format_error_response(drug_name, str(e))

def _format_success_response(
    drug_name: str, 
    pharmacies: List[Dict],
    user_lat: Optional[float],
    user_lng: Optional[float], 
    nearby_search: bool
) -> str:
    """Форматування успішної відповіді з результатами"""
    
    result = {
        "status": "success",
        "product": {
            "name": drug_name,
            "found": True
        },
        "search_type": "поруч з користувачем" if nearby_search else "загальний пошук",
        "pharmacies_found": len(pharmacies),
        "offers": []
    }
    
    if nearby_search and user_lat and user_lng:
        result["search_location"] = {
            "lat": user_lat,
            "lng": user_lng
        }
        result["radius_km"] = 2
    
    # Форматування інформації про аптеки
    for pharmacy in pharmacies:
        offer = {
            "pharmacy": {
                "name": pharmacy.get('name', 'Назва невідома'),
                "address": pharmacy.get('address') or 'Адреса уточнюється'
            }
        }
        
        if pharmacy.get('price'):
            offer["price_uah"] = pharmacy['price']
        
        if pharmacy.get('distance_m') is not None and pharmacy['distance_m'] != float('inf'):
            offer["distance"] = format_distance(pharmacy['distance_m'])
            offer["distance_m"] = pharmacy['distance_m']
        
        if pharmacy.get('availability'):
            offer["availability"] = pharmacy['availability']
        
        result["offers"].append(offer)
    
    # Додаємо disclaimer
    result["disclaimer"] = "Ціни орієнтовні. Рекомендуємо уточнити наявність та ціну в аптеці перед візитом. Це не є заміною консультації з лікарем."
    
    return json.dumps(result, ensure_ascii=False, indent=2)

def _format_fallback_response(drug_name: str, user_lat: float, user_lng: float) -> str:
    """Відповідь з популярними мережами якщо поруч нічого не знайдено"""
    
    # Логування fallback використання
    log_fallback_usage(drug_name, "no_nearby_pharmacies", {"lat": user_lat, "lng": user_lng})
    
    # Отримуємо fallback рекомендації
    recommendations = get_fallback_recommendations(drug_name, "no_nearby_pharmacies")
    
    result = {
        "status": "fallback",
        "product": {
            "name": drug_name,
            "found": True
        },
        "message": recommendations["message"],
        "search_location": {
            "lat": user_lat,
            "lng": user_lng  
        },
        "radius_km": 2,
        "fallback_used": True,
        "suggestions": recommendations["suggestions"],
        "popular_chains": [
            {
                "name": chain["name"],
                "phone": chain["phone"],
                "website": chain["website"], 
                "description": chain["description"],
                "services": chain.get("services", [])
            }
            for chain in recommendations["popular_chains"]
        ],
        "alternative_resources": recommendations["alternative_resources"]
    }
    
    # Додаємо екстрені контакти для критичних препаратів
    if should_suggest_emergency_contacts(drug_name):
        result["emergency_contacts"] = get_emergency_contacts()
        result["urgent_note"] = "⚠️ Це може бути життєво важливий препарат. За потреби зверніться до екстрених служб."
    
    result["disclaimer"] = "Інформація про аптечні мережі довідкова. Рекомендуємо зателефонувати для уточнення наявності препарату. Це не є заміною консультації з лікарем."
    
    return json.dumps(result, ensure_ascii=False, indent=2)

def _format_not_found_response(drug_name: str) -> str:
    """Відповідь коли препарат не знайдено"""
    
    # Логування та отримання рекомендацій
    log_fallback_usage(drug_name, "drug_not_found") 
    recommendations = get_fallback_recommendations(drug_name, "drug_not_found")
    
    result = {
        "status": "not_found",
        "product": {
            "name": drug_name,
            "found": False
        },
        "message": recommendations["message"],
        "suggestions": recommendations["suggestions"],
        "search_tips": recommendations["search_tips"],
        "popular_chains": [
            {
                "name": chain["name"],
                "phone": chain["phone"],
                "description": f"{chain['description']} - зверніться для пошуку аналогів"
            }
            for chain in recommendations["popular_chains"][:3]  # Топ-3 мережі
        ],
        "alternative_resources": recommendations["alternative_resources"]
    }
    
    # Екстрені контакти для критичних препаратів
    if should_suggest_emergency_contacts(drug_name):
        result["emergency_contacts"] = get_emergency_contacts()
        result["urgent_note"] = "⚠️ Якщо це життєво важливий препарат, зверніться до екстрених служб."
    
    result["disclaimer"] = "Відсутність препарату в пошуку не означає, що його немає в аптеках. Рекомендуємо консультацію з фармацевтом або лікарем."
    
    return json.dumps(result, ensure_ascii=False, indent=2)

def _format_no_prices_response(drug_name: str) -> str:
    """Відповідь коли препарат знайдено, але немає цін"""
    
    # Логування 
    log_fallback_usage(drug_name, "no_prices_available")
    
    # Використовуємо fallback для отримання рекомендацій (схожий на service_error)
    recommendations = get_fallback_recommendations(drug_name, "service_error")
    
    result = {
        "status": "no_prices", 
        "product": {
            "name": drug_name,
            "found": True
        },
        "message": f"Препарат '{drug_name}' знайдено, але актуальні ціни відсутні.",
        "suggestions": [
            "Зверніться безпосередньо до аптек для уточнення ціни",
            "Перевірте наявність на офіційних сайтах аптечних мереж",
            "Запитайте про програми знижок та акції"
        ],
        "popular_chains": [
            {
                "name": chain["name"],
                "phone": chain["phone"],
                "website": chain["website"],
                "services": chain.get("services", [])
            }
            for chain in recommendations["popular_chains"]
        ],
        "alternative_resources": recommendations["alternative_resources"]
    }
    
    result["disclaimer"] = "Рекомендуємо уточнити актуальну ціну та наявність безпосередньо в аптеці. Це не є заміною консультації з лікарем."
    
    return json.dumps(result, ensure_ascii=False, indent=2)

def _format_error_response(drug_name: str, error: str) -> str:
    """Відповідь при технічній помилці"""
    
    # Логування та отримання рекомендацій
    log_fallback_usage(drug_name, "service_error")
    recommendations = get_fallback_recommendations(drug_name, "service_error")
    
    result = {
        "status": "error", 
        "product": {
            "name": drug_name,
            "found": False
        },
        "message": recommendations["message"],
        "error_details": error if "timeout" in error.lower() or "connection" in error.lower() else "Технічна помилка",
        "suggestions": recommendations["suggestions"],
        "popular_chains": [
            {
                "name": chain["name"],
                "phone": chain["phone"],
                "website": chain["website"]
            }
            for chain in recommendations["popular_chains"][:4]
        ],
        "alternative_resources": recommendations["alternative_resources"]
    }
    
    # Єдиний формат екстрених контактів (як у no_nearby_pharmacies / drug_not_found)
    result["emergency_contacts"] = get_emergency_contacts()
    if should_suggest_emergency_contacts(drug_name):
        result["urgent_note"] = "⚠️ Якщо препарат невідкладно потрібен, зверніться до екстрених служб."
    
    result["disclaimer"] = "Технічні помилки тимчасові. За невідкладної потреби зверніться безпосередньо до аптек або медичних служб."
    
    return json.dumps(result, ensure_ascii=False, indent=2)