"""
CLI commands for snap package management.

Commands:
    lsctl snaps ls <computer_id>  - list installed snaps on a computer
"""

from __future__ import annotations

import asyncio

import typer

from landscape_ctrl.api.client import LandscapeAPIError, LandscapeClient
from landscape_ctrl.api.endpoints.snaps import list_installed_snaps
from landscape_ctrl.cli.output import OutputFormat, console, print_error, print_snaps
from landscape_ctrl.config import load_config

app = typer.Typer(help="Manage snap packages on Landscape computers.")


def _run(coro):
    return asyncio.run(coro)


@app.command("ls")
def snaps_ls(
    computer_id: int = typer.Argument(..., help="Landscape computer ID"),
    limit: int | None = typer.Option(None, "--limit", "-l", help="Max results"),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List installed snaps on a specific computer.

    Examples:
        lsctl snaps ls 42
        lsctl snaps ls 42 --output json
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await list_installed_snaps(client, computer_id, limit=limit)

    try:
        snaps = _run(_inner())
        if not snaps:
            console.print("[dim]No snaps found.[/dim]")
            return
        print_snaps(snaps, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)
