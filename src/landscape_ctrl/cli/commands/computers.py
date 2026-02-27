"""
CLI commands for computer/device management.

Commands:
    lsctl computers ls              - list all computers
    lsctl computers get <id>        - show full details for one computer
    lsctl computers processes <id>  - list running processes
    lsctl computers packages <id>   - list packages on a computer
    lsctl computers restart <id>    - restart a computer
    lsctl computers shutdown <id>   - shutdown a computer
    lsctl computers archive <id>    - archive a computer
    lsctl computers activities <id> - list activities for a computer
    lsctl computers groups <id>     - list groups a computer belongs to
"""

from __future__ import annotations

import asyncio

import typer

from landscape_ctrl.api.client import LandscapeAPIError, LandscapeClient
from landscape_ctrl.api.endpoints.computers import (
    archive_computer,
    get_computer,
    get_computer_activities,
    get_computer_groups,
    get_packages,
    get_processes,
    list_computers,
    restart_computer,
    shutdown_computer,
)
from landscape_ctrl.cli.output import (
    OutputFormat,
    console,
    print_activities,
    print_computer_detail,
    print_computers,
    print_error,
    print_packages,
    print_processes,
    print_success,
    print_warning,
)
from landscape_ctrl.config import load_config

app = typer.Typer(help="Manage computers and devices registered with Landscape.")


def _run(coro):
    """Helper to run async coroutines from synchronous Typer commands."""
    return asyncio.run(coro)


@app.command("ls")
def computers_ls(
    tag: str | None = typer.Option(None, "--tag", "-t", help="Filter by tag name"),
    query: str | None = typer.Option(None, "--query", "-q", help="Raw Landscape query string"),
    hostname: str | None = typer.Option(None, "--hostname", "-H", help="Filter by hostname"),
    limit: int = typer.Option(1000, "--limit", "-l", help="Max results to return"),
    with_alerts: bool = typer.Option(False, "--with-alerts", help="Include alert information"),
    with_upgrades: bool = typer.Option(False, "--with-upgrades", help="Include upgrade counts"),
    with_network: bool = typer.Option(False, "--with-network", help="Include network details"),
    with_hardware: bool = typer.Option(False, "--with-hardware", help="Include hardware details"),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o", help="Output format"),
):
    """
    List computers registered with Landscape.

    Examples:
        lsctl computers ls
        lsctl computers ls --tag webserver
        lsctl computers ls --query "tag:db-servers AND distribution:ubuntu"
        lsctl computers ls --with-alerts --with-upgrades
        lsctl computers ls --output json | jq '.[].hostname'
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await list_computers(
                client,
                query=query,
                tag=tag,
                hostname=hostname,
                limit=limit,
                with_alerts=with_alerts,
                with_upgrades=with_upgrades,
                with_network=with_network,
                with_hardware=with_hardware,
            )

    try:
        computers = _run(_inner())
        if not computers:
            print_warning("No computers found matching the given filter.")
            return
        print_computers(computers, output)
    except FileNotFoundError as e:
        print_error(str(e))
        raise typer.Exit(1)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("get")
def computers_get(
    computer_id: int = typer.Argument(..., help="Landscape computer ID"),
):
    """
    Show full details for a single computer.

    Example:
        lsctl computers get 42
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await get_computer(client, computer_id)

    try:
        computer = _run(_inner())
        print_computer_detail(computer)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("processes")
