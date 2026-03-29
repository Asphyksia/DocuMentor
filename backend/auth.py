"""
DocuMentor Authentication
-------------------------
Simple single-user auth with JWT tokens.
Credentials come from environment variables — no database needed.

Flow:
  1. User POSTs /auth/login with { email, password }
  2. Server validates against DOCUMENTER_EMAIL + DOCUMENTER_PASSWORD from .env
  3. Returns JWT token (also set as httpOnly cookie)
  4. WebSocket connections validate JWT from cookie or query param
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger("auth")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

AUTH_EMAIL = os.getenv("DOCUMENTER_EMAIL", "admin@documenter.local")
AUTH_PASSWORD = os.getenv("DOCUMENTER_PASSWORD", "")
SECRET_KEY = os.getenv("SECRET_KEY", "")
JWT_TTL = int(os.getenv("JWT_TTL", str(24 * 3600)))  # 24 hours default

# Auth can be disabled for development
AUTH_ENABLED = os.getenv("DOCUMENTER_AUTH", "true").lower() not in ("false", "0", "off")


def _check_config() -> list[str]:
    """Return list of config issues."""
    issues = []
    if AUTH_ENABLED and not AUTH_PASSWORD:
        issues.append("DOCUMENTER_PASSWORD not set — auth will reject all logins")
    if not SECRET_KEY:
        issues.append("SECRET_KEY not set — using insecure default for JWT signing")
    return issues


# ---------------------------------------------------------------------------
# JWT — minimal HMAC-SHA256 implementation (no external deps)
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    import base64
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _get_signing_key() -> bytes:
    key = SECRET_KEY or "documenter-insecure-default-key"
    return key.encode()


def create_token(email: str) -> str:
    """Create a JWT token for the given email."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_TTL,
    }

    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}"

    sig = hmac.new(_get_signing_key(), signing_input.encode(), hashlib.sha256).digest()
    s = _b64url_encode(sig)

    return f"{h}.{p}.{s}"


def verify_token(token: str) -> Optional[dict]:
    """Verify a JWT token. Returns payload dict or None if invalid."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        h, p, s = parts
        signing_input = f"{h}.{p}"

        expected_sig = hmac.new(
            _get_signing_key(), signing_input.encode(), hashlib.sha256
        ).digest()
        actual_sig = _b64url_decode(s)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_b64url_decode(p))

        # Check expiration
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Login validation
# ---------------------------------------------------------------------------

def validate_login(email: str, password: str) -> Optional[str]:
    """
    Validate login credentials.
    Returns JWT token string on success, None on failure.
    """
    if not AUTH_ENABLED:
        return create_token(email or "anonymous")

    if not AUTH_PASSWORD:
        logger.warning("Login attempt but DOCUMENTER_PASSWORD not configured")
        return None

    email_ok = hmac.compare_digest(email.lower().strip(), AUTH_EMAIL.lower().strip())
    password_ok = hmac.compare_digest(password, AUTH_PASSWORD)

    if email_ok and password_ok:
        logger.info("Login successful for %s", email)
        return create_token(email)

    logger.warning("Login failed for %s", email)
    return None


def validate_ws_token(token: str) -> bool:
    """Validate a token for WebSocket authentication."""
    if not AUTH_ENABLED:
        return True
    return verify_token(token) is not None


def is_auth_enabled() -> bool:
    """Check if authentication is enabled."""
    return AUTH_ENABLED
