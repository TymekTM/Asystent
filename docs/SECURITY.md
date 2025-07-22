# GAJA Assistant - Security Guide

## Przegląd bezpieczeństwa

GAJA Assistant implementuje wielopoziomowe zabezpieczenia chroniące zarówno dane użytkowników jak i sam system. Ten dokument opisuje środki bezpieczeństwa oraz najlepsze praktyki.

## 🔐 Zarządzanie kluczami API

### Zmienne środowiskowe
Wszystkie klucze API powinny być przechowywane jako zmienne środowiskowe lub w pliku `.env`:

```bash
# .env
OPENAI_API_KEY=your_actual_api_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here
AZURE_SPEECH_KEY=your_azure_key_here
```

### Migracja istniejących kluczy
Użyj skryptu `migrate_api_keys.py` aby bezpiecznie przenieść klucze z plików konfiguracyjnych:

```bash
# Skanuj pliki w poszukiwaniu kluczy
python migrate_api_keys.py --scan-only

# Pełna migracja z kopią zapasową
python migrate_api_keys.py

# Migracja z usunięciem kluczy z plików konfiguracyjnych
python migrate_api_keys.py --clean
```

### Zabezpieczenia implementacji
- Klucze API są automatycznie ładowane z zmiennych środowiskowych
- Wartości wrażliwe są sanityzowane przed logowaniem
- Pliki konfiguracyjne nie zawierają rzeczywistych kluczy
- Automatyczna walidacja kluczy przy starcie

## 🔒 System uwierzytelniania

### Bezpieczne hashowanie haseł
- PBKDF2 z 100,000 iteracji
- Losowe salt dla każdego hasła
- Bezpieczne porównywanie hash'y z `secrets.compare_digest()`

### Domyślny administrator
- Generowane losowe hasło (160-bit entropii)
- Hasło zapisywane do bezpiecznego pliku z odpowiednimi uprawnieniami
- Ostrzeżenia w logach o konieczności zmiany hasła

### Blokowanie kont
- Maksymalnie 5 nieudanych prób logowania
- 30 minut blokady po przekroczeniu limitu
- Automatyczne czyszczenie nieudanych prób po udanym logowaniu

## 🌐 Bezpieczeństwo sieciowe

### CORS (Cross-Origin Resource Sharing)
- Domyślnie ograniczony do `localhost`
- Ostrzeżenia przy konfiguracji `*` (wszystkie domeny)
- Automatyczna walidacja w trybie debug

### Konfiguracja serwera
```json
{
  "server": {
    "host": "localhost",  // Domyślnie localhost dla bezpieczeństwa
    "port": 8001
  },
  "security": {
    "cors_origins": [
      "http://localhost:3000",
      "http://localhost:8080"
    ],
    "max_connections_per_user": 5
  }
}
```

## 🔧 Bezpieczne ładowanie pluginów

### Walidacja nazw pluginów
- Tylko znaki alfanumeryczne, myślniki i podkreślenia
- Zapobieganie path traversal (`../`, `/`, `\`)
- Maksymalna długość nazwy: 50 znaków
- Opcjonalna whitelist dozwolonych pluginów

### Ograniczenia plików
- Maksymalny rozmiar pliku: 1MB (konfigurowalny)
- Walidacja uprawnień do odczytu
- Sprawdzanie czy plik znajduje się w katalogu `modules/`
- Timeout przy ładowaniu pluginów (10 sekund)

### Konfiguracja bezpieczeństwa pluginów
```json
{
  "plugins": {
    "whitelist": ["weather_module", "search_module"],
    "max_file_size": 1048576,
    "timeout_seconds": 10
  }
}
```

## 🖥️ Zarządzanie procesami

### Bezpieczne uruchamianie procesów zewnętrznych
- Walidacja ścieżek do plików wykonywalnych
- Zapobieganie uruchamianiu niebezpiecznych binariów
- Kontrola uprawnień plików
- Timeout przy uruchamianiu procesów

### Overlay Tauri
- Uruchamiany z ograniczonymi uprawnieniami
- Bezpieczne zamykanie z timeout'ami
- Walidacja ścieżki przed uruchomieniem
- Obsługa Windows-specific creation flags

## 📁 Struktura plików

### Pliki chronione przez .gitignore
```gitignore
# Wrażliwe dane
.env
.env.local
.env.production
admin_credentials.txt
**/config.json
**/client_config.json  
**/server_config.json

# Bazy danych
*.db
*.sqlite
*.sqlite3

# Logi (mogą zawierać wrażliwe dane)
logs/
*.log
```

## 🛡️ Najlepsze praktyki

### Dla administratorów
1. **Zmień domyślne hasło administratora** natychmiast po pierwszym logowaniu
2. **Usuń plik `admin_credentials.txt`** po zapisaniu hasła w bezpiecznym miejscu
3. **Skonfiguruj CORS** tylko dla zaufanych domen w produkcji
4. **Monitoruj logi** pod kątem podejrzanej aktywności
5. **Aktualizuj regularnie** zależności i system

### Dla użytkowników
1. **Używaj silnych haseł** (minimum 12 znaków, mieszane znaki)
2. **Nie udostępniaj kluczy API** nikomu
3. **Sprawdzaj regularne kopie zapasowe** danych
4. **Monitoruj wykorzystanie API** u dostawców usług
5. **Zgłaszaj podejrzaną aktywność** administratorom

### Dla deweloperów
1. **Nigdy nie commituj** prawdziwych kluczy API
2. **Używaj zmiennych środowiskowych** do wszystkich wrażliwych danych
3. **Waliduj wszystkie dane wejściowe** od użytkowników
4. **Stosuj principle of least privilege** dla uprawnień
5. **Dokumentuj wszystkie zmiany** związane z bezpieczeństwem

## 🚨 Procedury awaryjne

### W przypadku wycieku kluczy API
1. **Natychmiast unieważnij** skompromitowane klucze u dostawcy
2. **Wygeneruj nowe klucze** API
3. **Zaktualizuj zmienne środowiskowe**
4. **Sprawdź logi** pod kątem nieautoryzowanego użycia
5. **Powiadom użytkowników** jeśli konieczne

### W przypadku włamania
1. **Odłącz system** od sieci
2. **Zmień wszystkie hasła** użytkowników
3. **Sprawdź integralność** plików systemowych
4. **Przeanalizuj logi** bezpieczeństwa
5. **Zaktualizuj system** do najnowszej wersji

### Kontakt w sprawie bezpieczeństwa
W przypadku znalezienia luki bezpieczeństwa, skontaktuj się:
- Email: security@gaja-assistant.local
- Discord: [Serwer społeczności]
- GitHub Issues: [Repository Issues]

## 📊 Audyt bezpieczeństwa

### Regularne sprawdzenia
- **Cotygodniowe**: Przegląd logów bezpieczeństwa
- **Comiesięczne**: Aktualizacja zależności
- **Kwartalnie**: Pełny audyt konfiguracji
- **Rocznie**: Zewnętrzny audyt bezpieczeństwa

### Narzędzia audytu
- `migrate_api_keys.py --scan-only` - skanowanie kluczy API
- `bandit` - analiza bezpieczeństwa kodu Python
- `safety` - sprawdzenie znanych luk w zależnościach
- Custom security scanner - wewnętrzne narzędzie audytu

## 📚 Dodatkowe zasoby

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Guide](https://python-security.readthedocs.io/)
- [API Security Best Practices](https://owasp.org/www-project-api-security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

**Ostatnia aktualizacja:** Grudzień 2024  
**Wersja dokumentu:** 1.0  
**Status:** Aktywny
