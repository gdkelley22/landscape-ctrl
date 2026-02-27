"""
Package management endpoint wrappers.

REST v2:
    GET /api/v2/packages   - list packages across the account

Package operations (install/remove/upgrade) use the Legacy API because
REST v2 does not yet expose mutation endpoints for packages:
    InstallPackages   - install named packages on matching computers
    RemovePackages    - remove named packages
    UpgradePackages   - upgrade named packages (or all if names omitted)
    HoldPackages      - pin packages to current version
    ReleasePackages   - remove hold
"""

from __future__ import annotations

from landscape_ctrl.api.client import LandscapeClient
from landscape_ctrl.api.models import ActivityResult, Package


async def list_packages(
    client: LandscapeClient,
    names: list[str] | None = None,
    query: str | None = None,
    installed: bool = False,
    upgrade: bool = False,
    security: bool = False,
    limit: int = 1000,
) -> list[Package]:
    """
    List packages visible across the account (REST v2).

    Args:
        names:     Filter to specific package names
        query:     Computer query to scope results (e.g. "tag:webserver")
        installed: Only show installed packages
        upgrade:   Only show packages with upgrades available
        security:  Only show security updates
        limit:     Max results (default 1000)
    """
    params: dict = {"limit": limit}
    if names:
        # REST v2 accepts repeated names.1, names.2, ... keys
        for i, name in enumerate(names, 1):
            params[f"names.{i}"] = name
    if query:
        params["query"] = query
    if installed:
        params["installed"] = "true"
    if upgrade:
        params["upgrade"] = "true"
    if security:
        params["security"] = "true"

    data = await client.get_json("/packages", params=params)
    results = data.get("results", data) if isinstance(data, dict) else data
    return [Package.model_validate(p) for p in results]


async def install_packages(
    client: LandscapeClient,
    package_names: list[str],
    query: str,
    deliver_after: str | None = None,
) -> list[ActivityResult]:
    """
    Install packages on all computers matching query (Legacy API).

    Args:
        package_names: List of package names to install (e.g. ["nginx", "curl"])
        query:         Computer selector (e.g. "tag:webserver")
        deliver_after: ISO 8601 datetime for scheduled install

    Returns one ActivityResult per matched computer.
    """
    params: dict = {"query": query}
    for i, name in enumerate(package_names, 1):
        params[f"packages.{i}"] = name
    if deliver_after:
        params["deliver_after"] = deliver_after

    data = await client.legacy_call("InstallPackages", params)
    results = data if isinstance(data, list) else data.get("activities", [data])
    return [ActivityResult.model_validate(a) for a in results]


async def remove_packages(
    client: LandscapeClient,
    package_names: list[str],
    query: str,
    deliver_after: str | None = None,
) -> list[ActivityResult]:
    """Remove packages from matching computers (Legacy API)."""
    params: dict = {"query": query}
    for i, name in enumerate(package_names, 1):
        params[f"packages.{i}"] = name
    if deliver_after:
        params["deliver_after"] = deliver_after

    data = await client.legacy_call("RemovePackages", params)
    results = data if isinstance(data, list) else data.get("activities", [data])
    return [ActivityResult.model_validate(a) for a in results]


async def upgrade_packages(
    client: LandscapeClient,
    query: str,
    package_names: list[str] | None = None,
    deliver_after: str | None = None,
) -> list[ActivityResult]:
    """
    Upgrade packages on matching computers (Legacy API).
    If package_names is omitted, ALL upgradable packages are upgraded.
    """
    params: dict = {"query": query}
    if package_names:
        for i, name in enumerate(package_names, 1):
            params[f"packages.{i}"] = name
    if deliver_after:
        params["deliver_after"] = deliver_after

    data = await client.legacy_call("UpgradePackages", params)
    results = data if isinstance(data, list) else data.get("activities", [data])
    return [ActivityResult.model_validate(a) for a in results]


async def hold_packages(
    client: LandscapeClient,
    package_names: list[str],
    query: str,
) -> list[ActivityResult]:
    """Pin packages to current version on matching computers (Legacy API)."""
    params: dict = {"query": query}
    for i, name in enumerate(package_names, 1):
        params[f"packages.{i}"] = name

    data = await client.legacy_call("HoldPackages", params)
    results = data if isinstance(data, list) else data.get("activities", [data])
    return [ActivityResult.model_validate(a) for a in results]


async def release_packages(
    client: LandscapeClient,
    package_names: list[str],
    query: str,
) -> list[ActivityResult]:
    """Remove hold from packages on matching computers (Legacy API)."""
    params: dict = {"query": query}
    for i, name in enumerate(package_names, 1):
        params[f"packages.{i}"] = name

    data = await client.legacy_call("ReleasePackages", params)
    results = data if isinstance(data, list) else data.get("activities", [data])
    return [ActivityResult.model_validate(a) for a in results]
