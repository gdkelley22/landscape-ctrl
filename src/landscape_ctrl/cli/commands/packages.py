"""
CLI commands for package management.

Commands:
    lsctl packages ls               - list packages across the account
    lsctl packages install          - install packages on matching computers
    lsctl packages remove           - remove packages from matching computers
    lsctl packages upgrade          - upgrade packages on matching computers
    lsctl packages hold             - pin packages to current version
    lsctl packages release          - remove hold from packages
"""

from __future__ import annotations

import asyncio

import typer

from landscape_ctrl.api.client import LandscapeAPIError, LandscapeClient
from landscape_ctrl.api.endpoints.packages import (
    hold_packages,
    install_packages,
    list_packages,
    release_packages,
    remove_packages,
    upgrade_packages,
)
from landscape_ctrl.cli.output import (
    OutputFormat,
    console,
    print_activities,
    print_error,
    print_packages,
    print_success,
)
from landscape_ctrl.config import load_config

app = typer.Typer(help="Manage packages on Landscape-managed computers.")


def _run(coro):
    return asyncio.run(coro)


@app.command("ls")
def packages_ls(
    names: list[str] | None = typer.Option(None, "--name", "-n", help="Filter by package name (repeatable)"),
    query: str | None = typer.Option(None, "--query", "-q", help="Computer query to scope results"),
    upgrade: bool = typer.Option(False, "--upgrade", "-u", help="Only show packages with upgrades"),
    security: bool = typer.Option(False, "--security", "-s", help="Only show security updates"),
    installed: bool = typer.Option(False, "--installed", "-i", help="Only show installed packages"),
    limit: int = typer.Option(1000, "--limit", "-l", help="Max results"),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List packages visible across your Landscape account.

    Examples:
        lsctl packages ls
        lsctl packages ls --upgrade
        lsctl packages ls --security --query "tag:production"
        lsctl packages ls --name nginx --name curl --output json
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await list_packages(
                client,
                names=names,
                query=query,
                installed=installed,
                upgrade=upgrade,
                security=security,
                limit=limit,
            )

    try:
        pkgs = _run(_inner())
        if not pkgs:
            console.print("[dim]No packages found.[/dim]")
            return
        print_packages(pkgs, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("install")
def packages_install(
    packages: list[str] = typer.Argument(..., help="Package name(s) to install"),
    query: str = typer.Option(..., "--query", "-q", help="Computer selector (e.g. 'tag:webserver')"),
    schedule: str | None = typer.Option(None, "--schedule", help="Schedule install (ISO 8601)"),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Install package(s) on all computers matching a query.

    Examples:
        lsctl packages install nginx --query "tag:webserver"
        lsctl packages install nginx curl vim --query "tag:webserver" --yes
        lsctl packages install postgresql --query "hostname:db-01" --schedule 2025-01-15T03:00:00Z
    """
    if not yes:
        pkg_list = ", ".join(packages)
        confirmed = typer.confirm(
            f"Install [{pkg_list}] on computers matching '{query}'?",
            default=False,
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await install_packages(client, packages, query, deliver_after=schedule)

    try:
        activities = _run(_inner())
        print_success(f"Install dispatched to {len(activities)} computer(s)")
        print_activities(activities, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("remove")
def packages_remove(
    packages: list[str] = typer.Argument(..., help="Package name(s) to remove"),
    query: str = typer.Option(..., "--query", "-q", help="Computer selector"),
    schedule: str | None = typer.Option(None, "--schedule", help="Schedule removal (ISO 8601)"),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Remove package(s) from computers matching a query.

    Example:
        lsctl packages remove apache2 --query "tag:webserver" --yes
    """
    if not yes:
        pkg_list = ", ".join(packages)
        confirmed = typer.confirm(
            f"Remove [{pkg_list}] from computers matching '{query}'?",
            default=False,
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await remove_packages(client, packages, query, deliver_after=schedule)

    try:
        activities = _run(_inner())
        print_success(f"Remove dispatched to {len(activities)} computer(s)")
        print_activities(activities, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("upgrade")
def packages_upgrade(
    query: str = typer.Option(..., "--query", "-q", help="Computer selector"),
    packages: list[str] | None = typer.Option(None, "--package", "-p", help="Specific packages to upgrade (omit for all)"),
    schedule: str | None = typer.Option(None, "--schedule", help="Schedule upgrade (ISO 8601)"),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Upgrade packages on computers matching a query.
    If no specific packages are given, all upgradable packages are upgraded.

    Examples:
        lsctl packages upgrade --query "tag:webserver"
        lsctl packages upgrade --query "tag:production" --package nginx --package openssl
        lsctl packages upgrade --query "tag:all" --schedule 2025-01-20T02:00:00Z --yes
    """
    scope = f"[{', '.join(packages)}]" if packages else "ALL upgradable packages"
    if not yes:
        confirmed = typer.confirm(
            f"Upgrade {scope} on computers matching '{query}'?",
            default=False,
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await upgrade_packages(client, query, package_names=packages, deliver_after=schedule)

    try:
        activities = _run(_inner())
        print_success(f"Upgrade dispatched to {len(activities)} computer(s)")
        print_activities(activities, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("hold")
def packages_hold(
    packages: list[str] = typer.Argument(..., help="Package name(s) to hold"),
    query: str = typer.Option(..., "--query", "-q", help="Computer selector"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    Pin packages to their current version on matching computers.

    Example:
        lsctl packages hold nginx --query "tag:production" --yes
    """
    if not yes:
        pkg_list = ", ".join(packages)
        confirmed = typer.confirm(
            f"Hold [{pkg_list}] on computers matching '{query}'?",
            default=False,
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await hold_packages(client, packages, query)

    try:
        activities = _run(_inner())
        print_success(f"Hold dispatched to {len(activities)} computer(s)")
        print_activities(activities, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("release")
def packages_release(
    packages: list[str] = typer.Argument(..., help="Package name(s) to release"),
    query: str = typer.Option(..., "--query", "-q", help="Computer selector"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    Remove hold from packages on matching computers.

    Example:
        lsctl packages release nginx --query "tag:production" --yes
    """
    if not yes:
        pkg_list = ", ".join(packages)
        confirmed = typer.confirm(
            f"Release [{pkg_list}] on computers matching '{query}'?",
            default=False,
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await release_packages(client, packages, query)

    try:
        activities = _run(_inner())
        print_success(f"Release dispatched to {len(activities)} computer(s)")
        print_activities(activities, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)
