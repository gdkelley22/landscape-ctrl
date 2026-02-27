"""
CLI commands for token management.

Commands:
    lsctl tokens ls        - list tokens
    lsctl tokens create    - create a new token
    lsctl tokens revoke    - revoke a token
"""

from __future__ import annotations

import asyncio

import typer

from landscape_ctrl.api.client import LandscapeAPIError, LandscapeClient
from landscape_ctrl.api.endpoints.tokens import (
    create_token,
    list_tokens,
    revoke_token,
)
from landscape_ctrl.cli.output import (
    OutputFormat,
    console,
    print_error,
    print_success,
    print_tokens,
)
from landscape_ctrl.config import load_config

app = typer.Typer(help="Manage API tokens in Landscape.")


def _run(coro):
    return asyncio.run(coro)


@app.command("ls")
def tokens_ls(
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List all API tokens.

    Example:
        lsctl tokens ls
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await list_tokens(client)

    try:
        toks = _run(_inner())
        if not toks:
            console.print("[dim]No tokens found.[/dim]")
            return
        print_tokens(toks, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("create")
def tokens_create(
    title: str = typer.Option("", "--title", "-t", help="Token title/description"),
):
    """
    Create a new API token.

    Example:
        lsctl tokens create --title "CI/CD token"
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await create_token(client, title=title)

    try:
        result = _run(_inner())
        print_success("Token created")
        if isinstance(result, dict) and "token" in result:
            console.print(f"  Token: {result['token']}")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("revoke")
def tokens_revoke(
    token_id: int = typer.Argument(..., help="Token ID to revoke"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Revoke a token.

    Example:
        lsctl tokens revoke 5 --yes
    """
    if not yes:
        confirmed = typer.confirm(
            f"Revoke token #{token_id}?", default=False
        )
        if not confirmed:
            console.print("Aborted.")
            return

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await revoke_token(client, token_id)

    try:
        _run(_inner())
        print_success(f"Token #{token_id} revoked")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)
