"""
CLI commands for tag management.

Commands:
    lsctl tags ls                           - list all tags
    lsctl tags add <tag>... --query QUERY   - apply tags to matching computers
    lsctl tags remove <tag>... --query QUERY - remove tags from matching computers
"""

from __future__ import annotations

import asyncio

import typer

from landscape_ctrl.api.client import LandscapeAPIError, LandscapeClient
from landscape_ctrl.api.endpoints.tags import add_tags, list_tags, remove_tags
from landscape_ctrl.cli.output import OutputFormat, console, print_error, print_success
from landscape_ctrl.config import load_config

app = typer.Typer(help="Manage tags on Landscape computers.")


def _run(coro):
    return asyncio.run(coro)


@app.command("ls")
def tags_ls(
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List all tags in your Landscape account.

    Examples:
        lsctl tags ls
        lsctl tags ls --output json
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await list_tags(client)

    try:
        tags = _run(_inner())
        if not tags:
            console.print("[dim]No tags found.[/dim]")
            return
        if output == OutputFormat.json:
            import json
            print(json.dumps(tags, indent=2))
        else:
            console.print(f"\n[bold]Tags[/bold] ({len(tags)} total)\n")
            for tag in sorted(tags):
                console.print(f"  {tag}")
            console.print()
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("add")
def tags_add(
    tags: list[str] = typer.Argument(..., help="Tag(s) to apply"),
    query: str = typer.Option(..., "--query", "-q", help="Computer selector (e.g. 'tag:webserver')"),
):
    """
    Apply tags to all computers matching a query.

    Examples:
        lsctl tags add production --query "hostname:db-01"
        lsctl tags add web frontend --query "tag:ubuntu"
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await add_tags(client, query, tags)

    try:
        _run(_inner())
        print_success(f"Tags [{', '.join(tags)}] applied to computers matching '{query}'")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("remove")
def tags_remove(
    tags: list[str] = typer.Argument(..., help="Tag(s) to remove"),
    query: str = typer.Option(..., "--query", "-q", help="Computer selector"),
):
    """
    Remove tags from all computers matching a query.

    Example:
        lsctl tags remove deprecated --query "tag:deprecated"
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await remove_tags(client, query, tags)

    try:
        _run(_inner())
        print_success(f"Tags [{', '.join(tags)}] removed from computers matching '{query}'")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)
