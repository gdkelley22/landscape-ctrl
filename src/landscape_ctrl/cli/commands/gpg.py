"""
CLI commands for GPG key management.

Commands:
    lsctl gpg ls            - list GPG keys
    lsctl gpg import        - import a GPG key
"""

from __future__ import annotations

import asyncio

import typer

from landscape_ctrl.api.client import LandscapeAPIError, LandscapeClient
from landscape_ctrl.api.endpoints.gpg import import_gpg_key, list_gpg_keys
from landscape_ctrl.cli.output import (
    OutputFormat,
    console,
    print_error,
    print_gpg_keys,
    print_success,
)
from landscape_ctrl.config import load_config

app = typer.Typer(help="Manage GPG keys in Landscape.")


def _run(coro):
    return asyncio.run(coro)


@app.command("ls")
def gpg_ls(
    output: OutputFormat = typer.Option(OutputFormat.table, "--output", "-o"),
):
    """
    List all GPG keys.

    Example:
        lsctl gpg ls
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await list_gpg_keys(client)

    try:
        keys = _run(_inner())
        if not keys:
            console.print("[dim]No GPG keys found.[/dim]")
            return
        print_gpg_keys(keys, output)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("import")
def gpg_import(
    key_file: str = typer.Option(..., "--file", "-f", help="Path to GPG key file"),
):
    """
    Import a GPG key from a file.

    Example:
        lsctl gpg import --file /path/to/key.gpg
    """
    try:
        with open(key_file) as f:
            key_material = f.read()
    except FileNotFoundError:
        print_error(f"File not found: {key_file}")
        raise typer.Exit(1)

    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            return await import_gpg_key(client, key_material)

    try:
        _run(_inner())
        print_success(f"GPG key imported from {key_file}")
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)
