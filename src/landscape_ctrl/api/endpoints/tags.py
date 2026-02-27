"""
Tag management endpoint wrappers.

Tags in Landscape are labels applied to computers to enable group targeting
via the query syntax (e.g. "tag:webserver").

REST v2 does not have dedicated tag mutation endpoints — tag operations
use the Legacy API actions:
    AddTagsToComputers      - apply one or more tags
    RemoveTagsFromComputers - remove one or more tags
    GetTags                 - list all tags in the account

Tags are visible on Computer objects returned by /api/v2/computers
in the `tags` field.
"""

from __future__ import annotations

from landscape_ctrl.api.client import LandscapeClient


async def list_tags(client: LandscapeClient) -> list[str]:
    """Return all tags defined in the Landscape account (Legacy API)."""
    data = await client.legacy_call("GetTags")
    if isinstance(data, list):
        # Each item may be a dict with a "name" key or just a string
        return [t["name"] if isinstance(t, dict) else t for t in data]
    return []


async def add_tags(
    client: LandscapeClient,
    query: str,
    tags: list[str],
) -> dict:
    """
    Apply tags to all computers matching query.

    Args:
        query: Computer selector (e.g. "tag:db-servers" or "hostname:db-01")
        tags:  List of tag strings to apply (e.g. ["production", "mysql"])
    """
    params: dict = {"query": query}
    for i, tag in enumerate(tags, 1):
        params[f"tags.{i}"] = tag
    return await client.legacy_call("AddTagsToComputers", params)


async def remove_tags(
    client: LandscapeClient,
    query: str,
    tags: list[str],
) -> dict:
    """
    Remove tags from all computers matching query.

    Args:
        query: Computer selector
        tags:  List of tag strings to remove
    """
    params: dict = {"query": query}
    for i, tag in enumerate(tags, 1):
        params[f"tags.{i}"] = tag
    return await client.legacy_call("RemoveTagsFromComputers", params)
