"""
Base HTTP client for landscape-ctrl.

Wraps httpx to provide:
  - Automatic JWT Bearer auth header injection
  - Transparent 401 → re-login → retry (once)
  - HMAC-SHA256 signing for legacy API calls
  - Pagination helpers (auto-follow next cursor)
  - Consistent error handling with rich error messages
  - SSL/CA cert configuration

Usage:
    from landscape_ctrl.config import load_config
    from landscape_ctrl.api.client import LandscapeClient

    cfg = load_config()
    async with LandscapeClient(cfg) as client:
        computers = await client.get_json("/computers")
"""

from __future__ import annotations

import json
import urllib.parse
from collections.abc import AsyncIterator
from typing import Any

import httpx

from landscape_ctrl.api.auth import (
    build_access_key_login_payload,
    get_secret_key,
    sign_legacy_request,
)
from landscape_ctrl.config import LandscapeConfig, load_token, save_token


class LandscapeAPIError(Exception):
    """Raised when the Landscape API returns an error response."""

    def __init__(self, status_code: int, message: str, body: Any = None) -> None:
        self.status_code = status_code
        self.message = message
        self.body = body
        super().__init__(f"HTTP {status_code}: {message}")


class AuthError(LandscapeAPIError):
    """Raised for authentication/authorization failures."""


class LandscapeClient:
    """
    Async HTTP client for the Landscape API.

    Supports both REST v2 (JWT) and Legacy (HMAC) APIs transparently.
    Use as an async context manager:

        async with LandscapeClient(cfg) as client:
            data = await client.get_json("/computers")
    """

    def __init__(self, cfg: LandscapeConfig) -> None:
        self.cfg = cfg
        self._token: str | None = load_token()
        self._http: httpx.AsyncClient | None = None

    async def __aenter__(self) -> LandscapeClient:
        self._http = httpx.AsyncClient(
            verify=self.cfg.ssl_context(),
            timeout=30.0,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._http:
            await self._http.aclose()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    async def login_with_access_key(
        self,
        access_key: str,
        secret_key: str,
        expiry_minutes: int = 1440,
    ) -> str:
        """
        Authenticate via access-key/secret-key (Landscape 24.10+).
        Stores the JWT token for subsequent requests.
        Returns the raw JWT string.
        """
        payload = build_access_key_login_payload(access_key, secret_key, expiry_minutes)
        resp = await self._raw_post(f"{self.cfg.base_url}/login/access-key", json=payload)
        token = resp["token"]
        self._token = token
        save_token(token)
        return token

    async def login_with_email(
        self,
        email: str,
        password: str,
        account: str,
        expiry_minutes: int = 1440,
    ) -> str:
        """
        Authenticate via email/password.
        Returns the raw JWT string.
        """
        payload = {
            "email": email,
            "password": password,
            "account": account,
            "expiry_minutes": expiry_minutes,
        }
        resp = await self._raw_post(f"{self.cfg.base_url}/login", json=payload)
        token = resp["token"]
        self._token = token
        save_token(token)
        return token

    def _auth_headers(self) -> dict[str, str]:
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}

    # ------------------------------------------------------------------
    # REST v2 requests
    # ------------------------------------------------------------------

    async def get_json(self, path: str, params: dict | None = None) -> Any:
        """GET {base_url}{path} with JWT auth. Returns parsed JSON."""
        return await self._request_with_retry("GET", self.cfg.base_url + path, params=params)

    async def post_json(self, path: str, json: dict | None = None) -> Any:
        """POST {base_url}{path} with JWT auth. Returns parsed JSON."""
        return await self._request_with_retry("POST", self.cfg.base_url + path, json=json)

    async def put_json(self, path: str, json: dict | None = None) -> Any:
        """PUT {base_url}{path} with JWT auth. Returns parsed JSON."""
        return await self._request_with_retry("PUT", self.cfg.base_url + path, json=json)

    async def delete_json(self, path: str, json: dict | None = None) -> Any:
        """DELETE {base_url}{path} with JWT auth. Returns parsed JSON."""
        return await self._request_with_retry("DELETE", self.cfg.base_url + path, json=json)

    async def _request_with_retry(
        self, method: str, url: str, **kwargs: Any
    ) -> Any:
        """Send request. On 401, attempt token refresh and retry once."""
        resp = await self._send(method, url, **kwargs)
        if resp.status_code == 401 and self.cfg.access_key:
            # Token may have expired — try refreshing
            secret_key = get_secret_key()
            if secret_key:
                await self.login_with_access_key(self.cfg.access_key, secret_key)
                resp = await self._send(method, url, **kwargs)
        return self._handle_response(resp)

    async def _send(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        assert self._http is not None, "Client must be used as async context manager"
        headers = {**self._auth_headers(), **kwargs.pop("headers", {})}
        return await self._http.request(method, url, headers=headers, **kwargs)

    async def _raw_post(self, url: str, json: dict) -> Any:
        """POST without auth headers (used for login endpoints)."""
        assert self._http is not None
        resp = await self._http.post(url, json=json)
        return self._handle_response(resp)

    def _handle_response(self, resp: httpx.Response) -> Any:
        if resp.status_code in (200, 201, 204):
            if resp.content:
                try:
                    return resp.json()
                except (ValueError, json.JSONDecodeError):
                    return {}
            return {}
        if resp.status_code in (401, 403):
            raise AuthError(resp.status_code, "Authentication failed. Run: lsctl login")
        try:
            body = resp.json()
            message = body.get("message") or body.get("error") or str(body)
        except Exception:
            message = resp.text
        raise LandscapeAPIError(resp.status_code, message, body=resp.text)

    # ------------------------------------------------------------------
    # Pagination helper
    # ------------------------------------------------------------------

    async def paginate(
        self,
        path: str,
        params: dict | None = None,
        key: str = "results",
    ) -> AsyncIterator[Any]:
        """
        Async generator that yields individual items from a paginated endpoint.

        Follows the `next` cursor automatically until exhausted.

        Usage:
            async for computer in client.paginate("/computers"):
                print(computer["hostname"])
        """
        params = dict(params or {})
        url: str | None = self.cfg.base_url + path

        while url:
            data = await self._request_with_retry("GET", url, params=params)
            items = data.get(key, data) if isinstance(data, dict) else data
            for item in items:
                yield item
            next_url = data.get("next") if isinstance(data, dict) else None
            url = next_url
            params = {}  # next URL already contains params

    # ------------------------------------------------------------------
    # Legacy API (HMAC-SHA256 signed)
    # ------------------------------------------------------------------

    async def legacy_call(self, action: str, params: dict | None = None) -> Any:
        """
        Call a Landscape legacy API action (HMAC-SHA256 signed GET).

        Example actions: GetComputers, ExecuteScript, AddTagsToComputers,
                         InstallPackages, GetActivities

        Landscape legacy API is a single endpoint at /api/ that dispatches
        based on the `action` query parameter.
        """
        assert self._http is not None
        params = dict(params or {})
        params["action"] = action

        secret_key = get_secret_key()
        if not secret_key:
            raise AuthError(
                0,
                "No secret key found. Run: lsctl config set --secret-key YOUR_SECRET",
            )

        parsed = urllib.parse.urlparse(self.cfg.legacy_url)
        hostname = parsed.netloc
        path = parsed.path

        signed_params = sign_legacy_request(
            method="GET",
            hostname=hostname,
            path=path,
            params=params,
            access_key=self.cfg.access_key,
            secret_key=secret_key,
        )

        resp = await self._http.get(self.cfg.legacy_url, params=signed_params)
        return self._handle_response(resp)
