"""
CLI commands for repository management.

Commands:
    lsctl repos ls                - list repositories
    lsctl repos get <id>          - show repository details
    lsctl repos create --name X   - create a repository
    lsctl repos delete <id>       - delete a repository
"""

from __future__ import annotations

import asyncio

import typer

from landscape_ctrl.api.client import LandscapeAPIError, LandscapeClient
from landscape_ctrl.api.endpoints.repositories import (
    create_repository,
    delete_repository,
    get_repository,
    list_repositories,
)
from landscape_ctrl.cli.output import (
    OutputFormat,
    console,
    print_error,
    print_repositories,
    print_success,
)
from landscape_ctrl.config import load_config

app = typer.Typer(help="Manage repositories in Landscape.")


def _run(coro):
    return asyncio.run(coro)


@app.command("ls")
def repos_ls(
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List all repositories.

    Example:
        lsctl repos ls
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await list_repositories(client)

    try:
        repos = _run(_inner())
        if not repos:
            console.print("[dim]No repositories found.[/dim]")
            return
        print_repositories(repos, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("get")
def repos_get(
    repo_id: int = typer.Argument(..., help="Repository ID"),
):
    """
    Show details for a single repository.

    Example:
        lsctl repos get 3
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await get_repository(client, repo_id)

    try:
        repo = _run(_inner())
        console.print(f"\n[bold cyan]Repository #{repo.id}[/bold cyan]: {repo.name}")
        console.print(f"  Description  : {repo.description or '-'}")
        console.print(f"  Mode         : {repo.mode or '-'}")
        console.print(f"  URI          : {repo.uri or '-'}")
        console.print(f"  Distribution : {repo.distribution or '-'}")
        console.print(f"  Components   : {', '.join(repo.components) or '-'}")
        console.print(f"  Enabled      : {repo.enabled}")
        console.print()
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("create")
def repos_create(
    name: str = typer.Option(..., "--name", "-n", help="Repository name"),
    description: str = typer.Option("", "--description", "-d", help="Repository description"),
    mode: str | None = typer.Option(None, "--mode", "-m", help="Repository mode"),
):
    """
    Create a new repository.

    Example:
        lsctl repos create --name "my-repo" --description "Custom packages"
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await create_repository(client, name, description=description, mode=mode)

    try:
        _run(_inner())
        print_success(f"Repository '{name}' created")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("delete")
def repos_delete(
    repo_id: int = typer.Argument(..., help="Repository ID to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Delete a repository.

    Example:
        lsctl repos delete 3 --yes
    """
    if not yes:
        confirmed = typer.confirm(
            f"Delete repository #{repo_id}?", default=False
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await delete_repository(client, repo_id)

    try:
        _run(_inner())
        print_success(f"Repository #{repo_id} deleted")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)
