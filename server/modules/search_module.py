import asyncio
import logging
from typing import Dict, Any, List, Optional
import urllib.parse
import re
from datetime import datetime

from modules.api_module import get_api_module

logger = logging.getLogger(__name__)

# Required plugin functions
def get_functions() -> List[Dict[str, Any]]:
    """Zwraca listę dostępnych funkcji w pluginie."""
    return [
        {
            "name": "search",
            "description": "Wyszukuje informacje w internecie",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Zapytanie do wyszukania"
                    },
                    "engine": {
                        "type": "string",
                        "description": "Silnik wyszukiwania",
                        "enum": ["duckduckgo", "google", "bing"],
                        "default": "duckduckgo"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maksymalna liczba wyników",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "search_news",
            "description": "Wyszukuje najnowsze wiadomości",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Temat wiadomości do wyszukania"
                    },
                    "language": {
                        "type": "string",
                        "description": "Język wiadomości",
                        "default": "pl"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maksymalna liczba wyników",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20
                    }
                },
                "required": ["query"]
            }
        }
    ]

async def execute_function(function_name: str, parameters: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    """Wykonuje funkcję pluginu."""
    search_module = SearchModule()
    await search_module.initialize()
    
    try:
        if function_name == "search":
            query = parameters.get("query")
            engine = parameters.get("engine", "duckduckgo")
            max_results = parameters.get("max_results", 10)
            
            result = await search_module.search(user_id, query, engine, max_results=max_results)
            return {
                "success": True,
                "data": result,
                "message": f"Wyszukano informacje dla: {query}"
            }
            
        elif function_name == "search_news":
            query = parameters.get("query")
            language = parameters.get("language", "pl")
            max_results = parameters.get("max_results", 5)
            
            # Pobierz API key z konfiguracji użytkownika
            api_key = await search_module._get_user_api_key(user_id, "newsapi")
            if not api_key:
                return {
                    "success": False,
                    "error": "Brak klucza API dla NewsAPI. Skonfiguruj klucz w ustawieniach.",
                    "help": "Potrzebny klucz API z https://newsapi.org"
                }
            
            result = await search_module.search_news(user_id, query, language, max_results, api_key)
            return {
                "success": True,
                "data": result,
                "message": f"Znaleziono najnowsze wiadomości dla: {query}"
            }
            
        else:
            return {
                "success": False,
                "error": f"Unknown function: {function_name}"
            }
            
    except Exception as e:
        logger.error(f"Error executing {function_name}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

class SearchModule:
    """Moduł wyszukiwania informacji w internecie."""
    
    def __init__(self):
        self.api_module = None
        self.search_engines = {
            'duckduckgo': self._search_duckduckgo,
            'google': self._search_google,
            'bing': self._search_bing
        }
        
    async def initialize(self):
        """Inicjalizuje moduł wyszukiwania."""
        self.api_module = await get_api_module()
        logger.info("SearchModule initialized")
    
    async def search(self, user_id: int, query: str, 
                    engine: str = "duckduckgo",
                    api_key: str = None,
                    max_results: int = 10) -> Dict[str, Any]:
        """
        Wykonuje wyszukiwanie w internecie.
        
        Args:
            user_id: ID użytkownika
            query: Zapytanie wyszukiwania
            engine: Silnik wyszukiwania
            api_key: Klucz API (jeśli wymagany)
            max_results: Maksymalna liczba wyników
            
        Returns:
            Wyniki wyszukiwania
        """
        if not self.api_module:
            await self.initialize()
        
        if engine not in self.search_engines:
            return {
                'error': f'Nieobsługiwany silnik wyszukiwania: {engine}',
                'available_engines': list(self.search_engines.keys())
            }
        
        try:
            search_func = self.search_engines[engine]
            results = await search_func(user_id, query, api_key, max_results)
            
            # Dodaj metadane wyszukiwania
            results['search_metadata'] = {
                'query': query,
                'engine': engine,
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Search error with {engine}: {e}")
            return {
                'error': f'Błąd wyszukiwania: {str(e)}',
                'query': query,
                'engine': engine
            }
    
    async def _search_duckduckgo(self, user_id: int, query: str,
                                api_key: str = None, max_results: int = 10) -> Dict[str, Any]:
        """Wyszukiwanie za pomocą DuckDuckGo."""
        
        # DuckDuckGo Instant Answer API
        url = "https://api.duckduckgo.com/"
        params = {
            'q': query,
            'format': 'json',
            'no_html': '1',
            'skip_disambig': '1'
        }
        
        response = await self.api_module.get(user_id, url, params=params)
        
        if response.get('status') != 200:
            return {
                'error': 'Błąd połączenia z DuckDuckGo',
                'details': response
            }
        
        data = response.get('data', {})
        
        # Przetwórz wyniki DuckDuckGo
        results = {
            'engine': 'duckduckgo',
            'query': query,
            'results': [],
            'instant_answer': None,
            'definition': None
        }
        
        # Instant Answer (jeśli jest)
        if data.get('Answer'):
            results['instant_answer'] = {
                'answer': data['Answer'],
                'type': data.get('AnswerType', ''),
                'source': data.get('AbstractSource', '')
            }
        
        # Definicja (jeśli jest)
        if data.get('Definition'):
            results['definition'] = {
                'definition': data['Definition'],
                'source': data.get('DefinitionSource', ''),
                'url': data.get('DefinitionURL', '')
            }
        
        # Abstrakty
        if data.get('Abstract'):
            results['results'].append({
                'title': data.get('Heading', 'Informacja'),
                'snippet': data['Abstract'],
                'url': data.get('AbstractURL', ''),
                'source': data.get('AbstractSource', ''),
                'type': 'abstract'
            })
        
        # Related Topics
        for topic in data.get('RelatedTopics', [])[:max_results]:
            if isinstance(topic, dict) and 'Text' in topic:
                results['results'].append({
                    'title': topic.get('Text', '').split(' - ')[0] if ' - ' in topic.get('Text', '') else 'Powiązany temat',
                    'snippet': topic.get('Text', ''),
                    'url': topic.get('FirstURL', ''),
                    'type': 'related_topic'
                })
        
        return results
    
    async def _search_google(self, user_id: int, query: str,
                           api_key: str = None, max_results: int = 10) -> Dict[str, Any]:
        """Wyszukiwanie za pomocą Google Custom Search API."""
        
        if not api_key:
            return {
                'error': 'Google Search wymaga klucza API',
                'help': 'Ustaw klucz Google Custom Search API'
            }
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'q': query,
            'num': min(max_results, 10),  # Google pozwala max 10 na zapytanie
            'gl': 'pl',  # Lokalizacja - Polska
            'hl': 'pl',  # Język
            'safe': 'medium'
        }
        
        response = await self.api_module.get(user_id, url, params=params)
        
        if response.get('status') != 200:
            return {
                'error': 'Błąd połączenia z Google Search API',
                'details': response
            }
        
        data = response.get('data', {})
        
        results = {
            'engine': 'google',
            'query': query,
            'results': [],
            'search_information': data.get('searchInformation', {}),
            'spelling': data.get('spelling', {})
        }
        
        # Przetwórz wyniki Google
        for item in data.get('items', []):
            result = {
                'title': item.get('title', ''),
                'snippet': item.get('snippet', ''),
                'url': item.get('link', ''),
                'display_link': item.get('displayLink', ''),
                'type': 'web_result'
            }
            
            # Dodaj obrazek jeśli jest
            if 'pagemap' in item and 'cse_image' in item['pagemap']:
                images = item['pagemap']['cse_image']
                if images:
                    result['image'] = images[0].get('src')
            
            results['results'].append(result)
        
        return results
    
    async def _search_bing(self, user_id: int, query: str,
                          api_key: str = None, max_results: int = 10) -> Dict[str, Any]:
        """Wyszukiwanie za pomocą Bing Search API."""
        
        if not api_key:
            return {
                'error': 'Bing Search wymaga klucza API',
                'help': 'Ustaw klucz Bing Search API'
            }
        
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {
            'Ocp-Apim-Subscription-Key': api_key
        }
        params = {
            'q': query,
            'count': min(max_results, 50),
            'offset': 0,
            'mkt': 'pl-PL',
            'safesearch': 'Moderate'
        }
        
        response = await self.api_module.get(user_id, url, headers=headers, params=params)
        
        if response.get('status') != 200:
            return {
                'error': 'Błąd połączenia z Bing Search API',
                'details': response
            }
        
        data = response.get('data', {})
        
        results = {
            'engine': 'bing',
            'query': query,
            'results': [],
            'web_pages': data.get('webPages', {}),
            'query_context': data.get('queryContext', {})
        }
          # Przetwórz wyniki Bing
        web_pages = data.get('webPages', {})
        for item in web_pages.get('value', []):
            result = {
                'title': item.get('name', ''),
                'snippet': item.get('snippet', ''),
                'url': item.get('url', ''),
                'display_url': item.get('displayUrl', ''),
                'date_last_crawled': item.get('dateLastCrawled', ''),
                'type': 'web_result'
            }
            
            results['results'].append(result)
        
        return results
    
    async def search_news(self, user_id: int, query: str = None,
                         language: str = "pl", max_results: int = 5,
                         api_key: str = None, category: str = None, 
                         country: str = "pl") -> Dict[str, Any]:
        """
        Wyszukuje wiadomości.
        
        Args:
            user_id: ID użytkownika
            query: Zapytanie (opcjonalne)
            category: Kategoria wiadomości
            country: Kod kraju
            api_key: Klucz NewsAPI
            
        Returns:
            Wyniki wyszukiwania wiadomości
        """
        if not api_key:
            return {
                'error': 'Wyszukiwanie wiadomości wymaga klucza NewsAPI',
                'help': 'Ustaw klucz API z https://newsapi.org'
            }
        
        if not self.api_module:
            await self.initialize()
        
        return await self.api_module.get_news(
            user_id=user_id,
            api_key=api_key,
            query=query,
            category=category,
            country=country
        )
    
    async def search_images(self, user_id: int, query: str,
                           api_key: str = None, engine: str = "bing") -> Dict[str, Any]:
        """
        Wyszukuje obrazy.
        
        Args:
            user_id: ID użytkownika
            query: Zapytanie wyszukiwania
            api_key: Klucz API
            engine: Silnik wyszukiwania obrazów
            
        Returns:
            Wyniki wyszukiwania obrazów
        """
        if engine == "bing" and api_key:
            url = "https://api.bing.microsoft.com/v7.0/images/search"
            headers = {
                'Ocp-Apim-Subscription-Key': api_key
            }
            params = {
                'q': query,
                'count': 20,
                'offset': 0,
                'mkt': 'pl-PL',
                'safeSearch': 'Moderate'
            }
            
            if not self.api_module:
                await self.initialize()
            
            response = await self.api_module.get(user_id, url, headers=headers, params=params)
            
            if response.get('status') != 200:
                return {
                    'error': 'Błąd wyszukiwania obrazów',
                    'details': response
                }
            
            data = response.get('data', {})
            images = []
            
            for item in data.get('value', []):
                images.append({
                    'title': item.get('name', ''),
                    'url': item.get('webSearchUrl', ''),
                    'thumbnail_url': item.get('thumbnailUrl', ''),
                    'content_url': item.get('contentUrl', ''),
                    'width': item.get('width', 0),
                    'height': item.get('height', 0),
                    'size': item.get('contentSize', ''),
                    'host_page_url': item.get('hostPageUrl', '')
                })
            
            return {
                'engine': 'bing_images',
                'query': query,
                'images': images,
                'total_estimated_matches': data.get('totalEstimatedMatches', 0)
            }
        
        else:
            return {
                'error': f'Nieobsługiwany silnik obrazów: {engine}',
                'supported_engines': ['bing']
            }
    
    def extract_search_intent(self, query: str) -> Dict[str, Any]:
        """
        Analizuje intencję zapytania wyszukiwania.
        
        Args:
            query: Zapytanie użytkownika
            
        Returns:
            Analiza intencji
        """
        query_lower = query.lower()
        
        # Wzorce dla różnych typów zapytań
        patterns = {
            'weather': r'pogoda|temperatura|deszcz|słońce|prognoza pogody',
            'news': r'wiadomości|aktualności|newsy|co się dzieje',
            'definition': r'co to jest|co oznacza|definicja|znaczenie',
            'how_to': r'jak|w jaki sposób|tutorial|instrukcja',
            'when': r'kiedy|o której|w którym roku|data',
            'where': r'gdzie|w którym miejscu|lokalizacja|adres',
            'who': r'kto|kim jest|biografia',
            'why': r'dlaczego|z jakiego powodu|przyczyna',
            'price': r'cena|koszt|ile kosztuje|za ile',
            'review': r'opinia|recenzja|test|ocena'
        }
        
        intent = {
            'query': query,
            'type': 'general',
            'keywords': query_lower.split(),
            'suggested_engine': 'duckduckgo',
            'filters': []
        }
        
        # Wykryj typ zapytania
        for intent_type, pattern in patterns.items():
            if re.search(pattern, query_lower):
                intent['type'] = intent_type
                break
        
        # Sugeruj silnik na podstawie typu
        if intent['type'] == 'news':
            intent['suggested_engine'] = 'google'
        elif intent['type'] == 'weather':
            intent['suggested_engine'] = 'duckduckgo'
        elif intent['type'] in ['definition', 'how_to']:
            intent['suggested_engine'] = 'duckduckgo'
        
        # Wyciągnij potencjalne filtry
        if 'ostatni' in query_lower or 'najnowszy' in query_lower:
            intent['filters'].append('recent')
        
        if any(word in query_lower for word in ['polski', 'polska', 'polskie']):
            intent['filters'].append('polish')
        
        return intent
    
    async def smart_search(self, user_id: int, query: str,
                          user_api_keys: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Inteligentne wyszukiwanie z automatycznym wyborem silnika.
        
        Args:
            user_id: ID użytkownika
            query: Zapytanie
            user_api_keys: Klucze API użytkownika
            
        Returns:
            Wyniki inteligentnego wyszukiwania
        """
        if user_api_keys is None:
            user_api_keys = {}
        
        # Analizuj intencję
        intent = self.extract_search_intent(query)
        
        # Wybierz najlepszy silnik
        engine = intent['suggested_engine']
        
        # Sprawdź dostępność API key
        if engine == 'google' and 'google_search' not in user_api_keys:
            engine = 'duckduckgo'  # Fallback
        
        api_key = user_api_keys.get(f'{engine}_search') or user_api_keys.get('google_search')
        
        # Wykonaj wyszukiwanie
        results = await self.search(
            user_id=user_id,
            query=query,
            engine=engine,
            api_key=api_key
        )
        
        # Dodaj analizę intencji do wyników
        results['intent_analysis'] = intent        
        return results
        
    async def _get_user_api_key(self, user_id: int, provider: str) -> Optional[str]:
        """
        Pobiera klucz API użytkownika dla danego providera.
        
        Args:
            user_id: ID użytkownika
            provider: Provider (newsapi, google_search, bing_search)
            
        Returns:
            Klucz API lub None
        """
        try:
            from database_manager import get_database_manager
            db_manager = get_database_manager()
            return db_manager.get_user_api_key(user_id, provider)
        except Exception as e:
            logger.error(f"Error getting API key for user {user_id}, provider {provider}: {e}")
            return None
       

# Globalna instancja
_search_module = None

async def get_search_module() -> SearchModule:
    """Pobiera globalną instancję modułu wyszukiwania."""
    global _search_module
    if _search_module is None:
        _search_module = SearchModule()
        await _search_module.initialize()
    return _search_module
