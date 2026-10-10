"""
auth.py
Simple username + password accounts with server-side session tokens.

- Passwords are never stored: only a salted PBKDF2-SHA256 hash.
- Logging in/registering returns a random token; the frontend sends it
  as "Authorization: Bearer <token>" on every request.
- Tokens live in the sessions table and expire after SESSION_DAYS.
- Uses only the Python standard library (no extra packages).
"""

import hashlib
import hmac
import os
import secrets
import sqlite3

from fastapi import Header, HTTPException

from database import get_connection

PBKDF2_ITERATIONS = 200_000
SESSION_DAYS = 7


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return hmac.compare_digest(digest.hex(), digest_hex)


def validate_new_credentials(username: str, password: str):
    if len(username) < 3 or len(username) > 50:
        raise HTTPException(status_code=400, detail="Username must be 3 to 50 characters")
    if any(ch.isspace() for ch in username):
        raise HTTPException(status_code=400, detail="Username cannot contain spaces")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if len(password) > 128:
        raise HTTPException(status_code=400, detail="Password is too long (max 128 characters)")


def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    conn = get_connection()
    conn.execute("DELETE FROM sessions WHERE created_at < datetime('now', ?)", (f"-{SESSION_DAYS} days",))
    conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
    conn.commit()
    conn.close()
    return token


def register_user(username: str, password: str):
    username = username.strip()
    validate_new_credentials(username, password)

    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hash_password(password)),
        )
        conn.commit()
        user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="That username is already taken")
    finally:
        conn.close()

    return user_id, username


def login_user(username: str, password: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?",
        (username.strip(),),
    ).fetchone()
    conn.close()

    # Same message for "no such user" and "wrong password" on purpose.
    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return row["id"], row["username"]


def extract_token(authorization: str) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Please log in")
    return authorization[7:].strip()


def get_current_user(authorization: str = Header(None)) -> int:
    """FastAPI dependency: returns the logged-in user's id or raises 401."""
    token = extract_token(authorization)
    conn = get_connection()
    row = conn.execute(
        "SELECT user_id FROM sessions WHERE token = ? AND created_at > datetime('now', ?)",
        (token, f"-{SESSION_DAYS} days"),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again")
    return row["user_id"]


def delete_session(token: str):
    conn = get_connection()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


def get_username(user_id: int) -> str:
    conn = get_connection()
    row = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row["username"] if row else ""
