"""
Administrator endpoint wrappers.

REST v2 endpoints:
    GET    /api/v2/administrators       - list administrators
    GET    /api/v2/administrators/{id}  - get administrator details
    POST   /api/v2/administrators       - create a new administrator
    DELETE /api/v2/administrators/{id}  - remove an administrator
"""

from __future__ import annotations

from landscape_ctrl.api.client import LandscapeClient
from landscape_ctrl.api.models import Administrator


async def list_administrators(client: LandscapeClient) -> list[Administrator]:
    """List all administrators in the account (REST v2)."""
    data = await client.get_json("/administrators")
    results = data.get("results", data) if isinstance(data, dict) else data
    return [Administrator.model_validate(a) for a in results]


async def get_administrator(
    client: LandscapeClient, admin_id: int
) -> Administrator:
    """Fetch a single administrator by ID."""
    data = await client.get_json(f"/administrators/{admin_id}")
    return Administrator.model_validate(data)


async def create_administrator(
    client: LandscapeClient,
    name: str,
    email: str,
) -> dict:
    """Create a new administrator (REST v2)."""
    payload = {"name": name, "email": email}
    return await client.post_json("/administrators", json=payload)


async def remove_administrator(
    client: LandscapeClient, admin_id: int
) -> dict:
    """Remove an administrator by ID (REST v2)."""
    return await client.delete_json(f"/administrators/{admin_id}")
