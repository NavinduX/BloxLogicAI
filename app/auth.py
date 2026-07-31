"""
Authentication for the BloxLogicAI Streamlit app.

Flat-file user store (CSV, no database) plus password hashing and the
``st.session_state`` helpers the views use to drive the login/sign-out flow.

Password storage: a Django-style encoded string
``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>`` so the salt and hash live
in a single CSV cell. Hashing uses only the Python standard library.
"""

from __future__ import annotations

import functools
import hashlib
import hmac
import os
import threading
from datetime import datetime

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Storage location + schema
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_CSV = os.path.join(ROOT, "data", "users.csv")
COLUMNS = ["username", "email", "password", "role", "created_at"]

PBKDF2_ITERATIONS = 260_000
_ALGO = "pbkdf2_sha256"
_users_lock = threading.Lock()

MIN_PASSWORD_LENGTH = 8

# Seeded administrator (created on first run if no admin exists).
SEED_ADMIN_USERNAME = "admin"
SEED_ADMIN_EMAIL = "admin@bloxlogic.ai"
SEED_ADMIN_PASSWORD = os.environ.get("BLOXLOGIC_ADMIN_PASSWORD", "admin123")


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Return an encoded ``pbkdf2_sha256$iter$salt$hash`` string for *password*."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return f"{_ALGO}${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


@functools.lru_cache(maxsize=1)
def _dummy_hash() -> str:
    """Computed once on first use; equalises timing on the missing-user login path."""
    return hash_password("bloxlogic-timing-dummy")


def verify_password(password: str, encoded: str) -> bool:
    """Check *password* against a previously :func:`hash_password`-d string."""
    try:
        algo, iterations, salt_hex, hash_hex = encoded.split("$")
        if algo != _ALGO:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"),
            bytes.fromhex(salt_hex), int(iterations),
        )
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(digest.hex(), hash_hex)


# ---------------------------------------------------------------------------
# User store (CSV)
# ---------------------------------------------------------------------------
def load_users(path: str = USERS_CSV) -> pd.DataFrame:
    """Load the user store, creating it (with a seeded admin) if missing."""
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        pd.DataFrame(columns=COLUMNS).to_csv(path, index=False)
    ensure_seed_admin(path)
    return pd.read_csv(path, dtype=str).fillna("")


def _save_users(df: pd.DataFrame, path: str = USERS_CSV) -> None:
    df.to_csv(path, index=False)


def ensure_seed_admin(path: str = USERS_CSV) -> None:
    """Create the default admin account if no admin row exists yet."""
    try:
        df = pd.read_csv(path, dtype=str).fillna("") if os.path.exists(path) \
            else pd.DataFrame(columns=COLUMNS)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=COLUMNS)
    if not df.empty and (df["role"].str.lower() == "admin").any():
        return
    row = {
        "username": SEED_ADMIN_USERNAME,
        "email": SEED_ADMIN_EMAIL,
        "password": hash_password(SEED_ADMIN_PASSWORD),
        "role": "admin",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    _save_users(df, path)
    print(f"[auth] Seeded admin account '{SEED_ADMIN_USERNAME}' "
          f"(password '{SEED_ADMIN_PASSWORD}'). Change it after first login.")


def add_user(username: str, email: str, password: str,
             role: str = "user", path: str = USERS_CSV) -> tuple[bool, str]:
    """Append a new user. Returns ``(ok, message)`` for the UI to display."""
    username = (username or "").strip()
    email    = (email    or "").strip()
    password = (password or "").strip()
    if not username or not email or not password:
        return False, "Username, email and password are all required."
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."

    with _users_lock:
        df = load_users(path)
        if (df["username"].str.lower() == username.lower()).any():
            return False, f"Username '{username}' is already taken."
        if (df["email"].str.lower() == email.lower()).any():
            return False, "That email is already registered."

        row = {
            "username": username,
            "email": email,
            "password": hash_password(password),
            "role": role,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        _save_users(df, path)
    return True, f"Account '{username}' created. You can now log in."


def remove_user(username: str, path: str = USERS_CSV) -> tuple[bool, str]:
    """Delete a non-admin user inside the lock. Returns (ok, message)."""
    with _users_lock:
        df = load_users(path)
        row = df[df["username"].str.lower() == username.lower()]
        if row.empty:
            return False, f"User '{username}' not found."
        if row.iloc[0]["role"] == "admin":
            return False, "Admin accounts cannot be deleted."
        df = df[df["username"].str.lower() != username.lower()]
        _save_users(df, path)
    return True, f"User '{username}' removed."


def update_password(username: str, new_password: str,
                    path: str = USERS_CSV) -> tuple[bool, str]:
    """Update the password hash for an existing user inside the lock."""
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    with _users_lock:
        df = load_users(path)
        mask = df["username"].str.lower() == username.lower()
        if not mask.any():
            return False, f"User '{username}' not found."
        df.loc[mask, "password"] = hash_password(new_password)
        _save_users(df, path)
    return True, f"Password for '{username}' updated."


def update_user_email(username: str, email: str,
                      path: str = USERS_CSV) -> tuple[bool, str]:
    """Update the email for an existing user inside the lock."""
    email = (email or "").strip()
    if not email:
        return False, "Email cannot be empty."
    with _users_lock:
        df = load_users(path)
        mask = df["username"].str.lower() == username.lower()
        if not mask.any():
            return False, f"User '{username}' not found."
            
        if (df[~mask]["email"].str.lower() == email.lower()).any():
            return False, "That email is already in use by another account."
            
        df.loc[mask, "email"] = email
        _save_users(df, path)
    return True, f"Email for '{username}' updated."


def authenticate(username: str, password: str,
                 path: str = USERS_CSV) -> dict | None:
    """Return the user record (without password) on success, else ``None``."""
    username = (username or "").strip()
    password = (password or "").strip()
    df = load_users(path)
    match = df[df["username"].str.lower() == username.lower()]
    if match.empty:
        verify_password(password, _dummy_hash())  # constant-time: prevent username enumeration
        return None
    record = match.iloc[0]
    if not verify_password(password, record["password"]):
        return None
    return {"username": record["username"], "email": record["email"],
            "role": record["role"], "created_at": record["created_at"]}


# ---------------------------------------------------------------------------
# Session-state helpers
# ---------------------------------------------------------------------------
def init_session() -> None:
    """Seed the session keys the router and views rely on."""
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("page", "landing")


def login_user(record: dict) -> None:
    st.session_state.authenticated = True
    st.session_state.user = record


def logout_user() -> None:
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.page = "landing"


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated"))


def current_user() -> dict | None:
    return st.session_state.get("user")


def goto(page: str) -> None:
    """Set the active page; the caller should follow with ``st.rerun()``."""
    st.session_state.page = page
