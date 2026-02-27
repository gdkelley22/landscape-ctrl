"""
Event log endpoint wrappers.

Legacy API actions:
    GetEventLog - retrieve event log entries with optional filtering
"""

from __future__ import annotations

from landscape_ctrl.api.client import LandscapeClient
from landscape_ctrl.api.models import EventLogEntry


async def get_event_log(
    client: LandscapeClient,
    query: str | None = None,
    limit: int = 100,
) -> list[EventLogEntry]:
    """
    Retrieve event log entries (Legacy API).

    Args:
        query: Optional filter query
        limit: Max entries to return
    """
    params: dict = {"limit": str(limit)}
    if query:
        params["query"] = query

    data = await client.legacy_call("GetEventLog", params)
    results = data if isinstance(data, list) else data.get("results", [])
    return [EventLogEntry.model_validate(e) for e in results]
