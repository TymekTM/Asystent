#!/usr/bin/env python3
"""
GAJA Assistant - Simple Authentication Fix Script
Prosty skrypt naprawy autoryzacji używający bezpośrednio bcrypt.
"""

import bcrypt
import re
import os


def generate_password_hash(password: str) -> str:
    """Generuje hash hasła używając bcrypt."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    # Generuj salt i hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Weryfikuje hasło."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def fix_server_auth():
    """Naprawia autoryzację w serwerze."""
    
    print("🔧 GAJA Assistant - Simple Authentication Fix")
    print("="*50)
    
    # Definiuj użytkowników
    users_to_fix = {
        "admin@gaja.app": {
            "password": "admin123",
            "role": "admin"
        },
        "demo@mail.com": {
            "password": "demo1234", 
            "role": "user"
        }
    }
    
    # Wygeneruj hashe
    print("🔐 Generowanie hash'y haseł...")
    fixed_users = {}
    
    for email, user_data in users_to_fix.items():
        password = user_data["password"]
        password_hash = generate_password_hash(password)
        
        # Test
        test_result = verify_password(password, password_hash)
        print(f"✅ {email}: hash wygenerowany i zweryfikowany ({'OK' if test_result else 'ERROR'})")
        
        fixed_users[email] = {
            "email": email,
            "password": password,
            "password_hash": password_hash,
            "role": user_data["role"]
        }
    
    # Odczytaj plik routes.py
    routes_file = "server/api/routes.py"
    if not os.path.exists(routes_file):
        print(f"❌ Nie znaleziono pliku: {routes_file}")
        return False
    
    print(f"\n📖 Odczytywanie pliku: {routes_file}")
    with open(routes_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Znajdź sekcję SECURE_USERS
    start_pattern = r'SECURE_USERS = \{'
    end_pattern = r'\}'
    
    # Znajdź początek
    start_match = re.search(start_pattern, content)
    if not start_match:
        print("❌ Nie znaleziono początku SECURE_USERS")
        return False
    
    start_pos = start_match.start()
    
    # Znajdź koniec (pierwszą `}` po początku na odpowiednim poziomie)
    brace_count = 0
    end_pos = -1
    
    for i, char in enumerate(content[start_pos:]):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                end_pos = start_pos + i + 1
                break
    
    if end_pos == -1:
        print("❌ Nie znaleziono końca SECURE_USERS")
        return False
    
    # Wygeneruj nową sekcję SECURE_USERS
    new_secure_users = 'SECURE_USERS = {\n'
    
    for email, user_data in fixed_users.items():
        user_id = "1" if user_data["role"] == "admin" else "2"
        
        new_secure_users += f'    "{email}": {{\n'
        new_secure_users += f'        "id": "{user_id}",\n'
        new_secure_users += f'        "email": "{email}",\n'
        new_secure_users += f'        "role": "{user_data["role"]}",\n'
        new_secure_users += f'        "password_hash": "{user_data["password_hash"]}",\n'
        new_secure_users += f'        "is_active": True,\n'
        new_secure_users += f'        "created_at": datetime.now().isoformat(),\n'
        new_secure_users += f'        "settings": {{\n'
        
        if user_data["role"] == "admin":
            new_secure_users += f'            "language": "en",\n'
            new_secure_users += f'            "voice": "default",\n'
            new_secure_users += f'            "wakeWord": True,\n'
            new_secure_users += f'            "privacy": {{"shareAnalytics": True, "storeConversations": True}},\n'
        else:
            new_secure_users += f'            "language": "pl",\n'
            new_secure_users += f'            "voice": "default",\n'
            new_secure_users += f'            "wakeWord": True,\n'
            new_secure_users += f'            "privacy": {{"shareAnalytics": False, "storeConversations": True}},\n'
        
        new_secure_users += f'        }},\n'
        new_secure_users += f'    }},\n'
    
    new_secure_users += '}'
    
    # Zastąp w treści pliku
    new_content = content[:start_pos] + new_secure_users + content[end_pos:]
    
    # Zapisz kopię zapasową
    backup_file = f"{routes_file}.backup"
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"💾 Kopia zapasowa zapisana: {backup_file}")
    
    # Zapisz nową treść
    with open(routes_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Plik {routes_file} został zaktualizowany!")
    
    # Wyświetl dane logowania
    print("\n🔑 NOWE DANE LOGOWANIA:")
    print("="*35)
    for email, user_data in fixed_users.items():
        print(f"📧 Email: {email}")
        print(f"🔒 Hasło: {user_data['password']}")
        print(f"👤 Rola: {user_data['role']}")
        print("-" * 25)
    
    print("\n🚀 NEXT STEPS:")
    print("1. Uruchom ponownie serwer Docker")
    print("2. Przetestuj logowanie używając powyższych danych")
    print("3. Sprawdź funkcję calling system")
    
    return True


if __name__ == "__main__":
    try:
        if fix_server_auth():
            print("\n🎉 Autoryzacja została naprawiona!")
        else:
            print("\n❌ Nie udało się naprawić autoryzacji!")
            
    except Exception as e:
        print(f"\n❌ Błąd: {e}")
        import traceback
        traceback.print_exc()
