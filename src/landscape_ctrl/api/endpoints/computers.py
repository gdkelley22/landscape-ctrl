"""
Computer / Device endpoint wrappers.

REST v2 endpoints used:
    GET  /api/v2/computers              - list with optional query filter
    GET  /api/v2/computers/{id}         - single computer details
    GET  /api/v2/computers/{id}/processes
    GET  /api/v2/computers/{id}/packages
    POST /api/v2/computers/{id}/restart
    POST /api/v2/computers/{id}/shutdown
    POST /api/v2/computers/{id}/archive
    GET  /api/v2/computers/{id}/groups
    GET  /api/v2/computers/{id}/users/{username}/groups
    GET  /api/v2/computers/activities   - activity history

Landscape query syntax for filtering computers:
    tag:webserver           machines tagged "webserver"
    hostname:db-01          exact hostname match
    distribution:ubuntu     by OS distribution
    alert:package-upgrades  computers with pending upgrades
    id:42                   specific computer by id
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from landscape_ctrl.api.client import LandscapeClient
from landscape_ctrl.api.models import ActivityResult, Computer, Package, Process


async def list_computers(
    client: LandscapeClient,
    query: str | None = None,
    tag: str | None = None,
    hostname: str | None = None,
    limit: int = 1000,
    offset: int = 0,
    with_network: bool = False,
    with_alerts: bool = False,
    with_upgrades: bool = False,
    with_hardware: bool = False,
    with_annotations: bool = False,
) -> list[Computer]:
    """
    Return a list of computers, with optional filtering.

    Args:
        query:            Raw Landscape query string (overrides tag/hostname shortcuts)
        tag:              Filter by tag name (e.g. "webserver")
        hostname:         Filter by hostname substring
        limit:            Max results to return (default 1000)
        offset:           Offset for pagination
        with_network:     Include network interface details
        with_alerts:      Include alert information
        with_upgrades:    Include upgrade counts
        with_hardware:    Include hardware details
        with_annotations: Include annotation data
    """
    params: dict = {"limit": limit}
    if offset:
        params["offset"] = offset

    if query:
        params["query"] = query
    elif tag:
        params["query"] = f"tag:{tag}"
    elif hostname:
        params["query"] = f"hostname:{hostname}"

    withs = []
    if with_network:
        withs.append("network")
    if with_alerts:
        withs.append("alerts")
    if with_upgrades:
        withs.append("upgrades")
    if with_hardware:
        withs.append("hardware")
    if with_annotations:
        withs.append("annotations")
    if withs:
        params["with"] = ",".join(withs)

    data = await client.get_json("/computers", params=params)
    results = data.get("results", data) if isinstance(data, dict) else data
    return [Computer.model_validate(c) for c in results]


async def stream_computers(
    client: LandscapeClient,
    query: str | None = None,
    tag: str | None = None,
) -> AsyncIterator[Computer]:
    """
    Async generator yielding Computer objects across all pages.
    Use this for large fleets where results exceed the page limit.
    """
    params: dict = {}
    if query:
        params["query"] = query
    elif tag:
        params["query"] = f"tag:{tag}"

    async for item in client.paginate("/computers", params=params):
        yield Computer.model_validate(item)


async def get_computer(
    client: LandscapeClient,
    computer_id: int,
    with_hardware: bool = False,
    with_annotations: bool = False,
    with_network: bool = False,
    with_profiles: bool = False,
) -> Computer:
    """Fetch detailed info for a single computer by ID."""
    params: dict = {}
    withs = []
    if with_hardware:
        withs.append("hardware")
    if with_annotations:
        withs.append("annotations")
    if with_network:
        withs.append("network")
    if with_profiles:
        withs.append("profiles")
    if withs:
        params["with"] = ",".join(withs)

    data = await client.get_json(f"/computers/{computer_id}", params=params or None)
    return Computer.model_validate(data)


async def get_processes(
    client: LandscapeClient, computer_id: int
) -> list[Process]:
    """Return the list of running processes on a computer."""
    data = await client.get_json(f"/computers/{computer_id}/processes")
    results = data.get("results", data) if isinstance(data, dict) else data
    return [Process.model_validate(p) for p in results]


async def get_packages(
    client: LandscapeClient,
    computer_id: int,
    upgrade: bool = False,
    security: bool = False,
) -> list[Package]:
    """
    Return packages on a specific computer.

    Args:
        upgrade:  Only return packages with upgrades available
        security: Only return security updates
    """
    params: dict = {}
    if upgrade:
        params["upgrade"] = "true"
    if security:
        params["security"] = "true"

    data = await client.get_json(f"/computers/{computer_id}/packages", params=params)
    results = data.get("results", data) if isinstance(data, dict) else data
    return [Package.model_validate(p) for p in results]


async def restart_computer(
    client: LandscapeClient,
    computer_id: int,
    deliver_after: str | None = None,
) -> dict:
    """
    Schedule a restart for a computer.

    Args:
        deliver_after: ISO 8601 datetime string to schedule restart.
                       If None, executes as soon as possible.

    Returns the raw activity response dict.
    """
    payload: dict = {}
    if deliver_after:
        payload["deliver_after"] = deliver_after

    return await client.post_json(f"/computers/{computer_id}/restart", json=payload)


async def shutdown_computer(
    client: LandscapeClient,
    computer_id: int,
    deliver_after: str | None = None,
) -> dict:
    """Schedule a shutdown for a computer."""
    payload: dict = {}
    if deliver_after:
        payload["deliver_after"] = deliver_after

    return await client.post_json(f"/computers/{computer_id}/shutdown", json=payload)


async def archive_computer(
    client: LandscapeClient,
    computer_id: int,
    computer_title: str | None = None,
) -> dict:
    """Archive a computer."""
    payload: dict = {}
    if computer_title:
        payload["title"] = computer_title

    return await client.post_json(f"/computers/{computer_id}/archive", json=payload)


async def get_computer_activities(
    client: LandscapeClient,
    computer_ids: list[int],
    limit: int = 100,
    offset: int = 0,
) -> list[ActivityResult]:
    """Get activities for specific computers."""
    params: dict = {
        "computer_id": ",".join(str(i) for i in computer_ids),
        "limit": str(limit),
        "offset": str(offset),
    }
    data = await client.legacy_call("GetActivities", params)
    results = data if isinstance(data, list) else data.get("results", [])
    return [ActivityResult.model_validate(a) for a in results]


async def get_computer_groups(
    client: LandscapeClient,
    computer_id: int,
) -> list[dict]:
    """Get groups a computer belongs to."""
    data = await client.get_json(f"/computers/{computer_id}/groups")
    results = data.get("results", data) if isinstance(data, dict) else data
    return results


async def get_user_groups(
    client: LandscapeClient,
    computer_id: int,
    username: str,
) -> list[str]:
    """Get groups a user belongs to on a specific computer."""
    data = await client.get_json(
        f"/computers/{computer_id}/users/{username}/groups"
    )
    if isinstance(data, list):
        return [g["name"] if isinstance(g, dict) else str(g) for g in data]
    results = data.get("results", []) if isinstance(data, dict) else []
    return [g["name"] if isinstance(g, dict) else str(g) for g in results]
