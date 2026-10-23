"""口令哈希、登录、会话文件与角色校验。"""

import hashlib
import hmac
import json
import os
import secrets

from db import now_iso

ITERATIONS = 120000
SESSION_PATH = os.path.join("data", "session.json")


def session_path():
    return os.environ.get("DEVICELOAN_SESSION") or SESSION_PATH


def hash_password(password, iterations=ITERATIONS):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return salt.hex(), digest.hex(), iterations


def verify_password(password, salt_hex, hash_hex, iterations):
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
    )
    return hmac.compare_digest(digest.hex(), hash_hex)


def authenticate(conn, username, password):
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    if row is None:
        return None
    if not verify_password(password, row["salt"], row["password_hash"], row["iterations"]):
        return None
    return row


def write_session(user):
    path = session_path()
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    data = {
        "username": user["username"],
        "role": user["role"],
        "created_at": now_iso(),
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    return data


def read_session():
    path = session_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not data.get("username") or not data.get("role"):
        return None
    return data


def current_user(conn):
    session = read_session()
    if session is None:
        return None
    return conn.execute(
        "SELECT * FROM users WHERE username = ?", (session["username"],)
    ).fetchone()


def has_role(user, *roles):
    return user is not None and user["role"] in roles
