"""
Repository endpoint wrappers.

Legacy API actions:
    GetRepositories  - list all repositories
    CreateRepository - create a new repository
    DeleteRepository - delete a repository
"""

from __future__ import annotations

from landscape_ctrl.api.client import LandscapeClient
from landscape_ctrl.api.models import Repository


async def list_repositories(client: LandscapeClient) -> list[Repository]:
    """List all repositories in the account (Legacy API)."""
    data = await client.legacy_call("GetRepositories")
    results = data if isinstance(data, list) else data.get("results", [])
    return [Repository.model_validate(r) for r in results]


async def get_repository(client: LandscapeClient, repo_id: int) -> Repository:
    """Fetch a single repository by ID."""
    data = await client.legacy_call("GetRepositories", {"id": str(repo_id)})
    if isinstance(data, list) and data:
        return Repository.model_validate(data[0])
    return Repository.model_validate(data)


async def create_repository(
    client: LandscapeClient,
    name: str,
    description: str = "",
    mode: str | None = None,
) -> dict:
    """Create a new repository (Legacy API)."""
    params: dict = {"name": name}
    if description:
        params["description"] = description
    if mode:
        params["mode"] = mode
    return await client.legacy_call("CreateRepository", params)


async def delete_repository(client: LandscapeClient, repo_id: int) -> dict:
    """Delete a repository by ID (Legacy API)."""
    return await client.legacy_call("DeleteRepository", {"id": str(repo_id)})
