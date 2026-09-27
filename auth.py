"""
auth.py - Authentication system for Heart Disease Prediction App
Handles user signup, login, password hashing, and session management.
"""

import sqlite3
import hashlib
import os
import re
from functools import wraps
from flask import session, redirect, url_for, flash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")


def get_db():
    """Get a database connection."""
    # Increase timeout to reduce "database is locked" errors under concurrent access.
    # Enable WAL journal mode for better concurrency.
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        # If PRAGMA fails for any reason, ignore and continue with the connection.
        pass
    return conn


def init_db():
    """Initialize the SQLite database and create users table."""
    # Use a short-lived connection and commit immediately to avoid locking.
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with a salt."""
    salt = "hdp_secure_salt_2024"
    return hashlib.sha256((password + salt).encode()).hexdigest()


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password: str) -> tuple:
    """Validate password strength. Returns (bool, message)."""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    return True, "OK"


def signup_user(username: str, email: str, password: str) -> tuple:
    """
    Register a new user.
    Returns (success: bool, message: str)
    """
    username = username.strip()
    email = email.strip().lower()

    if not username or not email or not password:
        return False, "All fields are required."

    if len(username) < 3:
        return False, "Username must be at least 3 characters."

    if not validate_email(email):
        return False, "Invalid email format."

    valid, msg = validate_password(password)
    if not valid:
        return False, msg

    password_hash = hash_password(password)

    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )
        conn.commit()
        conn.close()
        return True, "Account created successfully! Please log in."
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return False, "Username already exists. Please choose another."
        elif "email" in str(e):
            return False, "Email already registered. Please log in."
        return False, "Registration failed. Please try again."
    except Exception as e:
        return False, f"An error occurred: {str(e)}"


def login_user(username: str, password: str) -> tuple:
    """
    Authenticate a user.
    Returns (success: bool, message: str, user_data: dict or None)
    """
    username = username.strip()

    if not username or not password:
        return False, "All fields are required.", None

    password_hash = hash_password(password)

    try:
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND password_hash = ?",
            (username, password_hash)
        ).fetchone()
        conn.close()

        if user:
            return True, "Login successful!", dict(user)
        else:
            return False, "Invalid username or password.", None
    except Exception as e:
        return False, f"An error occurred: {str(e)}", None


def get_user_by_email(email: str):
    """Retrieve a user record by email (used by Google OAuth)."""
    try:
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
        conn.close()
        return dict(user) if user else None
    except Exception:
        return None


def login_required(f):
    """Decorator to protect routes that require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function