def computers_processes(
    computer_id: int = typer.Argument(..., help="Landscape computer ID"),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List running processes on a computer.

    Example:
        lsctl computers processes 42
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await get_processes(client, computer_id)

    try:
        procs = _run(_inner())
        print_processes(procs, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("packages")
def computers_packages(
    computer_id: int = typer.Argument(..., help="Landscape computer ID"),
    upgrade: bool = typer.Option(False, "--upgrade", "-u", help="Only show packages with upgrades"),
    security: bool = typer.Option(False, "--security", "-s", help="Only show security updates"),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List packages installed on a specific computer.

    Examples:
        lsctl computers packages 42
        lsctl computers packages 42 --upgrade
        lsctl computers packages 42 --security --output json
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await get_packages(client, computer_id, upgrade=upgrade, security=security)

    try:
        pkgs = _run(_inner())
        print_packages(pkgs, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("restart")
def computers_restart(
    computer_id: int = typer.Argument(..., help="Landscape computer ID"),
    schedule: str | None = typer.Option(
        None, "--schedule", help="Schedule restart (ISO 8601 datetime, e.g. 2025-01-15T02:00:00Z)"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """
    Restart a computer managed by Landscape.

    Examples:
        lsctl computers restart 42
        lsctl computers restart 42 --schedule 2025-01-15T02:00:00Z
        lsctl computers restart 42 --yes
    """
    if not yes:
        confirmed = typer.confirm(
            f"Are you sure you want to restart computer #{computer_id}?",
            default=False,
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await restart_computer(client, computer_id, deliver_after=schedule)

    try:
        result = _run(_inner())
        if schedule:
            print_success(f"Restart of computer #{computer_id} scheduled for {schedule}")
        else:
            print_success(f"Restart initiated for computer #{computer_id} (activity: {result.get('id', '?')})")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("shutdown")
def computers_shutdown(
    computer_id: int = typer.Argument(..., help="Landscape computer ID"),
    schedule: str | None = typer.Option(
        None, "--schedule", help="Schedule shutdown (ISO 8601)"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """
    Shutdown a computer managed by Landscape.

    Examples:
        lsctl computers shutdown 42
        lsctl computers shutdown 42 --schedule 2025-01-15T02:00:00Z --yes
    """
    if not yes:
        confirmed = typer.confirm(
            f"Are you sure you want to shutdown computer #{computer_id}?",
            default=False,
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await shutdown_computer(client, computer_id, deliver_after=schedule)

    try:
        result = _run(_inner())
        if schedule:
            print_success(f"Shutdown of computer #{computer_id} scheduled for {schedule}")
        else:
            print_success(f"Shutdown initiated for computer #{computer_id} (activity: {result.get('id', '?')})")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("archive")
def computers_archive(
    computer_id: int = typer.Argument(..., help="Landscape computer ID"),
    title: str | None = typer.Option(None, "--title", help="Title for archived computer"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """
    Archive a computer.

    Example:
        lsctl computers archive 42 --title "Decommissioned DB" --yes
    """
    if not yes:
        confirmed = typer.confirm(
            f"Are you sure you want to archive computer #{computer_id}?",
            default=False,
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await archive_computer(client, computer_id, computer_title=title)

    try:
        _run(_inner())
        print_success(f"Computer #{computer_id} archived")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("activities")
def computers_activities(
    computer_id: int = typer.Argument(..., help="Landscape computer ID"),
    limit: int = typer.Option(100, "--limit", "-l", help="Max results"),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List activities for a specific computer.

    Example:
        lsctl computers activities 42 --limit 20
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await get_computer_activities(client, [computer_id], limit=limit)

    try:
        activities = _run(_inner())
        if not activities:
            console.print("[dim]No activities found.[/dim]")
            return
        print_activities(activities, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("groups")
def computers_groups(
    computer_id: int = typer.Argument(..., help="Landscape computer ID"),
):
    """
    List groups a computer belongs to.

    Example:
        lsctl computers groups 42
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await get_computer_groups(client, computer_id)

    try:
        groups = _run(_inner())
        if not groups:
            console.print("[dim]No groups found.[/dim]")
            return
        console.print(f"\n[bold]Groups for Computer #{computer_id}[/bold]\n")
        for g in groups:
            name = g.get("name", g) if isinstance(g, dict) else str(g)
            console.print(f"  {name}")
        console.print()
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)
