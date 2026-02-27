"""
Fallback дані та логіка для випадків коли tabletki.ua недоступний 
або не знайдено аптек поруч з користувачем.
"""
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Популярні аптечні мережі України
POPULAR_PHARMACY_CHAINS = {
    "АНЦ": {
        "name": "Аптечна мережа АНЦ", 
        "phone": "0 800 500 129",
        "website": "anc.ua",
        "description": "Одна з найбільших аптечних мереж України з понад 1000 відділень",
        "services": ["консультація фармацевта", "доставка", "онлайн замовлення"],
        "coverage": "вся Україна"
    },
    "Аптека Доброго Дня": {
        "name": "Аптека Доброго Дня",
        "phone": "0 800 505 911", 
        "website": "add.ua",
        "description": "Популярна мережа з широким асортиментом та конкурентними цінами",
        "services": ["консультація фармацевта", "програма лояльності", "доставка"],
        "coverage": "великі міста України"
    },
    "Аптека №1": {
        "name": "Аптека №1",
        "phone": "0 800 303 022",
        "website": "apteka1.ua",
        "description": "Надійна аптечна мережа з швидкою доставкою",
        "services": ["доставка до 2 годин", "онлайн консультація", "мобільний додаток"],
        "coverage": "Київ, Харків, Дніпро, Одеса"
    },
    "Бажаємо здоров'я": {
        "name": "Бажаємо здоров'я",
        "phone": "0 800 605 000",
        "website": "bz.ua",  
        "description": "Велика мережа з професійною консультацією фармацевтів",
        "services": ["консультація фармацевта", "рецептурний відділ", "дитячий асортимент"],
        "coverage": "західна та центральна Україна"
    },
    "Копійка": {
        "name": "Аптеки Копійка",
        "phone": "0 800 309 000",
        "website": "kopeyka.ua",
        "description": "Доступні ціни та широкий асортимент лікарських засобів",
        "services": ["низькі ціни", "акції та знижки", "програма лояльності"],
        "coverage": "вся Україна"
    }
}

# Альтернативні онлайн ресурси
ALTERNATIVE_RESOURCES = {
    "tabletki.ua": {
        "name": "Tabletki.ua",
        "url": "https://tabletki.ua",
        "description": "Офіційний каталог ліків та цін в аптеках України",
        "type": "ціни та наявність"
    },
    "liki24.com": {
        "name": "Liki24", 
        "url": "https://liki24.com",
        "description": "Онлайн аптека з доставкою по Україні",
        "type": "онлайн аптека"
    },
    "apteka911.ua": {
        "name": "Аптека 911",
        "url": "https://apteka911.ua", 
        "description": "Пошук ліків та порівняння цін",
        "type": "агрегатор цін"
    },
    "moezdorovie.ua": {
        "name": "Моє здоров'я",
        "url": "https://moezdorovie.ua",
        "description": "Медична інформація та пошук аптек",
        "type": "медична інформація"
    }
}

def get_fallback_recommendations(drug_name: str, reason: str = "no_nearby_pharmacies") -> Dict:
    """
    Генерує fallback рекомендації залежно від причини
    
    Args:
        drug_name: Назва препарату
        reason: Причина fallback ("no_nearby_pharmacies", "drug_not_found", "service_error")
        
    Returns:
        Структуровані рекомендації
    """
    base_recommendations = {
        "drug_name": drug_name,
        "reason": reason,
        "popular_chains": list(POPULAR_PHARMACY_CHAINS.values()),
        "alternative_resources": list(ALTERNATIVE_RESOURCES.values())
    }
    
    if reason == "no_nearby_pharmacies":
        base_recommendations.update({
            "title": "Аптек поруч не знайдено",
            "message": f"У радіусі 2км аптеки з препаратом '{drug_name}' не знайдено.",
            "suggestions": [
                "Зверніться до популярних аптечних мереж за телефоном",
                "Скористайтеся доставкою ліків додому",
                "Розширте радіус пошуку до 5-10 км",
                "Запитайте про аналоги препарату"
            ],
            "priority_chains": ["АНЦ", "Аптека Доброго Дня", "Аптека №1"]
        })
    
    elif reason == "drug_not_found":
        base_recommendations.update({
            "title": "Препарат не знайдено",
            "message": f"Препарат '{drug_name}' не знайдено в каталозі.",
            "suggestions": [
                "Перевірте правильність написання назви препарату",
                "Спробуйте використати торгівельну назву замість МНН",
                "Зверніться до фармацевта для підбору аналогів",
                "Проконсультуйтеся з лікарем щодо альтернатив"
            ],
            "search_tips": [
                "Використовуйте українську транскрипцію",
                "Спробуйте скорочену назву без дозування",
                "Пошукайте за діючою речовиною"
            ]
        })
    
    elif reason == "service_error":
        base_recommendations.update({
            "title": "Тимчасова недоступність сервісу",
            "message": "Наразі неможливо отримати актуальні дані про ціни.",
            "suggestions": [
                "Спробуйте пізніше (через 10-15 хвилин)",
                "Зверніться безпосередньо до аптек",
                "Скористайтеся альтернативними ресурсами",
                "Перевірте офіційні сайти аптечних мереж"
            ],
            "urgent_contacts": [
                "Екстрена медична допомога: 103",
                "Довідкова служба МОЗ: 0 800 505 201"
            ]
        })
    
    return base_recommendations

