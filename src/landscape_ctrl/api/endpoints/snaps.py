"""
Snap package endpoint wrappers.

REST v2 endpoints:
    GET /api/v2/computers/{id}/snaps/installed  - list installed snaps on a computer
"""

from __future__ import annotations

from landscape_ctrl.api.client import LandscapeClient
from landscape_ctrl.api.models import Snap


async def list_installed_snaps(
    client: LandscapeClient,
    computer_id: int,
    limit: int | None = None,
) -> list[Snap]:
    """
    List installed snaps on a specific computer (REST v2).

    Args:
        computer_id: The Landscape computer ID
        limit:       Max results to return
    """
    params: dict = {}
    if limit is not None:
        params["limit"] = limit

    data = await client.get_json(
        f"/computers/{computer_id}/snaps/installed", params=params
    )
    results = data.get("results", data) if isinstance(data, dict) else data
    return [Snap.model_validate(s) for s in results]
