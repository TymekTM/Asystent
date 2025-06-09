#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import sqlite3
from pathlib import Path

# Sprawdź bazę danych bezpośrednio
db_path = Path("f:/Asystent/server/server_data.db")

print(f"Sprawdzanie bazy danych: {db_path}")
print(f"Plik istnieje: {db_path.exists()}")

if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    # Włącz foreign keys jak w DatabaseManager
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    
    cursor = conn.cursor()
    
    # Sprawdź użytkowników
    print("\n=== UŻYTKOWNICY ===")
    cursor.execute("SELECT id, username, created_at FROM users")
    users = cursor.fetchall()
    for user in users:
        print(f"ID: {user['id']}, Username: {user['username']}, Created: {user['created_at']}")
    
    # Sprawdź foreign keys
    print("\n=== FOREIGN KEYS ===")
    cursor.execute("PRAGMA foreign_keys")
    fk_status = cursor.fetchone()
    print(f"Foreign keys enabled: {fk_status[0] if fk_status else 'unknown'}")
    
    # Sprawdź strukturę tabeli memory_contexts
    print("\n=== STRUKTURA TABELI memory_contexts ===")
    cursor.execute("PRAGMA table_info(memory_contexts)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"{col['name']}: {col['type']} (not null: {col['notnull']}, default: {col['dflt_value']})")
    
    # Sprawdź foreign key constraints
    print("\n=== FOREIGN KEY CONSTRAINTS ===")
    cursor.execute("PRAGMA foreign_key_list(memory_contexts)")
    fks = cursor.fetchall()
    for fk in fks:
        print(f"Column: {fk['from']} -> {fk['table']}.{fk['to']}")
    
    # Sprawdź pamięć
    print("\n=== WPISY PAMIĘCI ===")
    cursor.execute("SELECT COUNT(*) as count FROM memory_contexts")
    count = cursor.fetchone()
    print(f"Liczba wpisów: {count['count']}")
    
    conn.close()
else:
    print("Baza danych nie istnieje!")
