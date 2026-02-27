"""
Activity endpoint wrappers.

Legacy API actions:
    GetActivities     - list activities with optional filtering
    GetActivityTypes  - list all activity type names
    CancelActivities  - cancel pending activities
    ApproveActivities - approve activities awaiting approval
"""

from __future__ import annotations

from landscape_ctrl.api.client import LandscapeClient
from landscape_ctrl.api.models import ActivityResult


async def list_activities(
    client: LandscapeClient,
    query: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[ActivityResult]:
    """
    List activities with optional filtering (Legacy API).

    Args:
        query:  Computer query to scope results
        limit:  Max results to return
        offset: Offset for pagination
    """
    params: dict = {"limit": str(limit), "offset": str(offset)}
    if query:
        params["query"] = query

    data = await client.legacy_call("GetActivities", params)
    results = data if isinstance(data, list) else data.get("results", [])
    return [ActivityResult.model_validate(a) for a in results]


async def get_activity_types(client: LandscapeClient) -> list[str]:
    """Return all activity type names (Legacy API)."""
    data = await client.legacy_call("GetActivityTypes")
    if isinstance(data, list):
        return [t["name"] if isinstance(t, dict) else str(t) for t in data]
    return []


async def cancel_activities(
    client: LandscapeClient,
    query: str,
) -> dict:
    """Cancel pending activities matching query (Legacy API)."""
    return await client.legacy_call("CancelActivities", {"query": query})


async def approve_activities(
    client: LandscapeClient,
    query: str,
) -> dict:
    """Approve activities awaiting approval (Legacy API)."""
    return await client.legacy_call("ApproveActivities", {"query": query})
