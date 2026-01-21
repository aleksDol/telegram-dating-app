# database.py
import sqlite3
import json
from datetime import datetime
import threading
from contextlib import contextmanager

from config import config


class Database:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        self.conn = sqlite3.connect('dating.db', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для соединения с БД"""
        try:
            yield self.conn
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e

    def create_tables(self):
        """Создание всех таблиц"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Таблица пользователей
            cursor.execute('''CREATE TABLE IF NOT EXISTS users
                             (user_id INTEGER PRIMARY KEY, 
                              username TEXT,
                              name TEXT, 
                              age INTEGER,
                              gender TEXT,
                              city TEXT,
                              relationship_status TEXT,
                              photo TEXT,
                              purpose TEXT DEFAULT 'куда-то сходить',
                              reg_date TEXT,
                              points INTEGER DEFAULT 0,
                              last_active DATE,
                              favorite_categories TEXT DEFAULT '[]',
                              referral_code TEXT UNIQUE,
                              referred_by INTEGER DEFAULT NULL,
                              referrals_count INTEGER DEFAULT 0,
                              is_banned BOOLEAN DEFAULT 0,
                              ban_reason TEXT,
                              banned_date TEXT)''')

            # Таблица событий
            cursor.execute('''CREATE TABLE IF NOT EXISTS events
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
                              user_id INTEGER,
                              title TEXT,
                              description TEXT,
                              event_date TEXT,
                              target_gender TEXT DEFAULT 'Все',
                              city TEXT,
                              category TEXT,
                              created TEXT,
                              is_hidden BOOLEAN DEFAULT 0)''')

            # Таблица лайков
            cursor.execute('''CREATE TABLE IF NOT EXISTS likes
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
                              from_user INTEGER,
                              to_user INTEGER,
                              event_id INTEGER,
                              mutual BOOLEAN DEFAULT 0,
                              created TEXT)''')

            # Таблица достижений
            cursor.execute('''CREATE TABLE IF NOT EXISTS achievements
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
                              user_id INTEGER,
                              achievement_id TEXT,
                              unlocked_date TEXT,
                              FOREIGN KEY (user_id) REFERENCES users(user_id))''')

            # Таблица предпочтений пользователя
            cursor.execute('''CREATE TABLE IF NOT EXISTS user_preferences
                             (user_id INTEGER PRIMARY KEY,
                              liked_categories TEXT DEFAULT '[]',
                              disliked_categories TEXT DEFAULT '[]',
                              preferred_time TEXT DEFAULT 'Вечер',
                              FOREIGN KEY (user_id) REFERENCES users(user_id))''')

            # Таблицы для админ-панели
            cursor.execute('''CREATE TABLE IF NOT EXISTS admin_broadcasts
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
                              admin_id INTEGER,
                              content_type TEXT,
                              content TEXT,
                              caption TEXT,
                              filters TEXT,
                              total_users INTEGER DEFAULT 0,
                              sent_users INTEGER DEFAULT 0,
                              failed_users INTEGER DEFAULT 0,
                              status TEXT DEFAULT 'pending',
                              created TEXT,
                              completed TEXT)''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS admin_logs
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
                              admin_id INTEGER,
                              action TEXT,
                              details TEXT,
                              created TEXT)''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS bans
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
                              user_id INTEGER UNIQUE,
                              reason TEXT,
                              banned_by INTEGER,
                              banned_date TEXT,
                              expires TEXT)''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS reports
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
                              reporter_id INTEGER,
                              reported_user_id INTEGER,
                              reason TEXT,
                              status TEXT DEFAULT 'pending',
                              admin_notes TEXT,
                              created TEXT,
                              resolved TEXT,
                              appeal_status TEXT DEFAULT 'none',
                              appeal_text TEXT,
                              FOREIGN KEY (reporter_id) REFERENCES users(user_id),
                              FOREIGN KEY (reported_user_id) REFERENCES users(user_id))''')

    def execute_query(self, query, params=(), fetchone=False, fetchall=False, commit=False):
        """Выполнение SQL запроса"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)

            if commit:
                conn.commit()

            if fetchone:
                result = cursor.fetchone()
                if result:
                    result = dict(result)
                return result
            elif fetchall:
                results = cursor.fetchall()
                return [dict(row) for row in results]
            else:
                return cursor.lastrowid


# Синглтон для БД
db = Database()
execute_query = db.execute_query
