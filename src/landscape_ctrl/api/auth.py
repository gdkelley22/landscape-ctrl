"""
Authentication helpers for both Landscape API versions.

REST v2 (Landscape 24.04+):
    POST /api/v2/login  →  JWT Bearer token (24h default)
    POST /api/v2/login/access-key  →  JWT Bearer token

Legacy API (all versions):
    Every request is signed with HMAC-SHA256 using access_key + secret_key.
    Parameters are sorted, canonicalized, signed, and appended as ?Signature=...

Secret key storage priority:
    1. OS keychain (keyring) — most secure, never touches disk
    2. Environment variable LANDSCAPE_SECRET_KEY — for CI/CD pipelines
    3. Falls back to prompting the user
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import urllib.parse
from datetime import UTC, datetime

import keyring

KEYRING_SERVICE = "lsctl"
KEYRING_USERNAME = "secret_key"


# ---------------------------------------------------------------------------
# Secret key — OS keychain
# ---------------------------------------------------------------------------


def store_secret_key(secret_key: str) -> None:
    """Persist the secret key in the OS keychain (never written to disk)."""
    keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, secret_key)


def get_secret_key() -> str | None:
    """
    Retrieve secret key from (in order):
    1. OS keychain
    2. Environment variable LANDSCAPE_SECRET_KEY
    """
    # Try OS keychain first
    key = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    if key:
        return key
    # Fall back to environment variable (useful for CI)
    return os.environ.get("LANDSCAPE_SECRET_KEY")


def delete_secret_key() -> None:
    """Remove secret key from OS keychain on logout."""
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
    except keyring.errors.PasswordDeleteError:
        pass


# ---------------------------------------------------------------------------
# REST v2 — JWT login
# ---------------------------------------------------------------------------


def build_login_payload(
    email: str,
    password: str,
    account: str,
    expiry_minutes: int = 1440,
) -> dict:
    """Build the JSON body for POST /api/v2/login."""
    return {
        "email": email,
        "password": password,
        "account": account,
        "expiry_minutes": expiry_minutes,
    }


def build_access_key_login_payload(
    access_key: str,
    secret_key: str,
    expiry_minutes: int = 1440,
) -> dict:
    """Build the JSON body for POST /api/v2/login/access-key."""
    return {
        "access_key": access_key,
        "secret_key": secret_key,
        "expiry_minutes": expiry_minutes,
    }


# ---------------------------------------------------------------------------
# Legacy API — HMAC-SHA256 request signing
# ---------------------------------------------------------------------------


def _percent_encode(value: str) -> str:
    """RFC 3986 percent-encoding (urllib.parse.quote with safe='')."""
    return urllib.parse.quote(str(value), safe="")


def sign_legacy_request(
    method: str,
    hostname: str,
    path: str,
    params: dict,
    access_key: str,
    secret_key: str,
) -> dict:
    """
    Add HMAC-SHA256 signature to a legacy API request parameter dict.

    The signing process (per Landscape docs):
      1. Sort params alphabetically by key
      2. Percent-encode keys and values per RFC 3986
      3. Join as key=value pairs separated by &
      4. Build the string-to-sign:
             METHOD\\n
             hostname\\n
             path\\n
             canonicalized_params
      5. HMAC-SHA256(secret_key, string_to_sign) → Base64

    Returns a new dict with Signature appended.
    """
    # Required params added here so they are part of the signature
    params = dict(params)
    params["access_key_id"] = access_key
    params["signature_method"] = "HmacSHA256"
    params["signature_version"] = "2"
    params["timestamp"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    params["version"] = "2011-08-01"

    # Canonicalize: sort by key, percent-encode both key and value
    sorted_pairs = sorted(params.items(), key=lambda x: x[0])
    canonicalized = "&".join(
        f"{_percent_encode(k)}={_percent_encode(v)}" for k, v in sorted_pairs
    )

    string_to_sign = "\n".join([method.upper(), hostname, path, canonicalized])

    raw_sig = hmac.new(
        secret_key.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    params["signature"] = base64.b64encode(raw_sig).decode("utf-8")
    return params
