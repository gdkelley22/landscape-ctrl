"""
User management endpoint wrappers.

REST v2:
    GET    /api/v2/users    - list users on specified computers
    POST   /api/v2/users    - add user to computers
    PUT    /api/v2/users    - modify user on computers
    DELETE /api/v2/users    - remove users from computers
    POST   /api/v2/users/lock
    POST   /api/v2/users/unlock
"""

from __future__ import annotations

from landscape_ctrl.api.client import LandscapeClient
from landscape_ctrl.api.models import OSUser


async def list_users(
    client: LandscapeClient,
    computer_ids: list[int],
) -> list[OSUser]:
    """
    List OS users on the specified computers.

    Args:
        computer_ids: List of computer IDs to query users for.
    """
    params = {"computer_id": ",".join(str(i) for i in computer_ids)}
    data = await client.get_json("/users", params=params)
    results = data.get("results", data) if isinstance(data, dict) else data
    return [OSUser.model_validate(u) for u in results]


async def add_user(
    client: LandscapeClient,
    computer_ids: list[int],
    username: str,
    password: str,
    name: str = "",
    email: str = "",
    primary_group_name: str = "",
    home: str = "",
    shell: str = "/bin/bash",
) -> dict:
    """
    Add a new OS user to the specified computers.

    Args:
        computer_ids:        IDs of computers to add the user to
        username:            Login name (e.g. "deploy")
        password:            Initial password (hashed server-side)
        name:                Full name / GECOS field
        email:               Email address
        primary_group_name:  Primary group name (defaults to username)
        home:                Home directory path
        shell:               Login shell
    """
    payload: dict = {
        "computer_ids": computer_ids,
        "username": username,
        "password": password,
        "name": name,
        "email": email,
        "primary_group_name": primary_group_name or username,
        "home": home or f"/home/{username}",
        "shell": shell,
    }
    return await client.post_json("/users", json=payload)


async def remove_user(
    client: LandscapeClient,
    computer_ids: list[int],
    username: str,
    delete_home: bool = False,
) -> dict:
    """
    Remove an OS user from the specified computers.

    Args:
        delete_home: If True, also delete the user's home directory.
    """
    payload: dict = {
        "computer_ids": computer_ids,
        "username": username,
        "delete_home": delete_home,
    }
    return await client.delete_json("/users", json=payload)


async def lock_user(
    client: LandscapeClient,
    computer_ids: list[int],
    username: str,
) -> dict:
    """Lock (disable) an OS user account on the specified computers."""
    payload = {"computer_ids": computer_ids, "username": username}
    return await client.post_json("/users/lock", json=payload)


async def unlock_user(
    client: LandscapeClient,
    computer_ids: list[int],
    username: str,
) -> dict:
    """Unlock (re-enable) an OS user account on the specified computers."""
    payload = {"computer_ids": computer_ids, "username": username}
    return await client.post_json("/users/unlock", json=payload)
