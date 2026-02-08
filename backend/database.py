# database.py — PostgreSQL
import threading
from contextlib import contextmanager

import psycopg2
from psycopg2 import extras

from config import config


def _replace_placeholders(query: str) -> str:
    """SQLite uses ?; PostgreSQL (psycopg2) uses %s."""
    return query.replace("?", "%s")


class Database:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(Database, cls).__new__(cls)
                    cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        self.conn = psycopg2.connect(
            config.DATABASE_URL,
            cursor_factory=extras.RealDictCursor,
        )
        self.conn.autocommit = False
        self._conn_lock = threading.Lock()
        self.create_tables()

    @contextmanager
    def get_connection(self):
        with self._conn_lock:
            try:
                yield self.conn
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def create_tables(self):
        """Создание всех таблиц (PostgreSQL). При включённом autocommit каждый запрос
        в своей транзакции — неудачный ALTER не переводит соединение в aborted."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            old_autocommit = conn.autocommit
            conn.autocommit = True
            try:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    name TEXT,
                    age INTEGER,
                    gender TEXT,
                    city TEXT,
                    relationship_status TEXT,
                    photo TEXT,
                    photos TEXT DEFAULT '[]',
                    purpose TEXT DEFAULT 'куда-то сходить',
                    reg_date TEXT,
                    points INTEGER DEFAULT 0,
                    last_active DATE,
                    favorite_categories TEXT DEFAULT '[]',
                    referral_code TEXT UNIQUE,
                    referred_by BIGINT DEFAULT NULL,
                    referrals_count INTEGER DEFAULT 0,
                    is_banned BOOLEAN DEFAULT FALSE,
                    ban_reason TEXT,
                    banned_date TEXT
                )
            """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    title TEXT,
                    description TEXT,
                    event_date TEXT,
                    target_gender TEXT DEFAULT 'Все',
                    city TEXT,
                    category TEXT,
                    created TEXT,
                    is_hidden BOOLEAN DEFAULT FALSE
                )
            """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS likes (
                    id SERIAL PRIMARY KEY,
                    from_user BIGINT,
                    to_user BIGINT,
                    event_id INTEGER REFERENCES events(id),
                    mutual BOOLEAN DEFAULT FALSE,
                    created TEXT,
                    response TEXT DEFAULT NULL
                )
            """)
                try:
                    cursor.execute("ALTER TABLE likes ADD COLUMN response TEXT DEFAULT NULL")
                except Exception:
                    pass  # колонка уже есть
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN photos TEXT DEFAULT '[]'")
                except Exception:
                    pass  # колонка уже есть

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS achievements (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    achievement_id TEXT,
                    unlocked_date TEXT
                )
            """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id BIGINT PRIMARY KEY REFERENCES users(user_id),
                    liked_categories TEXT DEFAULT '[]',
                    disliked_categories TEXT DEFAULT '[]',
                    preferred_time TEXT DEFAULT 'Вечер'
                )
            """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_broadcasts (
                    id SERIAL PRIMARY KEY,
                    admin_id BIGINT,
                    content_type TEXT,
                    content TEXT,
                    caption TEXT,
                    filters TEXT,
                    total_users INTEGER DEFAULT 0,
                    sent_users INTEGER DEFAULT 0,
                    failed_users INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created TEXT,
                    completed TEXT
                )
            """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id SERIAL PRIMARY KEY,
                    admin_id BIGINT,
                    action TEXT,
                    details TEXT,
                    created TEXT
                )
            """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS bans (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE,
                    reason TEXT,
                    banned_by BIGINT,
                    banned_date TEXT,
                    expires TEXT
                )
            """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id SERIAL PRIMARY KEY,
                    reporter_id BIGINT REFERENCES users(user_id),
                    reported_user_id BIGINT REFERENCES users(user_id),
                    reason TEXT,
                    status TEXT DEFAULT 'pending',
                    admin_notes TEXT,
                    created TEXT,
                    resolved TEXT,
                    appeal_status TEXT DEFAULT 'none',
                    appeal_text TEXT
                )
                """)
            finally:
                conn.autocommit = old_autocommit

    def execute_query(self, query, params=(), fetchone=False, fetchall=False, commit=False):
        """Выполнение SQL. Плейсхолдеры: ? заменяются на %s для PostgreSQL."""
        query = _replace_placeholders(query)
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute(query, params)

            if commit:
                conn.commit()

            if fetchone:
                result = cursor.fetchone()
                return dict(result) if result else None
            if fetchall:
                return [dict(row) for row in cursor.fetchall()]

            # INSERT/UPDATE с RETURNING id — вернуть id
            if cursor.description:
                row = cursor.fetchone()
                if row:
                    return row.get("id") if "id" in row else list(row.values())[0]
            return None


db = Database()
execute_query = db.execute_query
