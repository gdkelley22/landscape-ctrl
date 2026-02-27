"""
CLI commands for profile management.

Commands:
    lsctl profiles ls --type <type>        - list profiles of a type
    lsctl profiles get <id> --type <type>  - show profile details
    lsctl profiles create --type <type>    - create a profile
    lsctl profiles delete <id> --type <type> - delete a profile
"""

from __future__ import annotations

import asyncio

import typer

from landscape_ctrl.api.client import LandscapeAPIError, LandscapeClient
from landscape_ctrl.api.endpoints.profiles import (
    PROFILE_TYPES,
    create_profile,
    delete_profile,
    get_profile,
    list_profiles,
)
from landscape_ctrl.cli.output import (
    OutputFormat,
    console,
    print_error,
    print_profiles,
    print_success,
)
from landscape_ctrl.config import load_config

app = typer.Typer(help="Manage profiles (package, script, security, reboot, repository, removal, upgrade).")


def _run(coro):
    return asyncio.run(coro)


def _validate_type(profile_type: str) -> str:
    if profile_type not in PROFILE_TYPES:
        raise typer.BadParameter(
            f"Invalid profile type '{profile_type}'. "
            f"Choose from: {', '.join(sorted(PROFILE_TYPES))}"
        )
    return profile_type


@app.command("ls")
def profiles_ls(
    profile_type: str = typer.Option(..., "--type", "-t", help="Profile type"),
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List profiles of a given type.

    Examples:
        lsctl profiles ls --type package
        lsctl profiles ls --type security --output json
    """
    _validate_type(profile_type)

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await list_profiles(client, profile_type)

    try:
        profs = _run(_inner())
        if not profs:
            console.print(f"[dim]No {profile_type} profiles found.[/dim]")
            return
        print_profiles(profs, output, profile_type)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("get")
def profiles_get(
    profile_id: int = typer.Argument(..., help="Profile ID"),
    profile_type: str = typer.Option(..., "--type", "-t", help="Profile type"),
):
    """
    Show details for a single profile.

    Example:
        lsctl profiles get 7 --type script
    """
    _validate_type(profile_type)

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await get_profile(client, profile_type, profile_id)

    try:
        prof = _run(_inner())
        console.print(f"\n[bold cyan]{profile_type.title()} Profile #{prof.id}[/bold cyan]: {prof.name}")
        console.print(f"  Description  : {prof.description or '-'}")
        console.print(f"  Enabled      : {prof.enabled}")
        console.print(f"  Access Group : {prof.access_group or '-'}")
        console.print(f"  Tags         : {', '.join(prof.tags) or '-'}")
        console.print()
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("create")
def profiles_create(
    profile_type: str = typer.Option(..., "--type", "-t", help="Profile type"),
    name: str = typer.Option(..., "--name", "-n", help="Profile name"),
    description: str = typer.Option("", "--description", "-d", help="Profile description"),
):
    """
    Create a new profile.

    Example:
        lsctl profiles create --type package --name "Web Packages"
    """
    _validate_type(profile_type)

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await create_profile(client, profile_type, name, description=description)

    try:
        _run(_inner())
        print_success(f"{profile_type.title()} profile '{name}' created")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("delete")
def profiles_delete(
    profile_id: int = typer.Argument(..., help="Profile ID to delete"),
    profile_type: str = typer.Option(..., "--type", "-t", help="Profile type"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Delete a profile.

    Example:
        lsctl profiles delete 7 --type script --yes
    """
    _validate_type(profile_type)

    if not yes:
        confirmed = typer.confirm(
            f"Delete {profile_type} profile #{profile_id}?", default=False
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await delete_profile(client, profile_type, profile_id)

    try:
        _run(_inner())
        print_success(f"{profile_type.title()} profile #{profile_id} deleted")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)
