"""
Token endpoint wrappers.

REST v2 endpoints:
    GET    /api/v2/tokens       - list tokens
    POST   /api/v2/tokens       - create a new token
    DELETE /api/v2/tokens/{id}  - revoke a token
"""

from __future__ import annotations

from landscape_ctrl.api.client import LandscapeClient
from landscape_ctrl.api.models import Token


async def list_tokens(client: LandscapeClient) -> list[Token]:
    """List all tokens in the account (REST v2)."""
    data = await client.get_json("/tokens")
    results = data.get("results", data) if isinstance(data, dict) else data
    return [Token.model_validate(t) for t in results]


async def create_token(client: LandscapeClient, title: str = "") -> dict:
    """Create a new token (REST v2)."""
    payload: dict = {}
    if title:
        payload["title"] = title
    return await client.post_json("/tokens", json=payload)


async def revoke_token(client: LandscapeClient, token_id: int) -> dict:
    """Revoke a token by ID (REST v2)."""
    return await client.delete_json(f"/tokens/{token_id}")
