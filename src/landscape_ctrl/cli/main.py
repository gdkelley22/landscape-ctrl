"""
landscape-ctrl CLI entry point.

All subcommands:
    lsctl config set        - configure server URL and credentials
    lsctl config show       - display current configuration
    lsctl login             - authenticate and cache a JWT token
    lsctl logout            - clear cached JWT token
    lsctl computers ...     - manage computers/devices
    lsctl scripts ...       - manage and run scripts
    lsctl packages ...      - manage packages
    lsctl users ...         - manage OS users
    lsctl tags ...          - manage tags
    lsctl activities ...    - manage activities/jobs
    lsctl snaps ...         - manage snap packages
    lsctl alerts ...        - manage alerts
    lsctl repos ...         - manage repositories
    lsctl admins ...        - manage administrators
    lsctl profiles ...      - manage profiles
    lsctl gpg ...           - manage GPG keys
    lsctl tokens ...        - manage API tokens
    lsctl events ...        - view event log and saved searches
    lsctl roles ...         - manage roles (RBAC)
"""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from landscape_ctrl import __version__
from landscape_ctrl.api.auth import (
    get_secret_key,
    store_secret_key,
)
from landscape_ctrl.api.client import LandscapeAPIError, LandscapeClient
from landscape_ctrl.cli.commands import (
    activities,
    administrators,
    alerts,
    computers,
    events,
    gpg,
    packages,
    profiles,
    rbac,
    repositories,
    scripts,
    snaps,
    tags,
    tokens,
    users,
)
from landscape_ctrl.cli.output import print_error, print_success
from landscape_ctrl.config import (
    CONFIG_FILE,
    LandscapeConfig,
    clear_token,
    config_exists,
    load_config,
    save_config,
)

console = Console()

