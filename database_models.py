import sqlite3
import os
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'assistant_memory.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                display_name TEXT,
                ai_persona TEXT,
                personalization TEXT
            )
        ''')
        # Memories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                user_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        # User config table (JSON blob for flexibility)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                config TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()
        conn.close()

def get_user_by_username(username):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user

def add_user(username, password, role='user', display_name=None, ai_persona=None, personalization=None):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password, role, display_name, ai_persona, personalization) VALUES (?, ?, ?, ?, ?, ?)',
                     (username, password, role, display_name, ai_persona, personalization))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_user(username):
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE username = ?', (username,))
    conn.commit()
    conn.close()

def list_users():
    conn = get_db_connection()
    users = conn.execute('SELECT username, role, display_name, ai_persona, personalization FROM users').fetchall()
    conn.close()
    # Convert sqlite3.Row to dict for Jinja2 compatibility
    return [dict(u) for u in users]

def update_user(username, **fields):
    conn = get_db_connection()
    keys = ', '.join([f'{k} = ?' for k in fields.keys()])
    values = list(fields.values()) + [username]
    conn.execute(f'UPDATE users SET {keys} WHERE username = ?', values)
    conn.commit()
    conn.close()

def set_user_config(user_id, config_json):
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO user_configs (user_id, config) VALUES (?, ?)', (user_id, config_json))
    conn.commit()
    conn.close()

def get_user_config(user_id):
    conn = get_db_connection()
    row = conn.execute('SELECT config FROM user_configs WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return row['config'] if row else None

def ensure_dev_account():
    if not get_user_by_username('dev'):
        add_user('dev', 'devpassword', 'dev', display_name='Dev', ai_persona='Admin', personalization='')

# Ensure dev account always exists on startup
initialize_database()
ensure_dev_account()
