"""
CLI commands for administrator management.

Commands:
    lsctl admins ls                   - list administrators
    lsctl admins get <id>             - show administrator details
    lsctl admins create --name X      - create an administrator
    lsctl admins remove <id>          - remove an administrator
"""

from __future__ import annotations

import asyncio

import typer

from landscape_ctrl.api.client import LandscapeAPIError, LandscapeClient
from landscape_ctrl.api.endpoints.administrators import (
    create_administrator,
    get_administrator,
    list_administrators,
    remove_administrator,
)
from landscape_ctrl.cli.output import (
    OutputFormat,
    console,
    print_administrators,
    print_error,
    print_success,
)
from landscape_ctrl.config import load_config

app = typer.Typer(help="Manage Landscape administrators.")


def _run(coro):
    return asyncio.run(coro)


@app.command("ls")
def admins_ls(
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List all administrators.

    Example:
        lsctl admins ls
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await list_administrators(client)

    try:
        admins = _run(_inner())
        if not admins:
            console.print("[dim]No administrators found.[/dim]")
            return
        print_administrators(admins, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("get")
def admins_get(
    admin_id: int = typer.Argument(..., help="Administrator ID"),
):
    """
    Show details for a single administrator.

    Example:
        lsctl admins get 1
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await get_administrator(client, admin_id)

    try:
        admin = _run(_inner())
        console.print(f"\n[bold cyan]Administrator #{admin.id}[/bold cyan]: {admin.name}")
        console.print(f"  Email   : {admin.email or '-'}")
        console.print(f"  Role    : {admin.role or '-'}")
        console.print(f"  Enabled : {admin.enabled}")
        console.print()
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("create")
def admins_create(
    name: str = typer.Option(..., "--name", "-n", help="Administrator name"),
    email: str = typer.Option(..., "--email", "-e", help="Administrator email"),
):
    """
    Create a new administrator.

    Example:
        lsctl admins create --name "Jane Doe" --email jane@example.com
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await create_administrator(client, name, email)

    try:
        _run(_inner())
        print_success(f"Administrator '{name}' created")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("remove")
def admins_remove(
    admin_id: int = typer.Argument(..., help="Administrator ID to remove"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Remove an administrator.

    Example:
        lsctl admins remove 5 --yes
    """
    if not yes:
        confirmed = typer.confirm(
            f"Remove administrator #{admin_id}?", default=False
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await remove_administrator(client, admin_id)

    try:
        _run(_inner())
        print_success(f"Administrator #{admin_id} removed")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)