app = typer.Typer(
    name="lsctl",
    help="landscape-ctrl — control Landscape MDM devices from your terminal.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Register subcommand groups
app.add_typer(computers.app, name="computers")
app.add_typer(scripts.app, name="scripts")
app.add_typer(packages.app, name="packages")
app.add_typer(users.app, name="users")
app.add_typer(tags.app, name="tags")
app.add_typer(activities.app, name="activities")
app.add_typer(snaps.app, name="snaps")
app.add_typer(alerts.app, name="alerts")
app.add_typer(repositories.app, name="repos")
app.add_typer(administrators.app, name="admins")
app.add_typer(profiles.app, name="profiles")
app.add_typer(gpg.app, name="gpg")
app.add_typer(tokens.app, name="tokens")
app.add_typer(events.app, name="events")
app.add_typer(rbac.app, name="roles")


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------


def version_callback(value: bool) -> None:
    if value:
        console.print(f"lsctl v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V", callback=version_callback, is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    pass


# ---------------------------------------------------------------------------
# Config commands
# ---------------------------------------------------------------------------

config_app = typer.Typer(help="Manage lsctl configuration.")
app.add_typer(config_app, name="config")


@config_app.command("set")
def config_set(
    url: str | None = typer.Option(None, "--url", help="Landscape server URL (e.g. https://landscape.example.com)"),
    access_key: str | None = typer.Option(None, "--access-key", help="API access key"),
    secret_key: str | None = typer.Option(None, "--secret-key", help="API secret key (stored in OS keychain)"),
    account: str = typer.Option("standalone", "--account", help="Landscape account name"),
    api_version: str = typer.Option("v2", "--api-version", help="API version: 'v2' or 'legacy'"),
    ssl_ca_file: str = typer.Option("", "--ssl-ca-file", help="Path to custom CA certificate file"),
    no_verify_ssl: bool = typer.Option(False, "--no-verify-ssl", help="Disable SSL verification (NOT recommended)"),
):
    """
    Set Landscape server configuration.

    On first run, provide at minimum --url and credentials.
    Secret key is stored securely in your OS keychain (not in the config file).

    Examples:
        lsctl config set --url https://landscape.example.com --access-key MYKEY --secret-key MYSECRET
        lsctl config set --url https://landscape.example.com --account myorg
        lsctl config set --ssl-ca-file /path/to/ca.pem
    """
    if config_exists():
        try:
            cfg = load_config()
        except Exception:
            cfg = LandscapeConfig(url=url or "")
    else:
        cfg = LandscapeConfig(url=url or "")

    if url:
        cfg.url = url.rstrip("/")
    if access_key:
        cfg.access_key = access_key
    if account:
        cfg.account = account
    if api_version:
        cfg.api_version = api_version
    if ssl_ca_file:
        cfg.ssl_ca_file = ssl_ca_file
    if no_verify_ssl:
        cfg.verify_ssl = False

    # Secret key goes to OS keychain, never to disk
    if secret_key:
        store_secret_key(secret_key)
        console.print("[dim]Secret key stored in OS keychain.[/dim]")

    if not cfg.url:
        print_error("--url is required. Example: --url https://landscape.example.com")
        raise typer.Exit(1)

    save_config(cfg)
    print_success(f"Configuration saved to {CONFIG_FILE}")
    console.print(f"  URL         : {cfg.url}")
    console.print(f"  Account     : {cfg.account}")
    console.print(f"  API version : {cfg.api_version}")
    if cfg.access_key:
        console.print(f"  Access key  : {cfg.access_key[:8]}...")


@config_app.command("show")
def config_show():
    """
    Display current configuration (secret key is masked).

    Example:
        lsctl config show
    """
    try:
        cfg = load_config()
    except FileNotFoundError as e:
        print_error(str(e))
        raise typer.Exit(1)

    secret = get_secret_key()
    console.print(f"\n[bold]Configuration[/bold] ({CONFIG_FILE})\n")
    console.print(f"  URL          : {cfg.url}")
    console.print(f"  Account      : {cfg.account}")
    console.print(f"  API version  : {cfg.api_version}")
    console.print(f"  Verify SSL   : {cfg.verify_ssl}")
    console.print(f"  SSL CA file  : {cfg.ssl_ca_file or '(system default)'}")
    console.print(f"  Access key   : {cfg.access_key or '(not set)'}")
    console.print(f"  Secret key   : {'*' * 12 if secret else '(not set)'}")
    console.print()


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------


@app.command("login")
def login(
    email: str | None = typer.Option(None, "--email", "-e", help="Email for email+password login"),
    password: str | None = typer.Option(
        None, "--password", "-p", prompt=False, help="Password (will prompt if --email used without --password)"
    ),
    expiry: int = typer.Option(1440, "--expiry", help="Token expiry in minutes (default: 1440 = 24h)"),
):
    """
    Authenticate with Landscape and cache a JWT token.

    By default, uses access-key + secret-key from config/keychain.
    Pass --email to use email + password login instead.

    Examples:
        lsctl login
        lsctl login --email admin@example.com
        lsctl login --expiry 60
    """
    async def _inner():
        cfg = load_config()
        async with LandscapeClient(cfg) as client:
            if email:
                pwd = password or typer.prompt("Password", hide_input=True)
                token = await client.login_with_email(email, pwd, cfg.account, expiry)
            else:
                secret = get_secret_key()
                if not secret:
                    print_error(
                        "No secret key found. Run:\n"
                        "  lsctl config set --secret-key YOUR_SECRET\n"
                        "Or use: lsctl login --email your@email.com"
                    )
                    raise typer.Exit(1)
                token = await client.login_with_access_key(cfg.access_key, secret, expiry)
            return token

    try:
        cfg = load_config()
        token = asyncio.run(_inner())
        preview = token[:16] + "..." if len(token) > 16 else token
        print_success(f"Authenticated with {cfg.url}")
        console.print(f"  Token cached (expires in {expiry // 60}h {expiry % 60}m): {preview}")
    except FileNotFoundError as e:
        print_error(str(e))
        raise typer.Exit(1)
    except LandscapeAPIError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("logout")
def logout():
    """
    Clear the cached JWT token.

    Example:
        lsctl logout
    """
    clear_token()
    print_success("Logged out — cached token removed.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run():
    app()


if __name__ == "__main__":
    run()
