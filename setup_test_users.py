#!/usr/bin/env python3
"""User Management for Testing Sets up test users in the database for comprehensive
testing."""

import json
import logging
import sqlite3
from pathlib import Path

import bcrypt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestUserManager:
    """Manages test users in the database."""

    def __init__(self, db_path: str = "databases/server_data.db"):
        self.db_path = Path(db_path)
        self.test_users = [
            {
                "id": "1",
                "email": "admin@gaja.app",
                "password": "admin123",
                "role": "admin",
                "name": "Administrator",
                "settings": {
                    "language": "en",
                    "voice": "default",
                    "wakeWord": True,
                    "privacy": {"shareAnalytics": True, "storeConversations": True},
                },
            },
            {
                "id": "2",
                "email": "demo@mail.com",
                "password": "demo1234",
                "role": "user",
                "name": "Demo User",
                "settings": {
                    "language": "en",
                    "voice": "default",
                    "wakeWord": True,
                    "privacy": {"shareAnalytics": False, "storeConversations": True},
                },
            },
            {
                "id": "3",
                "email": "test@example.com",
                "password": "test123",
                "role": "user",
                "name": "Test User",
                "settings": {
                    "language": "en",
                    "voice": "default",
                    "wakeWord": False,
                    "privacy": {"shareAnalytics": False, "storeConversations": False},
                },
            },
        ]

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def setup_database(self):
        """Setup database tables if they don't exist."""
        if not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check existing table structure
            cursor.execute("PRAGMA table_info(users)")
            existing_columns = [row[1] for row in cursor.fetchall()]

            if existing_columns:
                logger.info(
                    f"Found existing users table with columns: {existing_columns}"
                )
                # Work with existing structure
                return
            else:
                # Create new table with current schema
                cursor.execute(
                    """
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        email TEXT UNIQUE,
                        password_hash TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP,
                        settings TEXT DEFAULT '{}',
                        api_keys TEXT DEFAULT '{}'
                    )
                """
                )

            # Create index on email
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

            conn.commit()
            logger.info("Database tables created/verified")

    def add_test_users(self):
        """Add test users to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for user in self.test_users:
                try:
                    # Hash password
                    password_hash = self.hash_password(user["password"])

                    # Convert settings to JSON
                    settings_json = json.dumps(user["settings"])

                    # Check if user exists
                    cursor.execute(
                        "SELECT id FROM users WHERE email = ?", (user["email"],)
                    )
                    existing = cursor.fetchone()

                    if existing:
                        # Update existing user
                        cursor.execute(
                            """
                            UPDATE users
                            SET password_hash = ?, settings = ?
                            WHERE email = ?
                        """,
                            (password_hash, settings_json, user["email"]),
                        )
                        logger.info(f"Updated user: {user['email']}")
                    else:
                        # Insert new user - adapt to existing schema
                        cursor.execute(
                            """
                            INSERT INTO users
                            (username, email, password_hash, settings)
                            VALUES (?, ?, ?, ?)
                        """,
                            (
                                user["name"],  # Use name as username
                                user["email"],
                                password_hash,
                                settings_json,
                            ),
                        )
                        logger.info(f"Added user: {user['email']}")

                except Exception as e:
                    logger.error(f"Failed to add user {user['email']}: {e}")

            conn.commit()

    def verify_users(self):
        """Verify test users exist in database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id, email, username FROM users")
            users = cursor.fetchall()

            logger.info(f"Found {len(users)} users in database:")
            for user in users:
                logger.info(f"  - {user[1]} ({user[2]})")

            return users

    def clean_test_users(self):
        """Remove test users (except admin)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Keep admin, remove others
            cursor.execute("DELETE FROM users WHERE email != ?", ("admin@gaja.app",))
            deleted = cursor.rowcount

            conn.commit()
            logger.info(f"Cleaned {deleted} test users (kept admin)")

    def setup_for_testing(self):
        """Complete setup for testing."""
        logger.info("Setting up database for comprehensive testing...")

        self.setup_database()
        self.add_test_users()
        users = self.verify_users()

        logger.info("✅ Database setup complete for testing")
        return users


def main():
    """Main setup function."""
    manager = TestUserManager()
    users = manager.setup_for_testing()
    return users


if __name__ == "__main__":
    main()
