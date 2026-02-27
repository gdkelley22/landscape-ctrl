"""
Output formatting for landscape-ctrl CLI.

Supports three output modes (set via --output flag on any command):
  table  - Rich-formatted terminal tables with color (default)
  json   - Raw JSON output, suitable for piping to jq
  csv    - Comma-separated values, suitable for spreadsheets

Usage:
    from landscape_ctrl.cli.output import OutputFormat, print_computers

    @app.command()
    def ls(output: OutputFormat = OutputFormat.table):
        computers = ...
        print_computers(computers, output)
"""

from __future__ import annotations

import csv
import io
import json
from enum import Enum
from typing import Any

from rich.console import Console
from rich.table import Table

from landscape_ctrl.api.models import (
    ActivityResult,
    Administrator,
    Alert,
    Computer,
    EventLogEntry,
    GPGKey,
    OSUser,
    Package,
    Process,
    Profile,
    Repository,
    Role,
    SavedSearch,
    Script,
    Snap,
    Token,
)

console = Console()
err_console = Console(stderr=True)


class OutputFormat(str, Enum):
    table = "table"
    json = "json"
    csv = "csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_json(data: list[Any]) -> None:
    """Dump a list of Pydantic models or dicts as formatted JSON."""
    serialized = [
        item.model_dump(mode="json") if hasattr(item, "model_dump") else item
        for item in data
    ]
    print(json.dumps(serialized, indent=2, default=str))


def _to_csv(rows: list[dict], fieldnames: list[str]) -> None:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    print(buf.getvalue(), end="")


def _mb(bytes_val: int | None) -> str:
    if bytes_val is None:
        return "-"
    return f"{bytes_val // 1024 // 1024} MB"


def _ts(dt: Any) -> str:
    if dt is None:
        return "-"
    return str(dt)[:16]  # trim microseconds


# ---------------------------------------------------------------------------
# Computers
# ---------------------------------------------------------------------------


