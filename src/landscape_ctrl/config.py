"""
Configuration management for landscape-ctrl.

Config file lives at: ~/.config/lsctl/config.toml
Token cache lives at: ~/.local/share/lsctl/token

Config file example:
    [landscape]
    url = "https://landscape.example.com"
    account = "standalone"
    ssl_ca_file = ""          # path to custom CA cert, empty = system default
    api_version = "v2"        # "v2" (REST, Landscape 24.04+) or "legacy"
    verify_ssl = true

    [auth]
    access_key = "YOUR_ACCESS_KEY"   # stored here OR in OS keychain (keyring)
    # secret_key is always stored in the OS keychain, never in the config file
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import tomli_w
from platformdirs import user_config_dir, user_data_dir

APP_NAME = "lsctl"
CONFIG_DIR = Path(user_config_dir(APP_NAME))
DATA_DIR = Path(user_data_dir(APP_NAME))
CONFIG_FILE = CONFIG_DIR / "config.toml"
TOKEN_FILE = DATA_DIR / "token"


# ---------------------------------------------------------------------------
# Data class (not Pydantic — no runtime dep needed here, stdlib only)
# ---------------------------------------------------------------------------


class LandscapeConfig:
    """Holds all runtime configuration for landscape-ctrl."""

    def __init__(
        self,
        url: str,
        account: str = "standalone",
        ssl_ca_file: str = "",
        api_version: str = "v2",
        verify_ssl: bool = True,
        access_key: str = "",
        secret_key: str = "",
    ) -> None:
        self.url = url.rstrip("/")
        self.account = account
        self.ssl_ca_file = ssl_ca_file
        self.api_version = api_version  # "v2" or "legacy"
        self.verify_ssl = verify_ssl
        self.access_key = access_key
        self.secret_key = secret_key  # populated from keyring at runtime

    @property
    def base_url(self) -> str:
        if self.api_version == "v2":
            return f"{self.url}/api/v2"
        return f"{self.url}/api"

    @property
    def legacy_url(self) -> str:
        """Always return the legacy API base URL (needed for some operations)."""
        return f"{self.url}/api"

    def ssl_context(self):
        """Return the value to pass to httpx's verify= parameter."""
        if not self.verify_ssl:
            return False
        if self.ssl_ca_file:
            return self.ssl_ca_file
        return True  # use system CA bundle

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"LandscapeConfig(url={self.url!r}, account={self.account!r}, "
            f"api_version={self.api_version!r})"
        )


# ---------------------------------------------------------------------------
# Disk I/O
# ---------------------------------------------------------------------------


def config_exists() -> bool:
    return CONFIG_FILE.exists()


def load_config() -> LandscapeConfig:
    """
    Load config from CONFIG_FILE.  Raises FileNotFoundError if not set up yet.
    Secret key is loaded from the OS keychain separately (see auth.py).
    """
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"No config found at {CONFIG_FILE}.\n"
            "Run:  lsctl config set --url https://your-landscape-host.example.com"
        )

    with open(CONFIG_FILE, "rb") as f:
        data = tomllib.load(f)

    ls = data.get("landscape", {})
    auth = data.get("auth", {})

    return LandscapeConfig(
        url=ls.get("url", ""),
        account=ls.get("account", "standalone"),
        ssl_ca_file=ls.get("ssl_ca_file", ""),
        api_version=ls.get("api_version", "v2"),
        verify_ssl=ls.get("verify_ssl", True),
        access_key=auth.get("access_key", ""),
    )


def save_config(cfg: LandscapeConfig) -> None:
    """Persist config to disk. Secret key is NEVER written here."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "landscape": {
            "url": cfg.url,
            "account": cfg.account,
            "ssl_ca_file": cfg.ssl_ca_file,
            "api_version": cfg.api_version,
            "verify_ssl": cfg.verify_ssl,
        },
        "auth": {
            "access_key": cfg.access_key,
        },
    }
    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(data, f)


# ---------------------------------------------------------------------------
# Token cache
# ---------------------------------------------------------------------------


def save_token(token: str) -> None:
    """Cache the JWT token to disk so login isn't needed every invocation."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token)
    TOKEN_FILE.chmod(0o600)  # owner read/write only


def load_token() -> str | None:
    """Return cached JWT token, or None if not present."""
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip() or None
    return None


def clear_token() -> None:
    """Remove cached JWT token (logout)."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
