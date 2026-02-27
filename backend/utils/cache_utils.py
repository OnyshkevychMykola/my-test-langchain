"""
Кешування та rate limiting для tabletki.ua скрапінгу.
Забезпечує етичне використання ресурсів та швидкий доступ до даних.
"""
import hashlib
import json
import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from functools import wraps

logger = logging.getLogger(__name__)

# Конфігурація кешу
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
CACHE_EXPIRY_MINUTES = 30
MAX_CACHE_SIZE_MB = 50

# Rate limiting конфігурація  
RATE_LIMIT_REQUESTS_PER_MINUTE = 10
RATE_LIMIT_MIN_DELAY_SECONDS = 3

class CacheManager:
    """Менеджер кешування для результатів пошуку аптек"""
    
    def __init__(self):
        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)
        self._cleanup_old_cache()
    
    def _get_cache_key(self, drug_name: str, user_lat: Optional[float] = None, 
                      user_lng: Optional[float] = None) -> str:
        """Генерація ключа кешу для запиту"""
        key_data = f"{drug_name}:{user_lat}:{user_lng}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cache_file(self, cache_key: str) -> Path:
        """Отримання шляху до файлу кешу"""
        return self.cache_dir / f"pharmacy_cache_{cache_key}.json"
    
    def get(self, drug_name: str, user_lat: Optional[float] = None, 
           user_lng: Optional[float] = None) -> Optional[Dict]:
        """Отримання даних з кешу"""
        try:
            cache_key = self._get_cache_key(drug_name, user_lat, user_lng)
            cache_file = self._get_cache_file(cache_key)
            
            if not cache_file.exists():
                return None
            
            # Перевірка терміну дії
            file_age = time.time() - cache_file.stat().st_mtime
            if file_age > CACHE_EXPIRY_MINUTES * 60:
                cache_file.unlink()  # Видаляємо застарілий кеш
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                
            logger.info(f"Кеш знайдено для {drug_name}")
            return cached_data
            
        except Exception as e:
            logger.error(f"Помилка читання кешу: {e}")
            return None
    
    def set(self, drug_name: str, data: Dict, user_lat: Optional[float] = None,
           user_lng: Optional[float] = None):
        """Збереження даних в кеш"""
        try:
            cache_key = self._get_cache_key(drug_name, user_lat, user_lng)
            cache_file = self._get_cache_file(cache_key)
            
            # Додаємо метадані до кешованих даних
            cached_data = {
                'timestamp': datetime.now().isoformat(),
                'drug_name': drug_name,
                'user_location': {'lat': user_lat, 'lng': user_lng} if user_lat and user_lng else None,
                'data': data
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cached_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Дані закешовано для {drug_name}")
            
        except Exception as e:
            logger.error(f"Помилка збереження кешу: {e}")
    
    def _cleanup_old_cache(self):
        """Видалення застарілих файлів кешу"""
        try:
            if not self.cache_dir.exists():
                return
                
            current_time = time.time()
            total_size = 0
            
            cache_files = list(self.cache_dir.glob("pharmacy_cache_*.json"))
            
            # Видаляємо застарілі файли
            for cache_file in cache_files:
                file_age = current_time - cache_file.stat().st_mtime
                file_size = cache_file.stat().st_size
                total_size += file_size
                
                if file_age > CACHE_EXPIRY_MINUTES * 60:
                    cache_file.unlink()
                    logger.debug(f"Видалено застарілий кеш: {cache_file.name}")
            
            # Перевірка розміру кешу
            if total_size > MAX_CACHE_SIZE_MB * 1024 * 1024:
                logger.warning(f"Кеш перевищує {MAX_CACHE_SIZE_MB}MB, рекомендується очистка")
                
        except Exception as e:
            logger.error(f"Помилка очистки кешу: {e}")

class RateLimiter:
    """Rate limiter для контролю частоти запитів"""
    
    def __init__(self):
        self.request_times = []
        self.last_request_time = 0
    
    def wait_if_needed(self):
        """Очікування якщо потрібно дотримання rate limit"""
        current_time = time.time()
        
        # Видаляємо запити старші за хвилину
        minute_ago = current_time - 60
        self.request_times = [t for t in self.request_times if t > minute_ago]
        
        # Перевіряємо ліміт запитів за хвилину
        if len(self.request_times) >= RATE_LIMIT_REQUESTS_PER_MINUTE:
            sleep_time = 60 - (current_time - self.request_times[0]) + 1
            logger.warning(f"Досягнуто ліміт запитів, очікування {sleep_time:.1f} секунд")
            time.sleep(sleep_time)
            current_time = time.time()
        
        # Перевіряємо мінімальну затримку
        time_since_last = current_time - self.last_request_time
        if time_since_last < RATE_LIMIT_MIN_DELAY_SECONDS:
            sleep_time = RATE_LIMIT_MIN_DELAY_SECONDS - time_since_last
            time.sleep(sleep_time)
            current_time = time.time()
        
        # Реєструємо запит
        self.request_times.append(current_time)
        self.last_request_time = current_time

# Глобальні екземпляри
cache_manager = CacheManager()
rate_limiter = RateLimiter()

def cached_pharmacy_search(cache_enabled: bool = True):
    """Декоратор для кешування результатів пошуку аптек"""
    def decorator(func):
        @wraps(func)
        def wrapper(drug_name: str, user_lat: Optional[float] = None, 
                   user_lng: Optional[float] = None, *args, **kwargs):
            
            # Спробуємо отримати з кешу
            if cache_enabled:
                cached_result = cache_manager.get(drug_name, user_lat, user_lng)
                if cached_result:
                    return cached_result['data']
            
            # Rate limiting перед запитом
            rate_limiter.wait_if_needed()
            
            # Виконуємо функцію
            result = func(drug_name, user_lat, user_lng, *args, **kwargs)
            
            # Кешуємо результат
            if cache_enabled and result:
                cache_manager.set(drug_name, result, user_lat, user_lng)
            
            return result
        return wrapper
    return decorator

def clear_pharmacy_cache():
    """Очистка всього кешу аптек"""
    try:
        if CACHE_DIR.exists():
            for cache_file in CACHE_DIR.glob("pharmacy_cache_*.json"):
                cache_file.unlink()
            logger.info("Кеш аптек очищено")
        return True
    except Exception as e:
        logger.error(f"Помилка очистки кешу: {e}")
        return False

def get_cache_stats() -> Dict:
    """Статистика використання кешу"""
    try:
        if not CACHE_DIR.exists():
            return {"files": 0, "total_size_mb": 0, "status": "no_cache_dir"}
        
        cache_files = list(CACHE_DIR.glob("pharmacy_cache_*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        # Аналіз віку файлів
        current_time = time.time()
        fresh_files = 0
        expired_files = 0
        
        for cache_file in cache_files:
            file_age = current_time - cache_file.stat().st_mtime
            if file_age <= CACHE_EXPIRY_MINUTES * 60:
                fresh_files += 1
            else:
                expired_files += 1
        
        return {
            "files": len(cache_files),
            "fresh_files": fresh_files,
            "expired_files": expired_files,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "expiry_minutes": CACHE_EXPIRY_MINUTES,
            "status": "active"
        }
        
    except Exception as e:
        return {"error": str(e), "status": "error"}

# Функція для налаштування логування rate limiter'а
def setup_rate_limit_logging():
    """Налаштування логування для rate limiter"""
    logging.getLogger('utils.cache_utils').setLevel(logging.INFO)