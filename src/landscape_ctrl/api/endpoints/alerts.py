"""
Alert endpoint wrappers.

Legacy API actions:
    GetAlerts   - list all alerts
    CreateAlert - create a new alert
    DeleteAlert - delete an alert by ID

REST v2 (if available):
    GET /api/v2/alerts       - list alerts
    GET /api/v2/alerts/{id}  - get alert details
"""

from __future__ import annotations

from landscape_ctrl.api.client import LandscapeClient
from landscape_ctrl.api.models import Alert


async def list_alerts(client: LandscapeClient) -> list[Alert]:
    """List all alerts in the account."""
    try:
        data = await client.get_json("/alerts")
        results = data.get("results", data) if isinstance(data, dict) else data
    except Exception:
        data = await client.legacy_call("GetAlerts")
        results = data if isinstance(data, list) else data.get("results", [])
    return [Alert.model_validate(a) for a in results]


async def get_alert(client: LandscapeClient, alert_id: int) -> Alert:
    """Fetch a single alert by ID."""
    data = await client.get_json(f"/alerts/{alert_id}")
    return Alert.model_validate(data)


async def create_alert(
    client: LandscapeClient,
    name: str,
    query: str,
    description: str | None = None,
) -> dict:
    """Create a new alert (Legacy API)."""
    params: dict = {"name": name, "query": query}
    if description:
        params["description"] = description
    return await client.legacy_call("CreateAlert", params)


async def delete_alert(client: LandscapeClient, alert_id: int) -> dict:
    """Delete an alert by ID (Legacy API)."""
    return await client.legacy_call("DeleteAlert", {"id": str(alert_id)})
