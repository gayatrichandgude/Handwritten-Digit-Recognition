from werkzeug.security import generate_password_hash, check_password_hash
from backend.db import get_db

def register_user(name, email, password):
    db = get_db()
    cursor = db.cursor()
    hashed = generate_password_hash(password)
    cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                   (name, email, hashed))
    db.commit()

def login_user(email, password):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    if user and check_password_hash(user['password'], password):
        return user
    return None

def change_user_password(user_id, new_password):
    db = get_db()
    cursor = db.cursor()
    hashed = generate_password_hash(new_password)
    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
    db.commit()

def delete_user_account(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
