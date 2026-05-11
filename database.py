import sqlite3
from datetime import datetime

DB_NAME = "database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE,
                    password_hash TEXT,
                    role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY,
                    camera_name TEXT,
                    timestamp TEXT,
                    file_path TEXT,
                    description TEXT)''')
    # demo admin
    c.execute("INSERT OR IGNORE INTO users VALUES (1, 'admin', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'admin')")  # password: password
    conn.commit()
    conn.close()

def get_db():
    return sqlite3.connect(DB_NAME)