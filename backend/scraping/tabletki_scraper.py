"""
Веб-скрапер для tabletki.ua - пошук препаратів та цін в аптеках.
Використовує консервативний rate limiting та кешування для етичного скрапінгу.
"""
import re
import time
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

from utils.cache_utils import cached_pharmacy_search, rate_limiter

logger = logging.getLogger(__name__)

class TabletkiScraper:
    """Скрапер для отримання цін препаратів з tabletki.ua"""
    
    BASE_URL = "https://tabletki.ua"
    SEARCH_URL = "https://tabletki.ua/uk/{drug_name}/"
    PRICES_URL = "https://tabletki.ua/uk/{drug_name}/pharmacy/київ/"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'uk-UA,uk;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.last_request_time = 0
        self.min_delay = 3  # мінімум 3 секунди між запитами

    def _rate_limit(self):
        """Дотримання rate limiting - мінімум 3 секунди між запитами"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _make_request(self, url: str, timeout: int = 10) -> Optional[requests.Response]:
        """Безпечний HTTP запит з rate limiting"""
        try:
            self._rate_limit()
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка запиту до {url}: {e}")
            return None

    def _normalize_drug_name(self, drug_name: str) -> str:
        """Нормалізація назви препарату для URL"""
        # Видалити зайві символи, залишити тільки букви, цифри, дефіси
        normalized = re.sub(r'[^\w\s\-]', '', drug_name.strip())
        # Замінити пробіли на дефіси
        normalized = re.sub(r'\s+', '-', normalized)
        # URL encoding для кириличних символів
        return quote(normalized.lower())

    def search_drug(self, drug_name: str) -> Optional[str]:
        """
        Пошук препарату за назвою, повертає URL сторінки з цінами
        
        Args:
            drug_name: Назва препарату
            
        Returns:
            URL сторінки з цінами в аптеках або None якщо не знайдено
        """
        normalized_name = self._normalize_drug_name(drug_name)
        search_url = self.SEARCH_URL.format(drug_name=normalized_name)
        
        logger.info(f"Пошук препарату: {drug_name} -> {search_url}")
        
        response = self._make_request(search_url)
        if not response:
            return None
            
        # Перевіряємо чи знайдено препарат (чи не редирект на головну)
        if "tabletki.ua/uk/" not in response.url or response.url.endswith("tabletki.ua/uk/"):
            logger.warning(f"Препарат '{drug_name}' не знайдено")
            return None
            
        # Формуємо URL сторінки з цінами
        prices_url = self.PRICES_URL.format(drug_name=normalized_name)
        return prices_url

    def get_pharmacy_prices(self, prices_url: str) -> List[Dict]:
        """
        Отримання цін препарату в аптеках Києва
        
        Args:
            prices_url: URL сторінки з цінами
            
        Returns:
            List[Dict] з інформацією про аптеки та ціни
        """
        response = self._make_request(prices_url)
        if not response:
            return []
            
        soup = BeautifulSoup(response.content, 'html.parser')
        return self._parse_pharmacy_data(soup)

    def _parse_pharmacy_data(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Парсинг HTML з даними про аптеки та ціни
        
        Args:
            soup: Parsed HTML
            
        Returns:
            List[Dict] з даними аптек
        """
        pharmacies = []
        
        # Шукаємо контейнери з аптеками
        pharmacy_items = soup.find_all(['div', 'li'], class_=re.compile(r'pharmacy|price|offer'))
        
        for item in pharmacy_items:
            pharmacy_data = self._extract_pharmacy_info(item)
            if pharmacy_data:
                pharmacies.append(pharmacy_data)
                
        # Якщо не знайшли стандартні селектори, пробуємо альтернативні
        if not pharmacies:
            pharmacies = self._parse_alternative_format(soup)
            
        logger.info(f"Знайдено аптек: {len(pharmacies)}")
        return pharmacies

    def _extract_pharmacy_info(self, item) -> Optional[Dict]:
        """Витягування інформації про аптеку з HTML елемента"""
        try:
            # Пошук назви аптеки
            name_elem = item.find(attrs={'data-name': True}) or \
                       item.find(class_=re.compile(r'pharmacy.?name|name')) or \
                       item.find('h3') or item.find('h4')
            
            if not name_elem:
                return None
                
            name = name_elem.get('data-name') or name_elem.get_text(strip=True)
            
            # Пошук координат
            location_elem = item.find(attrs={'data-location': True})
            lat, lng = None, None
            
            if location_elem and location_elem.get('data-location'):
                try:
                    coords = location_elem.get('data-location').split(',')
                    if len(coords) == 2:
                        lat, lng = float(coords[0]), float(coords[1])
                except (ValueError, IndexError):
                    pass
            
            # Пошук ціни
            price_elem = item.find(class_=re.compile(r'price')) or \
                        item.find(attrs=re.compile(r'price', re.I))
            
            price = None
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'(\d+(?:\.\d+)?)', price_text.replace(',', '.'))
                if price_match:
                    price = float(price_match.group(1))
            
            # Пошук адреси
            address_elem = item.find(class_=re.compile(r'address|addr')) or \
                          item.find(attrs=re.compile(r'addr', re.I))
            
            address = address_elem.get_text(strip=True) if address_elem else None
            
            # Пошук статусу наявності
            availability_elem = item.find(class_=re.compile(r'availability|stock|status'))
            availability = availability_elem.get_text(strip=True) if availability_elem else "уточнити"
            
            if not name:
                return None
                
            return {
                'name': name,
                'latitude': lat,
                'longitude': lng,
                'price': price,
                'address': address,
                'availability': availability,
                'raw_html': str(item)[:500]  # для debugging
            }
            
        except Exception as e:
            logger.error(f"Помилка парсингу аптеки: {e}")
            return None

    def _parse_alternative_format(self, soup: BeautifulSoup) -> List[Dict]:
        """Альтернативний парсер якщо основний не спрацював"""
        pharmacies = []
        
        # Пробуємо знайти таблицю з цінами
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')[1:]  # Skip header
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    name = cells[0].get_text(strip=True)
                    price_text = cells[1].get_text(strip=True)
                    
                    price_match = re.search(r'(\d+(?:\.\d+)?)', price_text.replace(',', '.'))
                    price = float(price_match.group(1)) if price_match else None
                    
                    if name and price:
                        pharmacies.append({
                            'name': name,
                            'latitude': None,
                            'longitude': None, 
                            'price': price,
                            'address': None,
                            'availability': 'уточнити'
                        })
        
        return pharmacies

    @cached_pharmacy_search(cache_enabled=True)
    def search_drug_with_prices(self, drug_name: str, user_lat: Optional[float] = None, 
                               user_lng: Optional[float] = None) -> Tuple[Optional[str], List[Dict]]:
        """
        Комплексний пошук - знаходить препарат та отримує ціни
        
        Returns:
            Tuple[drug_url, pharmacies_list]
        """
        prices_url = self.search_drug(drug_name)
        if not prices_url:
            return None, []
            
        pharmacies = self.get_pharmacy_prices(prices_url)
        return prices_url, pharmacies


# Глобальний екземпляр для повторного використання
scraper = TabletkiScraper()