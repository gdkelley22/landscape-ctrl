"""
CLI commands for alert management.

Commands:
    lsctl alerts ls                    - list all alerts
    lsctl alerts get <id>              - show alert details
    lsctl alerts create --name X       - create an alert
    lsctl alerts delete <id>           - delete an alert
"""

from __future__ import annotations

import asyncio

import typer

from landscape_ctrl.api.client import LandscapeAPIError, LandscapeClient
from landscape_ctrl.api.endpoints.alerts import (
    create_alert,
    delete_alert,
    get_alert,
    list_alerts,
)
from landscape_ctrl.cli.output import (
    OutputFormat,
    console,
    print_alerts,
    print_error,
    print_success,
)
from landscape_ctrl.config import load_config

app = typer.Typer(help="Manage alerts in Landscape.")


def _run(coro):
    return asyncio.run(coro)


@app.command("ls")
def alerts_ls(
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List all alerts.

    Example:
        lsctl alerts ls
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await list_alerts(client)

    try:
        alerts = _run(_inner())
        if not alerts:
            console.print("[dim]No alerts found.[/dim]")
            return
        print_alerts(alerts, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("get")
def alerts_get(
    alert_id: int = typer.Argument(..., help="Alert ID"),
):
    """
    Show details for a single alert.

    Example:
        lsctl alerts get 5
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await get_alert(client, alert_id)

    try:
        alert = _run(_inner())
        console.print(f"\n[bold cyan]Alert #{alert.id}[/bold cyan]: {alert.name}")
        console.print(f"  Description : {alert.description or '-'}")
        console.print(f"  Severity    : {alert.severity or '-'}")
        console.print(f"  Active      : {alert.active}")
        console.print(f"  Computers   : {len(alert.computer_ids)}")
        console.print()
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("create")
def alerts_create(
    name: str = typer.Option(..., "--name", "-n", help="Alert name"),
    query: str = typer.Option(..., "--query", "-q", help="Computer query for alert scope"),
    description: str | None = typer.Option(None, "--description", "-d", help="Alert description"),
):
    """
    Create a new alert.

    Example:
        lsctl alerts create --name "High CPU" --query "tag:production"
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await create_alert(client, name, query, description=description)

    try:
        _run(_inner())
        print_success(f"Alert '{name}' created")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("delete")
def alerts_delete(
    alert_id: int = typer.Argument(..., help="Alert ID to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Delete an alert.

    Example:
        lsctl alerts delete 5 --yes
    """
    if not yes:
        confirmed = typer.confirm(
            f"Delete alert #{alert_id}?", default=False
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await delete_alert(client, alert_id)

    try:
        _run(_inner())
        print_success(f"Alert #{alert_id} deleted")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)
