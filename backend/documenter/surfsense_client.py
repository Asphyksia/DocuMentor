"""
SurfSense HTTP Client
---------------------
Encapsulates all communication with the SurfSense backend.
Handles authentication, token lifecycle, and request retries.

This is the ONLY module that knows about SurfSense URLs and auth.
Everything else goes through this client.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger("documenter.surfsense")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SURFSENSE_BASE = os.getenv("SURFSENSE_BASE_URL", "http://localhost:8929")
SURFSENSE_EMAIL = os.getenv("SURFSENSE_EMAIL", "admin@documenter.local")
SURFSENSE_PASSWORD = os.getenv("SURFSENSE_PASSWORD", "admin")
TOKEN_TTL = int(os.getenv("TOKEN_TTL", "3300"))  # 55 min
REQUEST_TIMEOUT = int(os.getenv("MCP_REQUEST_TIMEOUT", "120"))


class SurfSenseClient:
    """Authenticated HTTP client for the SurfSense API."""

    def __init__(self) -> None:
        self._http: httpx.AsyncClient | None = None
        self._token: str | None = None
        self._token_expires: float = 0

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(REQUEST_TIMEOUT, connect=10),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return self._http

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # -- Auth ---------------------------------------------------------------

    async def authenticate(self) -> str:
        resp = await self.http.post(
            f"{SURFSENSE_BASE}/auth/jwt/login",
            data={"username": SURFSENSE_EMAIL, "password": SURFSENSE_PASSWORD},
        )
        if resp.status_code != 200:
            self._token = None
            raise SurfSenseError(f"Auth failed ({resp.status_code})")
        self._token = resp.json()["access_token"]
        self._token_expires = time.time() + TOKEN_TTL
        logger.info("Authenticated (TTL %ds)", TOKEN_TTL)
        return self._token

    async def get_token(self) -> str:
        if self._token and time.time() < self._token_expires:
            return self._token
        return await self.authenticate()

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    # -- Request helper -----------------------------------------------------

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: Any = None,
        data: dict | None = None,
        files: Any = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Authenticated request with auto-retry on 401."""
        token = await self.get_token()
        url = f"{SURFSENSE_BASE}{path}"
        kwargs: dict[str, Any] = {"headers": self._auth_headers(token)}
        if params:
            kwargs["params"] = params
        if json_body is not None:
            kwargs["json"] = json_body
        if data is not None:
            kwargs["data"] = data
        if files is not None:
            kwargs["files"] = files
        if timeout is not None:
            kwargs["timeout"] = timeout

        resp = await getattr(self.http, method.lower())(url, **kwargs)

        if resp.status_code == 401:
            logger.warning("401 received, re-authenticating...")
            token = await self.authenticate()
            kwargs["headers"] = self._auth_headers(token)
            resp = await getattr(self.http, method.lower())(url, **kwargs)

        resp.raise_for_status()
        return resp

    async def stream(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        timeout: float | None = None,
    ):
        """Return an async streaming context manager."""
        token = await self.get_token()
        url = f"{SURFSENSE_BASE}{path}"
        return self.http.stream(
            method,
            url,
            headers=self._auth_headers(token),
            json=json_body,
            timeout=timeout or REQUEST_TIMEOUT,
        )

    # -- Health -------------------------------------------------------------

    async def health_check(self) -> bool:
        try:
            resp = await self.http.get(f"{SURFSENSE_BASE}/health", timeout=10)
            return resp.status_code == 200
        except Exception:
            return False


class SurfSenseError(Exception):
    """Raised when SurfSense returns an error."""
    pass


# Singleton instance
client = SurfSenseClient()
