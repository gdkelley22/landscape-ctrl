"""
CLI commands for RBAC (Role-Based Access Control).

Commands:
    lsctl roles ls                - list roles
    lsctl roles create --name X   - create a role
    lsctl roles delete <id>       - delete a role
"""

from __future__ import annotations

import asyncio

import typer

from landscape_ctrl.api.client import LandscapeAPIError, LandscapeClient
from landscape_ctrl.api.endpoints.rbac import create_role, delete_role, list_roles
from landscape_ctrl.cli.output import (
    OutputFormat,
    console,
    print_error,
    print_roles,
    print_success,
)
from landscape_ctrl.config import load_config

app = typer.Typer(help="Manage roles and permissions (RBAC).")


def _run(coro):
    return asyncio.run(coro)


@app.command("ls")
def roles_ls(
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List all roles.

    Example:
        lsctl roles ls
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await list_roles(client)

    try:
        roles = _run(_inner())
        if not roles:
            console.print("[dim]No roles found.[/dim]")
            return
        print_roles(roles, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("create")
def roles_create(
    name: str = typer.Option(..., "--name", "-n", help="Role name"),
    permissions: list[str] | None = typer.Option(
        None, "--permission", "-p", help="Permission name (repeatable)"
    ),
):
    """
    Create a new role.

    Example:
        lsctl roles create --name "Deployer" --permission ExecuteScript --permission ViewComputers
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await create_role(client, name, permissions=permissions)

    try:
        _run(_inner())
        print_success(f"Role '{name}' created")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("delete")
def roles_delete(
    role_id: int = typer.Argument(..., help="Role ID to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Delete a role.

    Example:
        lsctl roles delete 5 --yes
    """
    if not yes:
        confirmed = typer.confirm(
            f"Delete role #{role_id}?", default=False
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await delete_role(client, role_id)

    try:
        _run(_inner())
        print_success(f"Role #{role_id} deleted")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)
