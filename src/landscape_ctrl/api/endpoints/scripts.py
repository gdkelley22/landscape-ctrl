"""
Script endpoint wrappers.

REST v2 endpoints:
    GET /api/v2/scripts             - list scripts
    GET /api/v2/scripts/{id}        - get script details

Script execution uses the Legacy API action `ExecuteScript` because
REST v2 exposes script execution only through script profiles (not ad-hoc).
The legacy action allows running a script by ID against any computer query.
"""

from __future__ import annotations

from landscape_ctrl.api.client import LandscapeClient
from landscape_ctrl.api.models import ActivityResult, Script


async def list_scripts(
    client: LandscapeClient,
    limit: int = 200,
) -> list[Script]:
    """Return all available scripts in the account."""
    data = await client.get_json("/scripts", params={"limit": limit})
    results = data.get("results", data) if isinstance(data, dict) else data
    return [Script.model_validate(s) for s in results]


async def get_script(client: LandscapeClient, script_id: int) -> Script:
    """Fetch a single script by ID including its code."""
    data = await client.get_json(f"/scripts/{script_id}")
    return Script.model_validate(data)


async def execute_script(
    client: LandscapeClient,
    script_id: int,
    query: str,
    username: str,
    deliver_after: str | None = None,
    time_limit: int | None = None,
) -> list[ActivityResult]:
    """
    Run a script (by ID) on all computers matching `query`.

    Uses the legacy API `ExecuteScript` action.

    Args:
        script_id:     The Landscape script ID to execute
        query:         Computer selection query (e.g. "tag:webserver")
        username:      OS user to run the script as (e.g. "ubuntu", "root")
        deliver_after: ISO 8601 datetime to schedule future execution
        time_limit:    Override the script's default time limit (seconds)

    Returns a list of ActivityResult objects, one per matched computer.
    """
    params: dict = {
        "script_id": str(script_id),
        "query": query,
        "username": username,
    }
    if deliver_after:
        params["deliver_after"] = deliver_after
    if time_limit is not None:
        params["time_limit"] = str(time_limit)

    data = await client.legacy_call("ExecuteScript", params)

    # Legacy API returns a list of activity dicts directly
    if isinstance(data, list):
        return [ActivityResult.model_validate(a) for a in data]
    # Some versions wrap in a dict
    results = data.get("activities", data.get("results", [data]))
    return [ActivityResult.model_validate(a) for a in results]


async def get_activity_results(
    client: LandscapeClient,
    activity_ids: list[int],
) -> list[ActivityResult]:
    """
    Poll the status of activities (e.g. script execution jobs).
    Useful for checking whether a previously submitted script has completed.
    """
    ids_str = ",".join(str(i) for i in activity_ids)
    data = await client.legacy_call("GetActivities", {"id": ids_str})
    results = data if isinstance(data, list) else data.get("results", [])
    return [ActivityResult.model_validate(a) for a in results]
