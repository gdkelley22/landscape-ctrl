"""
CLI commands for activity management.

Commands:
    lsctl activities ls       - list activities
    lsctl activities types    - list activity types
    lsctl activities cancel   - cancel pending activities
    lsctl activities approve  - approve activities
"""

from __future__ import annotations

import asyncio

import typer

from landscape_ctrl.api.client import LandscapeAPIError, LandscapeClient
from landscape_ctrl.api.endpoints.activities import (
    approve_activities,
    cancel_activities,
    get_activity_types,
    list_activities,
)
from landscape_ctrl.cli.output import (
    OutputFormat,
    console,
    print_activities,
    print_error,
    print_success,
)
from landscape_ctrl.config import load_config

app = typer.Typer(help="Manage activities and jobs in Landscape.")


def _run(coro):
    return asyncio.run(coro)


@app.command("ls")
def activities_ls(
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
    computer: str | None = typer.Option(None, "--computer", "-c", help="Filter by computer query"),
    activity_type: str | None = typer.Option(None, "--type", "-t", help="Filter by activity type"),
    limit: int = typer.Option(100, "--limit", "-l", help="Max results"),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List activities in your Landscape account.

    Examples:
        lsctl activities ls
        lsctl activities ls --status failed --limit 20
        lsctl activities ls --computer "tag:webserver"
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            query_parts = []
            if status:
                query_parts.append(f"status:{status}")
            if computer:
                query_parts.append(computer)
            if activity_type:
                query_parts.append(f"type:{activity_type}")
            query = " AND ".join(query_parts) if query_parts else None
            return await list_activities(client, query=query, limit=limit)

    try:
        activities = _run(_inner())
        if not activities:
            console.print("[dim]No activities found.[/dim]")
            return
        print_activities(activities, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("types")
def activities_types():
    """
    List all activity types.

    Example:
        lsctl activities types
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await get_activity_types(client)

    try:
        types = _run(_inner())
        if not types:
            console.print("[dim]No activity types found.[/dim]")
            return
        console.print(f"\n[bold]Activity Types[/bold] ({len(types)} total)\n")
        for t in sorted(types):
            console.print(f"  {t}")
        console.print()
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("cancel")
def activities_cancel(
    query: str = typer.Option(..., "--query", "-q", help="Query to select activities to cancel"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Cancel pending activities matching a query.

    Example:
        lsctl activities cancel --query "status:undelivered" --yes
    """
    if not yes:
        confirmed = typer.confirm(
            f"Cancel activities matching '{query}'?", default=False
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await cancel_activities(client, query)

    try:
        _run(_inner())
        print_success(f"Activities matching '{query}' cancelled")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("approve")
def activities_approve(
    query: str = typer.Option(..., "--query", "-q", help="Query to select activities to approve"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Approve activities awaiting approval.

    Example:
        lsctl activities approve --query "status:unapproved" --yes
    """
    if not yes:
        confirmed = typer.confirm(
            f"Approve activities matching '{query}'?", default=False
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await approve_activities(client, query)

    try:
        _run(_inner())
        print_success(f"Activities matching '{query}' approved")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)
