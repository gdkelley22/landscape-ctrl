"""
GPG key endpoint wrappers.

REST v2:
    GET /api/v2/gpg-keys  - list GPG keys

Legacy API:
    ImportGPGKey - import a GPG key
"""

from __future__ import annotations

from landscape_ctrl.api.client import LandscapeClient
from landscape_ctrl.api.models import GPGKey


async def list_gpg_keys(client: LandscapeClient) -> list[GPGKey]:
    """List all GPG keys in the account (REST v2)."""
    data = await client.get_json("/gpg-keys")
    results = data.get("results", data) if isinstance(data, dict) else data
    return [GPGKey.model_validate(k) for k in results]


async def import_gpg_key(
    client: LandscapeClient,
    key_material: str,
) -> dict:
    """Import a GPG key (Legacy API)."""
    return await client.legacy_call("ImportGPGKey", {"material": key_material})
