"""
CLI commands for script management and execution.

Commands:
    lsctl scripts ls                - list all scripts
    lsctl scripts get <id>          - show script details and code
    lsctl scripts run               - run a script on matching computers
    lsctl scripts status <ids...>   - check execution activity status
"""

from __future__ import annotations

import asyncio

import typer

from landscape_ctrl.api.client import LandscapeAPIError, LandscapeClient
from landscape_ctrl.api.endpoints.scripts import (
    execute_script,
    get_activity_results,
    get_script,
    list_scripts,
)
from landscape_ctrl.cli.output import (
    OutputFormat,
    console,
    print_activities,
    print_error,
    print_scripts,
    print_success,
)
from landscape_ctrl.config import load_config

app = typer.Typer(help="Manage and execute scripts on Landscape-managed computers.")


def _run(coro):
    return asyncio.run(coro)


@app.command("ls")
def scripts_ls(
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List all scripts available in your Landscape account.

    Example:
        lsctl scripts ls
        lsctl scripts ls --output json
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await list_scripts(client)

    try:
        scripts = _run(_inner())
        print_scripts(scripts, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("get")
def scripts_get(
    script_id: int = typer.Argument(..., help="Script ID to retrieve"),
):
    """
    Show script details including its code.

    Example:
        lsctl scripts get 7
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await get_script(client, script_id)

    try:
        script = _run(_inner())
        console.print(f"\n[bold cyan]Script #{script.id}[/bold cyan]: {script.title}")
        console.print(f"  Interpreter : {script.interpreter}")
        console.print(f"  Run as      : {script.username or '(unset)'}")
        console.print(f"  Time limit  : {script.time_limit or 'default'}s")
        console.print("\n[bold]Code:[/bold]")
        console.print(f"[dim]{'─' * 60}[/dim]")
        console.print(script.code)
        console.print(f"[dim]{'─' * 60}[/dim]\n")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("run")
def scripts_run(
    script_id: int = typer.Option(..., "--script-id", "-s", help="ID of the script to run"),
    query: str = typer.Option(..., "--query", "-q", help="Computer query (e.g. 'tag:webserver')"),
    username: str = typer.Option("ubuntu", "--user", "-u", help="OS user to run the script as"),
    schedule: str | None = typer.Option(
        None, "--schedule", help="Schedule execution (ISO 8601, e.g. 2025-01-15T02:00:00Z)"
    ),
    time_limit: int | None = typer.Option(
        None, "--time-limit", help="Override script time limit (seconds)"
    ),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """
    Execute a script on all computers matching a query.

    Uses the Landscape legacy API ExecuteScript action.

    Examples:
        lsctl scripts run --script-id 7 --query "tag:webserver" --user ubuntu
        lsctl scripts run --script-id 12 --query "hostname:db-01" --user root --yes
        lsctl scripts run --script-id 7 --query "tag:all" --schedule 2025-02-01T03:00:00Z
    """
    if not yes:
        confirmed = typer.confirm(
            f"Run script #{script_id} as '{username}' on computers matching '{query}'?",
            default=False,
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await execute_script(
                client,
                script_id=script_id,
                query=query,
                username=username,
                deliver_after=schedule,
                time_limit=time_limit,
            )

    try:
        activities = _run(_inner())
        print_success(f"Script #{script_id} dispatched to {len(activities)} computer(s)")
        print_activities(activities, output)
        activity_ids = " ".join(str(a.id) for a in activities)
        console.print(f"\nCheck status:  lsctl scripts status {activity_ids}\n")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("status")
def scripts_status(
    activity_ids: list[int] = typer.Argument(..., help="Activity IDs to check (space-separated)"),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    Check the status of script execution activities.

    Example:
        lsctl scripts status 1001 1002 1003
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await get_activity_results(client, activity_ids)

    try:
        activities = _run(_inner())
        print_activities(activities, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)
