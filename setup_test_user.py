"""
setup_test_user.py
Skrypt do utworzenia testowego użytkownika w bazie danych
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "server"))

from database_manager import DatabaseManager
import json

def create_test_user():
    """Utwórz testowego użytkownika."""
    db = DatabaseManager("server/server_data.db")
      # Sprawdź czy użytkownik już istnieje
    existing_user = db.get_user(username="default_user")
    if existing_user:
        print("✅ Użytkownik 'default_user' już istnieje")
        user_id = existing_user.id
        print(f"✅ Używam istniejącego użytkownika (ID: {user_id})")
        return user_id
    
    # Utwórz użytkownika
    user_id = db.create_user(
        username="default_user",
        email="test@example.com",
        settings={
            "language": "pl",
            "theme": "dark"
        }
    )
    
    print(f"✅ Utworzono użytkownika 'default_user' (ID: {user_id})")
      # Ustaw domyślne pluginy
    import asyncio
    asyncio.run(db.update_user_plugins(str(user_id), "weather_module", True))
    asyncio.run(db.update_user_plugins(str(user_id), "search_module", True))
    
    print("✅ Ustawiono domyślne pluginy")
    
    # Dodaj przykładowe klucze API (placeholder)
    # UWAGA: W prawdziwej aplikacji należy ustawić prawdziwe klucze API
    try:
        db.set_user_api_key(user_id, "openweather", "YOUR_OPENWEATHER_API_KEY_HERE")
        db.set_user_api_key(user_id, "weatherapi", "YOUR_WEATHERAPI_KEY_HERE")
        db.set_user_api_key(user_id, "newsapi", "YOUR_NEWSAPI_KEY_HERE")
        print("✅ Dodano placeholder'y dla kluczy API")
        print("⚠️  Pamiętaj o ustawieniu prawdziwych kluczy API!")
    except Exception as e:
        print(f"⚠️  Nie udało się dodać kluczy API: {e}")
    
    return user_id

if __name__ == "__main__":
    create_test_user()
