import sqlite3
import os
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_FOLDER = os.path.join(BASE_DIR, 'database')

# ✅ ensure folder exists
if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER)

DB_PATH = os.path.join(DB_FOLDER, 'digit.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                reset_token TEXT,  -- 🔹 add this line
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                prediction_type TEXT NOT NULL,
                image_path TEXT,
                predicted_digit INTEGER NOT NULL,
                confidence REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        admin = cursor.execute("SELECT * FROM admin WHERE username = 'admin'").fetchone()
        if not admin:
            hashed_pw = generate_password_hash('Admin@123')
            cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", ('admin', hashed_pw))
            conn.commit()

init_db()