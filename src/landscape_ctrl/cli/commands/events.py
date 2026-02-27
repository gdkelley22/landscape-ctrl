"""
CLI commands for event log and saved searches.

Commands:
    lsctl events log                       - view event log
    lsctl events searches ls               - list saved searches
    lsctl events searches create           - create a saved search
    lsctl events searches delete <id>      - delete a saved search
"""

from __future__ import annotations

import asyncio

import typer

from landscape_ctrl.api.client import LandscapeAPIError, LandscapeClient
from landscape_ctrl.api.endpoints.event_log import get_event_log
from landscape_ctrl.api.endpoints.saved_searches import (
    create_saved_search,
    delete_saved_search,
    list_saved_searches,
)
from landscape_ctrl.cli.output import (
    OutputFormat,
    console,
    print_error,
    print_event_log,
    print_saved_searches,
    print_success,
)
from landscape_ctrl.config import load_config

app = typer.Typer(help="View event log and manage saved searches.")
searches_app = typer.Typer(help="Manage saved searches.")
app.add_typer(searches_app, name="searches")


def _run(coro):
    return asyncio.run(coro)


@app.command("log")
def events_log(
    query: str | None = typer.Option(None, "--query", "-q", help="Filter query"),
    limit: int = typer.Option(100, "--limit", "-l", help="Max entries"),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    View event log entries.

    Examples:
        lsctl events log
        lsctl events log --limit 20
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await get_event_log(client, query=query, limit=limit)

    try:
        entries = _run(_inner())
        if not entries:
            console.print("[dim]No events found.[/dim]")
            return
        print_event_log(entries, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@searches_app.command("ls")
def searches_ls(
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List saved searches.

    Example:
        lsctl events searches ls
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await list_saved_searches(client)

    try:
        searches = _run(_inner())
        if not searches:
            console.print("[dim]No saved searches found.[/dim]")
            return
        print_saved_searches(searches, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@searches_app.command("create")
def searches_create(
    name: str = typer.Option(..., "--name", "-n", help="Search name"),
    query: str = typer.Option(..., "--query", "-q", help="Search query"),
):
    """
    Create a saved search.

    Example:
        lsctl events searches create --name "Production servers" --query "tag:production"
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await create_saved_search(client, name, query)

    try:
        _run(_inner())
        print_success(f"Saved search '{name}' created")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@searches_app.command("delete")
def searches_delete(
    search_id: int = typer.Argument(..., help="Saved search ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Delete a saved search.

    Example:
        lsctl events searches delete 3 --yes
    """
    if not yes:
        confirmed = typer.confirm(
            f"Delete saved search #{search_id}?", default=False
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await delete_saved_search(client, search_id)

    try:
        _run(_inner())
        print_success(f"Saved search #{search_id} deleted")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)
