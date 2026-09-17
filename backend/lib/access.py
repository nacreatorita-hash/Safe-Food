"""Authentication and authorization boundary for the private admin surface.

The only configured account is the administrator account from the backend
environment. Sessions are signed, short-lived, and stored in an HttpOnly
cookie so the browser never needs to handle a bearer token directly.
"""

import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from fastapi import HTTPException, Request

SESSION_COOKIE = "food_alert_session"
PASSWORD_SCHEME = "pbkdf2_sha256"
DEFAULT_SESSION_TTL_SECONDS = 8 * 60 * 60


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def admin_email() -> str:
    return os.environ.get("ADMIN_EMAIL", "").strip().lower()


def session_ttl_seconds() -> int:
    try:
        return max(300, int(os.environ.get("ADMIN_SESSION_TTL_SECONDS", DEFAULT_SESSION_TTL_SECONDS)))
    except ValueError:
        return DEFAULT_SESSION_TTL_SECONDS


def _session_secret() -> str:
    return os.environ.get("ADMIN_SESSION_SECRET", "").strip()


def _password_matches(password: str) -> bool:
    stored = os.environ.get("ADMIN_PASSWORD_HASH", "").strip()
    try:
        scheme, iterations_value, salt_value, digest_value = stored.split("$", 3)
        iterations = int(iterations_value)
        if scheme != PASSWORD_SCHEME or iterations < 100_000:
            return False
        salt = _b64decode(salt_value)
        expected = _b64decode(digest_value)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, binascii.Error):
        return False


def verify_admin_credentials(email: str, password: str) -> bool:
    configured_email = admin_email()
    if not configured_email or not _session_secret() or not os.environ.get("ADMIN_PASSWORD_HASH"):
        return False
    return hmac.compare_digest(email.strip().lower(), configured_email) and _password_matches(password)


def issue_admin_session(email: str) -> str:
    secret = _session_secret()
    if len(secret) < 32:
        raise RuntimeError("ADMIN_SESSION_SECRET deve contenere almeno 32 caratteri")

    now = int(time.time())
    payload = {"sub": email.strip().lower(), "role": "admin", "iat": now, "exp": now + session_ttl_seconds()}
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _b64encode(hmac.new(secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest())
    return f"{encoded_payload}.{signature}"


def get_admin_session(request: Request) -> dict[str, Any]:
    token = request.cookies.get(SESSION_COOKIE, "")
    secret = _session_secret()
    if not token or len(secret) < 32:
        raise HTTPException(status_code=401, detail="Accesso amministrativo richiesto")

    try:
        encoded_payload, supplied_signature = token.split(".", 1)
        expected_signature = _b64encode(
            hmac.new(secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise ValueError("firma non valida")
        payload = json.loads(_b64decode(encoded_payload))
        if not isinstance(payload, dict):
            raise ValueError("payload non valido")
        if payload.get("role") != "admin" or payload.get("sub") != admin_email():
            raise ValueError("ruolo non valido")
        if int(payload.get("exp", 0)) <= int(time.time()):
            raise ValueError("sessione scaduta")
        return payload
    except (ValueError, TypeError, binascii.Error, json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="Sessione amministrativa non valida o scaduta") from None


def require_admin_access(request: Request) -> dict[str, Any]:
    """FastAPI dependency used by every admin endpoint."""

    return get_admin_session(request)


def cookie_is_secure(request: Request) -> bool:
    """Use Secure cookies only when the current request is HTTPS."""

    return request.url.scheme == "https"


def cookie_samesite(request: Request) -> str:
    """Allow the hosted frontend to send the admin cookie to the API cross-site."""

    if cookie_is_secure(request) and os.environ.get("APP_ENV", "").strip().lower() == "production":
        return "none"
    return "lax"


def new_session_secret() -> str:
    """Small helper for local setup scripts; never called by the web request path."""

    return secrets.token_urlsafe(32)
