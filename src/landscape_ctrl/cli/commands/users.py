"""
CLI commands for OS user management.

Commands:
    lsctl users ls              - list users on computers
    lsctl users add             - add a user to computers
    lsctl users remove          - remove a user from computers
    lsctl users lock            - lock (disable) a user account
    lsctl users unlock          - unlock a user account
"""

from __future__ import annotations

import asyncio

import typer

from landscape_ctrl.api.client import LandscapeAPIError, LandscapeClient
from landscape_ctrl.api.endpoints.users import (
    add_user,
    list_users,
    lock_user,
    remove_user,
    unlock_user,
)
from landscape_ctrl.cli.output import (
    OutputFormat,
    console,
    print_error,
    print_success,
    print_users,
)
from landscape_ctrl.config import load_config

app = typer.Typer(help="Manage OS users on Landscape-managed computers.")


def _run(coro):
    return asyncio.run(coro)


def _parse_ids(ids_str: str) -> list[int]:
    """Parse a comma-separated list of computer IDs."""
    try:
        return [int(i.strip()) for i in ids_str.split(",")]
    except ValueError:
        raise typer.BadParameter(f"Invalid computer IDs: {ids_str!r}. Use comma-separated integers.")


@app.command("ls")
def users_ls(
    computers: str = typer.Option(..., "--computers", "-c", help="Computer IDs (comma-separated, e.g. 1,2,3)"),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List OS users on the specified computers.

    Example:
        lsctl users ls --computers 42
        lsctl users ls --computers 1,2,3 --output json
    """
    computer_ids = _parse_ids(computers)

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await list_users(client, computer_ids)

    try:
        users = _run(_inner())
        if not users:
            console.print("[dim]No users found.[/dim]")
            return
        print_users(users, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("add")
def users_add(
    username: str = typer.Option(..., "--username", "-u", help="Login name for the new user"),
    computers: str = typer.Option(..., "--computers", "-c", help="Computer IDs (comma-separated)"),
    password: str = typer.Option(..., "--password", prompt=True, hide_input=True, help="Initial password"),
    name: str = typer.Option("", "--name", "-n", help="Full name (GECOS)"),
    email: str = typer.Option("", "--email", "-e", help="Email address"),
    home: str = typer.Option("", "--home", help="Home directory (default: /home/<username>)"),
    shell: str = typer.Option("/bin/bash", "--shell", help="Login shell"),
    group: str = typer.Option("", "--group", "-g", help="Primary group name (default: same as username)"),
):
    """
    Add a new OS user to computers.

    Examples:
        lsctl users add --username deploy --computers 42,43 --password
        lsctl users add --username ci --computers 10 --shell /bin/sh --name "CI Runner"
    """
    computer_ids = _parse_ids(computers)

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await add_user(
                client,
                computer_ids=computer_ids,
                username=username,
                password=password,
                name=name,
                email=email,
                primary_group_name=group,
                home=home,
                shell=shell,
            )

    try:
        _run(_inner())
        print_success(f"User '{username}' added to computers {computer_ids}")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("remove")
def users_remove(
    username: str = typer.Option(..., "--username", "-u", help="Username to remove"),
    computers: str = typer.Option(..., "--computers", "-c", help="Computer IDs (comma-separated)"),
    delete_home: bool = typer.Option(False, "--delete-home", help="Also delete the user's home directory"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Remove an OS user from computers.

    Examples:
        lsctl users remove --username deploy --computers 42
        lsctl users remove --username olduser --computers 42,43 --delete-home --yes
    """
    computer_ids = _parse_ids(computers)

    if not yes:
        home_note = " (and home directory)" if delete_home else ""
        confirmed = typer.confirm(
            f"Remove user '{username}'{home_note} from computers {computer_ids}?",
            default=False,
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await remove_user(client, computer_ids, username, delete_home=delete_home)

    try:
        _run(_inner())
        print_success(f"User '{username}' removed from computers {computer_ids}")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("lock")
def users_lock(
    username: str = typer.Option(..., "--username", "-u", help="Username to lock"),
    computers: str = typer.Option(..., "--computers", "-c", help="Computer IDs (comma-separated)"),
):
    """
    Lock (disable) an OS user account on computers.

    Example:
        lsctl users lock --username jdoe --computers 42,43
    """
    computer_ids = _parse_ids(computers)

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await lock_user(client, computer_ids, username)

    try:
        _run(_inner())
        print_success(f"User '{username}' locked on computers {computer_ids}")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("unlock")
def users_unlock(
    username: str = typer.Option(..., "--username", "-u", help="Username to unlock"),
    computers: str = typer.Option(..., "--computers", "-c", help="Computer IDs (comma-separated)"),
):
    """
    Unlock (re-enable) an OS user account on computers.

    Example:
        lsctl users unlock --username jdoe --computers 42
    """
    computer_ids = _parse_ids(computers)

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await unlock_user(client, computer_ids, username)

    try:
        _run(_inner())
        print_success(f"User '{username}' unlocked on computers {computer_ids}")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)
