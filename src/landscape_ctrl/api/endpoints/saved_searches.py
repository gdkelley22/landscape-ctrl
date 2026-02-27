"""
Saved search endpoint wrappers.

Legacy API actions:
    GetSavedSearches  - list saved searches
    CreateSavedSearch - create a saved search
    DeleteSavedSearch - delete a saved search
"""

from __future__ import annotations

from landscape_ctrl.api.client import LandscapeClient
from landscape_ctrl.api.models import SavedSearch


async def list_saved_searches(client: LandscapeClient) -> list[SavedSearch]:
    """List all saved searches in the account (Legacy API)."""
    data = await client.legacy_call("GetSavedSearches")
    results = data if isinstance(data, list) else data.get("results", [])
    return [SavedSearch.model_validate(s) for s in results]


async def create_saved_search(
    client: LandscapeClient,
    name: str,
    query: str,
) -> dict:
    """Create a new saved search (Legacy API)."""
    return await client.legacy_call(
        "CreateSavedSearch", {"name": name, "query": query}
    )


async def delete_saved_search(
    client: LandscapeClient,
    search_id: int,
) -> dict:
    """Delete a saved search by ID (Legacy API)."""
    return await client.legacy_call("DeleteSavedSearch", {"id": str(search_id)})
