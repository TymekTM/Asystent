import json
import os
import requests

class APIManager:
    def __init__(self, config_path="modules\\api_integrations_config.json"):
        self.config_path = config_path
        self.integrations = self.load_config()
        # Async HTTP session for non-blocking requests; created lazily in async context
        try:
            import aiohttp
            self._aio_module = aiohttp
            self._aio_session = None
        except ImportError:
            self._aio_module = None
            self._aio_session = None

    def load_config(self) -> dict:
        """
        Ładuje konfigurację integracji z pliku JSON.
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Nie znaleziono pliku konfiguracyjnego: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def check_integration_async(self, integration_name: str) -> bool:
        """
        Sprawdza, czy dana integracja API jest dostępna.
        Dla przykładu wywołuje zapytanie GET z domyślnym parametrem.
        """
        integration = self.integrations.get(integration_name)
        if not integration or not self._aio_module:
            return False
        # ensure session is initialized in async context
        if self._aio_session is None:
            self._aio_session = self._aio_module.ClientSession()
        default_location = integration.get("default_params", {}).get("location", "")
        url = integration["url_template"].format(default_location)
        try:
            async with self._aio_session.get(url, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False
    
    def check_integration(self, integration_name: str) -> bool:
        """Synchronous check using requests library."""
        integration = self.integrations.get(integration_name)
        if not integration:
            return False
        default_location = integration.get("default_params", {}).get("location", "")
        url = integration["url_template"].format(default_location)
        try:
            resp = requests.get(url, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def get_best_integration(self, query: str) -> str:
        """
        Wybiera najlepszą (najwyższy priorytet) integrację, która jest dostępna.
        Możesz rozszerzyć logikę na podstawie treści zapytania.
        """
        sorted_integrations = sorted(
            self.integrations.items(), key=lambda item: item[1].get("priority", 100)
        )
        for name, config in sorted_integrations:
            if self.check_integration(name):
                return name
        return None

    async def call_integration_async(self, integration_name: str, params: dict) -> str:
        """
        Wywołuje integrację API dla podanej nazwy z uwzględnieniem przekazanych parametrów.
        Jeśli nie podano parametrów, używa wartości domyślnych.
        """
        integration = self.integrations.get(integration_name)
        if not integration or not self._aio_module:
            return f"Nie znaleziono integracji o nazwie {integration_name}."
        # ensure session is initialized in async context
        if self._aio_session is None:
            self._aio_session = self._aio_module.ClientSession()
        location = params.get("location", integration.get("default_params", {}).get("location", ""))
        url = integration["url_template"].format(location)
        try:
            async with self._aio_session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    return text.strip()
                else:
                    return f"API zwróciło błąd: {resp.status}"
        except Exception as e:
            return f"Wystąpił wyjątek: {e}"
    
    def call_integration(self, integration_name: str, params: dict) -> str:
        """Synchronous call using requests library."""
        integration = self.integrations.get(integration_name)
        if not integration:
            return f"Nie znaleziono integracji o nazwie {integration_name}."
        location = params.get("location", integration.get("default_params", {}).get("location", ""))
        url = integration["url_template"].format(location)
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return resp.text.strip()
            else:
                return f"API zwróciło błąd: {resp.status_code}"
        except Exception as e:
            return f"Wystąpił wyjątek: {e}"

    async def handle_api_query_async(self, query: str, params: dict) -> str:
        """
        Główna funkcja obsługująca zapytania API.
        Na podstawie zapytania wybiera najlepszą dostępną integrację i wywołuje ją.
        """
        best = self.get_best_integration(query)
        if best:
            return await self.call_integration_async(best, params)
        return "Żadna integracja API nie jest dostępna."
    
    def handle_api_query(self, query: str, params: dict) -> str:
        """Synchronous handler using sync integration calls."""
        best = self.get_best_integration(query)
        if best:
            return self.call_integration(best, params)
        return "Żadna integracja API nie jest dostępna."

# Globalna instancja managera API
api_manager = APIManager()

# Modify handler to accept conversation_history (though likely unused here)
def handle_api_query_wrapper(params: str, conversation_history: list = None) -> str:
    """
    Handler rejestrowany jako plugin.
    Parametry wejściowe traktujemy jako lokalizację dla zapytania o pogodę.
    Jeśli nie podano, użyjemy wartości domyślnej z konfiguracji.
    """
    location = params.strip() if params.strip() else ""
    # W tym przykładzie query jest ignorowane i zakładamy, że chodzi o pogodę.
    # conversation_history is available but not used in this specific tool
    # Wrap async handler in sync call
    # Delegate to synchronous handler
    return api_manager.handle_api_query("Pogoda", {"location": location})

def register():
    """
    Funkcja rejestrująca plugin API.
    Zwraca słownik zawierający:
      - command: nazwa komendy
      - aliases: lista aliasów
      - description: opis funkcji
      - handler: funkcja obsługująca zapytanie
    """
    return {
        "command": "api",
        "aliases": ["api", "pogoda", "weather"],
        "description": "Obsługuje zapytania API na podstawie konfiguracji w JSON.",
        "handler": handle_api_query_wrapper,
        "sub_commands": {
            "weather": {
                "description": "Sprawdź pogodę dla danej lokalizacji",
                "parameters": {
                    "location": {
                        "type": "string",
                        "description": "Nazwa miasta lub lokalizacji do sprawdzenia pogody",
                        "required": True
                    }
                }
            },
            "api_call": {
                "description": "Wykonaj zapytanie API",
                "parameters": {
                    "query": {
                        "type": "string", 
                        "description": "Zapytanie do API",
                        "required": True
                    }
                }
            }
        }
    }

if __name__ == "__main__":
    # Przykładowe wywołanie: zapytanie o pogodę dla Krakowa
    result = handle_api_query_wrapper("Kraków")
    print(result)