def get_priority_chains_by_region(region: Optional[str] = None) -> List[str]:
    """
    Повертає пріоритетні мережі для регіону
    
    Args:
        region: Регіон України (None для загального списку)
        
    Returns:
        List назв мереж в порядку пріоритету
    """
    if region and region.lower() in ["київ", "kyiv", "киев"]:
        return ["АНЦ", "Аптека №1", "Аптека Доброго Дня", "Копійка"]
    elif region and region.lower() in ["львів", "lviv", "львов"]:
        return ["Бажаємо здоров'я", "АНЦ", "Аптека Доброго Дня"]
    elif region and region.lower() in ["харків", "kharkiv", "харьков"]:
        return ["Аптека №1", "АНЦ", "Копійка"]
    else:
        return ["АНЦ", "Аптека Доброго Дня", "Аптека №1", "Бажаємо здоров'я", "Копійка"]

def format_chain_contact_info(chain_name: str, include_services: bool = True) -> Dict:
    """
    Форматує контактну інформацію мережі для показу користувачу
    
    Args:
        chain_name: Назва мережі
        include_services: Включати інформацію про послуги
        
    Returns:
        Відформатована інформація
    """
    chain_data = POPULAR_PHARMACY_CHAINS.get(chain_name)
    if not chain_data:
        return {}
    
    formatted = {
        "name": chain_data["name"],
        "phone": chain_data["phone"],
        "website": chain_data["website"],
        "description": chain_data["description"]
    }
    
    if include_services:
        formatted["services"] = chain_data["services"]
        formatted["coverage"] = chain_data["coverage"]
    
    return formatted

def get_emergency_contacts() -> Dict:
    """Контакти для екстрених випадків"""
    return {
        "emergency_medical": {
            "number": "103",
            "description": "Швидка медична допомога"
        },
        "moh_hotline": {
            "number": "0 800 505 201", 
            "description": "Довідкова служба МОЗ України"
        },
        "poison_control": {
            "number": "044 486 22 22",
            "description": "Центр лікування отруєнь (Київ)"
        },
        "pharmacy_duty": {
            "number": "0 800 305 909",
            "description": "Довідка про чергові аптеки"
        }
    }

def should_suggest_emergency_contacts(drug_name: str) -> bool:
    """
    Визначає чи потрібно показувати екстрені контакти
    
    Args:
        drug_name: Назва препарату
        
    Returns:
        True якщо потрібно показати екстрені контакти
    """
    emergency_keywords = [
        "інсулін", "нітрогліцерин", "атропін", "адреналін", "преднізолон",
        "фуросемід", "нітропруссид", "хлорид калію", "глюкоза", "фізрозчин"
    ]
    
    drug_lower = drug_name.lower()
    return any(keyword in drug_lower for keyword in emergency_keywords)

# Функція для логування використання fallback'у
def log_fallback_usage(drug_name: str, reason: str, user_location: Optional[Dict] = None):
    """Логування використання fallback логіки для аналітики"""
    logger.info(f"Fallback usage: drug='{drug_name}', reason='{reason}', location={user_location}")