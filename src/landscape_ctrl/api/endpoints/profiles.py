"""
Profile endpoint wrappers.

Landscape supports multiple profile types: package, script, security,
reboot, repository, removal, upgrade. All share a common REST v2 pattern:

    GET    /api/v2/{profile_type}-profiles
    GET    /api/v2/{profile_type}-profiles/{id}
    POST   /api/v2/{profile_type}-profiles
    DELETE /api/v2/{profile_type}-profiles/{id}
"""

from __future__ import annotations

from typing import Any

from landscape_ctrl.api.client import LandscapeClient
from landscape_ctrl.api.models import Profile

PROFILE_TYPES = frozenset({
    "package", "script", "security", "reboot",
    "repository", "removal", "upgrade",
})


def _profile_path(profile_type: str) -> str:
    """Build the REST v2 URL path segment for a profile type."""
    return f"/{profile_type}-profiles"


async def list_profiles(
    client: LandscapeClient,
    profile_type: str,
    limit: int = 200,
) -> list[Profile]:
    """List profiles of a given type."""
    params: dict = {"limit": limit}
    data = await client.get_json(_profile_path(profile_type), params=params)
    results = data.get("results", data) if isinstance(data, dict) else data
    return [Profile.model_validate(p) for p in results]


async def get_profile(
    client: LandscapeClient,
    profile_type: str,
    profile_id: int,
) -> Profile:
    """Fetch a single profile by type and ID."""
    data = await client.get_json(f"{_profile_path(profile_type)}/{profile_id}")
    return Profile.model_validate(data)


async def create_profile(
    client: LandscapeClient,
    profile_type: str,
    name: str,
    description: str = "",
    extra: dict[str, Any] | None = None,
) -> dict:
    """Create a new profile."""
    payload: dict = {"name": name, "description": description}
    if extra:
        payload.update(extra)
    return await client.post_json(_profile_path(profile_type), json=payload)


async def delete_profile(
    client: LandscapeClient,
    profile_type: str,
    profile_id: int,
) -> dict:
    """Delete a profile by type and ID."""
    return await client.delete_json(f"{_profile_path(profile_type)}/{profile_id}")