def print_computers(computers: list[Computer], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _to_json(computers)
        return

    if fmt == OutputFormat.csv:
        rows = [
            {
                "id": c.id,
                "hostname": c.hostname,
                "distribution": c.distribution,
                "ip": c.ip,
                "tags": " ".join(c.tags),
                "reboot_required": c.reboot_required,
                "last_ping": _ts(c.last_ping),
            }
            for c in computers
        ]
        fields = ["id", "hostname", "distribution", "ip", "tags", "reboot_required", "last_ping"]
        _to_csv(rows, fields)
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Hostname", min_width=20)
    table.add_column("Distribution", min_width=16)
    table.add_column("IP Address", min_width=15)
    table.add_column("Tags", min_width=20)
    table.add_column("Reboot?", justify="center", width=8)
    table.add_column("Last Seen", min_width=16)

    for c in computers:
        reboot = "[bold red]YES[/bold red]" if c.reboot_required else "[green]no[/green]"
        tags = ", ".join(c.tags) if c.tags else "[dim]-[/dim]"
        table.add_row(
            str(c.id),
            c.hostname or c.title,
            c.distribution,
            c.ip or "-",
            tags,
            reboot,
            _ts(c.last_ping),
        )

    console.print(f"\n[bold]Computers[/bold] ({len(computers)} total)\n")
    console.print(table)


def print_computer_detail(c: Computer) -> None:
    """Print a single computer's full details."""
    console.print(f"\n[bold cyan]Computer #{c.id}[/bold cyan]")
    fields = [
        ("Hostname", c.hostname),
        ("Title", c.title),
        ("Distribution", c.distribution),
        ("Tags", ", ".join(c.tags) or "-"),
        ("Access Group", c.access_group or "-"),
        ("Reboot Required", "[bold red]YES[/bold red]" if c.reboot_required else "no"),
        ("Last Ping", _ts(c.last_ping)),
        ("Last Package Report", _ts(c.last_package_report)),
        ("RAM", _mb(c.total_memory)),
        ("Swap", _mb(c.total_swap)),
    ]
    for label, value in fields:
        console.print(f"  [bold]{label:<22}[/bold] {value}")
    if c.network_interfaces:
        console.print("\n  [bold]Network Interfaces[/bold]")
        for iface in c.network_interfaces:
            ips = ", ".join(iface.ip_addresses)
            console.print(f"    {iface.name:<12} {ips}  MAC: {iface.mac_address}")
    console.print()


# ---------------------------------------------------------------------------
# Processes
# ---------------------------------------------------------------------------


def print_processes(processes: list[Process], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _to_json(processes)
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("PID", justify="right", width=8)
    table.add_column("Name", min_width=24)
    table.add_column("User", min_width=12)
    table.add_column("State", width=8)
    table.add_column("VSZ (KB)", justify="right", width=10)
    table.add_column("RSS (KB)", justify="right", width=10)
    table.add_column("CPU%", justify="right", width=7)

    for p in processes:
        table.add_row(
            str(p.pid),
            p.name,
            p.username,
            p.state,
            str(p.vm_size) if p.vm_size else "-",
            str(p.vm_rss) if p.vm_rss else "-",
            f"{p.cpu:.1f}" if p.cpu is not None else "-",
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Packages
# ---------------------------------------------------------------------------


def print_packages(packages: list[Package], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _to_json(packages)
        return

    if fmt == OutputFormat.csv:
        rows = [
            {
                "name": p.name,
                "version": p.version,
                "installed": p.installed,
                "upgrade": p.upgrade,
                "security": p.security,
                "architecture": p.architecture,
            }
            for p in packages
        ]
        _to_csv(rows, ["name", "version", "installed", "upgrade", "security", "architecture"])
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("Name", min_width=28)
    table.add_column("Version", min_width=20)
    table.add_column("Arch", width=8)
    table.add_column("Installed", justify="center", width=10)
    table.add_column("Upgrade", justify="center", width=8)
    table.add_column("Security", justify="center", width=9)

    for p in packages:
        upgrade_cell = "[bold yellow]YES[/bold yellow]" if p.upgrade else "no"
        security_cell = "[bold red]YES[/bold red]" if p.security else "no"
        installed_cell = "[green]yes[/green]" if p.installed else "no"
        table.add_row(
            p.name,
            p.version,
            p.architecture,
            installed_cell,
            upgrade_cell,
            security_cell,
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Scripts
# ---------------------------------------------------------------------------


def print_scripts(scripts: list[Script], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _to_json(scripts)
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("ID", width=6)
    table.add_column("Title", min_width=30)
    table.add_column("Interpreter", min_width=16)
    table.add_column("Time Limit", justify="right", width=12)
    table.add_column("Run As", width=12)

    for s in scripts:
        table.add_row(
            str(s.id),
            s.title,
            s.interpreter,
            f"{s.time_limit}s" if s.time_limit else "-",
            s.username or "-",
        )
    console.print(table)


def print_activities(activities: list[ActivityResult], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _to_json(activities)
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("Activity ID", width=12)
    table.add_column("Computer ID", width=12)
    table.add_column("Type", min_width=16)
    table.add_column("Status", min_width=12)
    table.add_column("Return Code", justify="center", width=12)
    table.add_column("Completed", min_width=16)

    for a in activities:
        status_style = {
            "succeeded": "[green]succeeded[/green]",
            "failed": "[bold red]failed[/bold red]",
            "delivered": "[yellow]delivered[/yellow]",
            "undelivered": "[dim]undelivered[/dim]",
        }.get(a.status, a.status)
        table.add_row(
            str(a.id),
            str(a.computer_id) if a.computer_id else "-",
            a.type or "-",
            status_style,
            str(a.result_code) if a.result_code is not None else "-",
            _ts(a.completion_time),
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def print_users(users: list[OSUser], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _to_json(users)
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("Username", min_width=16)
    table.add_column("UID", width=8)
    table.add_column("GID", width=8)
    table.add_column("Home", min_width=20)
    table.add_column("Shell", min_width=14)
    table.add_column("Groups", min_width=24)
    table.add_column("Enabled", justify="center", width=8)

    for u in users:
        enabled_cell = "[green]yes[/green]" if u.enabled else "[bold red]no[/bold red]"
        table.add_row(
            u.name,
            str(u.uid) if u.uid is not None else "-",
            str(u.gid) if u.gid is not None else "-",
            u.home,
            u.shell,
            ", ".join(u.groups) or "-",
            enabled_cell,
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Snaps
# ---------------------------------------------------------------------------


def print_snaps(snaps: list[Snap], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _to_json(snaps)
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("Name", min_width=24)
    table.add_column("Version", min_width=16)
    table.add_column("Revision", width=10)
    table.add_column("Channel", min_width=12)
    table.add_column("Publisher", min_width=16)
    table.add_column("Confinement", width=14)

    for s in snaps:
        table.add_row(
            s.name,
            s.version,
            s.revision,
            s.channel,
            s.publisher,
            s.confinement,
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


def print_alerts(alerts: list[Alert], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _to_json(alerts)
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("ID", width=6)
    table.add_column("Name", min_width=24)
    table.add_column("Severity", width=12)
    table.add_column("Active", justify="center", width=8)
    table.add_column("Computers", justify="right", width=10)

    for a in alerts:
        active_cell = "[green]yes[/green]" if a.active else "[dim]no[/dim]"
        table.add_row(
            str(a.id),
            a.name,
            a.severity or "-",
            active_cell,
            str(len(a.computer_ids)),
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Administrators
# ---------------------------------------------------------------------------


def print_administrators(admins: list[Administrator], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _to_json(admins)
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("ID", width=6)
    table.add_column("Name", min_width=20)
    table.add_column("Email", min_width=24)
    table.add_column("Role", min_width=12)
    table.add_column("Enabled", justify="center", width=8)

    for a in admins:
        enabled_cell = "[green]yes[/green]" if a.enabled else "[bold red]no[/bold red]"
        table.add_row(
            str(a.id),
            a.name,
            a.email,
            a.role or "-",
            enabled_cell,
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------


def print_repositories(repos: list[Repository], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _to_json(repos)
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("ID", width=6)
    table.add_column("Name", min_width=24)
    table.add_column("Mode", width=12)
    table.add_column("Distribution", min_width=16)
    table.add_column("Enabled", justify="center", width=8)

    for r in repos:
        enabled_cell = "[green]yes[/green]" if r.enabled else "[dim]no[/dim]"
        table.add_row(
            str(r.id),
            r.name,
            r.mode or "-",
            r.distribution or "-",
            enabled_cell,
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------


def print_profiles(profiles: list[Profile], fmt: OutputFormat, profile_type: str = "") -> None:
    if fmt == OutputFormat.json:
        _to_json(profiles)
        return

    title = f"{profile_type.title()} Profiles" if profile_type else "Profiles"
    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("ID", width=6)
    table.add_column("Name", min_width=24)
    table.add_column("Description", min_width=30)
    table.add_column("Enabled", justify="center", width=8)

    for p in profiles:
        enabled_cell = "[green]yes[/green]" if p.enabled else "[dim]no[/dim]"
        table.add_row(
            str(p.id),
            p.name,
            p.description or "-",
            enabled_cell,
        )
    console.print(f"\n[bold]{title}[/bold] ({len(profiles)} total)\n")
    console.print(table)


# ---------------------------------------------------------------------------
# GPG Keys
# ---------------------------------------------------------------------------


def print_gpg_keys(keys: list[GPGKey], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _to_json(keys)
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("ID", width=6)
    table.add_column("Name", min_width=24)
    table.add_column("Key ID", min_width=16)
    table.add_column("Fingerprint", min_width=40)

    for k in keys:
        table.add_row(
            str(k.id),
            k.name,
            k.key_id,
            k.fingerprint,
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------


def print_tokens(tokens: list[Token], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _to_json(tokens)
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("ID", width=6)
    table.add_column("Title", min_width=24)
    table.add_column("Created", min_width=16)

    for t in tokens:
        table.add_row(
            str(t.id),
            t.title or "-",
            _ts(t.created_at),
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Event Log
# ---------------------------------------------------------------------------


def print_event_log(entries: list[EventLogEntry], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _to_json(entries)
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("ID", width=8)
    table.add_column("Type", min_width=16)
    table.add_column("Administrator", min_width=16)
    table.add_column("Message", min_width=40)
    table.add_column("Time", min_width=16)

    for e in entries:
        table.add_row(
            str(e.id),
            e.event_type,
            e.administrator or "-",
            e.message[:80] if e.message else "-",
            _ts(e.timestamp),
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Saved Searches
# ---------------------------------------------------------------------------


def print_saved_searches(searches: list[SavedSearch], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _to_json(searches)
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("ID", width=6)
    table.add_column("Name", min_width=24)
    table.add_column("Query", min_width=40)
    table.add_column("Default", justify="center", width=8)

    for s in searches:
        default_cell = "[green]yes[/green]" if s.default else "no"
        table.add_row(
            str(s.id),
            s.name,
            s.query,
            default_cell,
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Roles (RBAC)
# ---------------------------------------------------------------------------


def print_roles(roles: list[Role], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _to_json(roles)
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("ID", width=6)
    table.add_column("Name", min_width=24)
    table.add_column("Description", min_width=30)
    table.add_column("Permissions", min_width=30)

    for r in roles:
        table.add_row(
            str(r.id),
            r.name,
            r.description or "-",
            ", ".join(r.permissions) if r.permissions else "-",
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Error / info helpers
# ---------------------------------------------------------------------------


def print_error(message: str) -> None:
    err_console.print(f"[bold red]Error:[/bold red] {message}")


def print_success(message: str) -> None:
    console.print(f"[bold green]✓[/bold green] {message}")


def print_warning(message: str) -> None:
    console.print(f"[bold yellow]![/bold yellow] {message}")
