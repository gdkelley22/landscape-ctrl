"""
RBAC (Role-Based Access Control) endpoint wrappers.

Legacy API actions:
    GetRoles   - list all roles
    CreateRole - create a new role with permissions
    DeleteRole - delete a role by ID
"""

from __future__ import annotations

from landscape_ctrl.api.client import LandscapeClient
from landscape_ctrl.api.models import Role


async def list_roles(client: LandscapeClient) -> list[Role]:
    """List all roles in the account (Legacy API)."""
    data = await client.legacy_call("GetRoles")
    results = data if isinstance(data, list) else data.get("results", [])
    return [Role.model_validate(r) for r in results]


async def create_role(
    client: LandscapeClient,
    name: str,
    permissions: list[str] | None = None,
) -> dict:
    """Create a new role (Legacy API)."""
    params: dict = {"name": name}
    if permissions:
        for i, perm in enumerate(permissions, 1):
            params[f"permissions.{i}"] = perm
    return await client.legacy_call("CreateRole", params)


async def delete_role(client: LandscapeClient, role_id: int) -> dict:
    """Delete a role by ID (Legacy API)."""
    return await client.legacy_call("DeleteRole", {"id": str(role_id)})
