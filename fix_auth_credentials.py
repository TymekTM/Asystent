#!/usr/bin/env python3
"""
GAJA Assistant - Authentication Fix Script
Naprawia hasła użytkowników w serwerze generując właściwe hashe.
"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

import re

from server.auth.security import SecurityManager


def fix_server_auth():
    """Naprawia autoryzację w serwerze generując właściwe hashe haseł."""

    print("🔧 GAJA Assistant - Authentication Fix")
    print("=" * 50)

    # Inicjalizuj security manager
    security_manager = SecurityManager()

    # Definiuj poprawne dane użytkowników
    users_to_fix = {
        "admin@gaja.app": {"password": "admin123", "role": "admin"},
        "demo@mail.com": {"password": "demo1234", "role": "user"},
    }

    # Wygeneruj poprawne hashe
    print("🔐 Generowanie nowych hash'y haseł...")
    fixed_users = {}

    for email, user_data in users_to_fix.items():
        password = user_data["password"]
        password_hash = security_manager.hash_password(password)

        fixed_users[email] = {
            "email": email,
            "password": password,
            "password_hash": password_hash,
            "role": user_data["role"],
        }

        print(f"✅ {email}: hash wygenerowany")

    # Odczytaj plik routes.py
    routes_file = "server/api/routes.py"
    if not os.path.exists(routes_file):
        print(f"❌ Nie znaleziono pliku: {routes_file}")
        return False

    print(f"\n📖 Odczytywanie pliku: {routes_file}")
    with open(routes_file, encoding="utf-8") as f:
        content = f.read()

    # Znajdź sekcję SECURE_USERS
    pattern = r"SECURE_USERS = \{([^}]+)\}"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        print("❌ Nie znaleziono sekcji SECURE_USERS w pliku routes.py")
        return False

    # Wygeneruj nową sekcję SECURE_USERS
    new_secure_users = "SECURE_USERS = {\n"

    for email, user_data in fixed_users.items():
        user_id = "1" if user_data["role"] == "admin" else "2"

        new_secure_users += f'    "{email}": {{\n'
        new_secure_users += f'        "id": "{user_id}",\n'
        new_secure_users += f'        "email": "{email}",\n'
        new_secure_users += f'        "role": "{user_data["role"]}",\n'
        new_secure_users += (
            f'        "password_hash": "{user_data["password_hash"]}",\n'
        )
        new_secure_users += '        "is_active": True,\n'
        new_secure_users += '        "created_at": datetime.now().isoformat(),\n'
        new_secure_users += '        "settings": {\n'

        if user_data["role"] == "admin":
            new_secure_users += '            "language": "en",\n'
            new_secure_users += '            "voice": "default",\n'
            new_secure_users += '            "wakeWord": True,\n'
            new_secure_users += '            "privacy": {"shareAnalytics": True, "storeConversations": True},\n'
        else:
            new_secure_users += '            "language": "pl",\n'
            new_secure_users += '            "voice": "default",\n'
            new_secure_users += '            "wakeWord": True,\n'
            new_secure_users += '            "privacy": {"shareAnalytics": False, "storeConversations": True},\n'

        new_secure_users += "        },\n"
        new_secure_users += "    },\n"

    new_secure_users += "}"

    # Zastąp w treści pliku
    new_content = re.sub(pattern, new_secure_users, content, flags=re.DOTALL)

    # Zapisz kopię zapasową
    backup_file = f"{routes_file}.backup"
    with open(backup_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"💾 Kopia zapasowa zapisana: {backup_file}")

    # Zapisz nową treść
    with open(routes_file, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ Plik {routes_file} został zaktualizowany!")

    # Wyświetl dane logowania
    print("\n🔑 DANE LOGOWANIA:")
    print("=" * 30)
    for email, user_data in fixed_users.items():
        print(f"📧 Email: {email}")
        print(f"🔒 Hasło: {user_data['password']}")
        print(f"👤 Rola: {user_data['role']}")
        print("-" * 20)

    print("\n🚀 NEXT STEPS:")
    print("1. Uruchom ponownie serwer Docker")
    print("2. Przetestuj logowanie używając powyższych danych")
    print("3. Sprawdź funkcje calling system")

    return True


def test_auth_locally():
    """Testuje autoryzację lokalnie."""

    print("\n🧪 Test autoryzacji lokalnie...")
    security_manager = SecurityManager()

    # Test dla admin@gaja.app / admin123
    admin_hash = security_manager.hash_password("admin123")
    admin_verified = security_manager.verify_password("admin123", admin_hash)

    # Test dla demo@mail.com / demo1234
    demo_hash = security_manager.hash_password("demo1234")
    demo_verified = security_manager.verify_password("demo1234", demo_hash)

    print(f"✅ Admin test: {'PASSED' if admin_verified else 'FAILED'}")
    print(f"✅ Demo test: {'PASSED' if demo_verified else 'FAILED'}")

    return admin_verified and demo_verified


if __name__ == "__main__":
    try:
        # Test lokalny
        if not test_auth_locally():
            print("❌ Test lokalny autoryzacji nie powiódł się!")
            sys.exit(1)

        # Napraw autoryzację w serwerze
        if fix_server_auth():
            print("\n🎉 Autoryzacja została naprawiona!")
        else:
            print("\n❌ Nie udało się naprawić autoryzacji!")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Błąd: {e}")
        sys.exit(1)
