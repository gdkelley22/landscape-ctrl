# landscape-ctrl (`lsctl`)

A terminal-native CLI and Python API client for [Canonical Landscape MDM](https://ubuntu.com/landscape) — manage, query, and control your Linux fleet without touching the web UI.

---

## Table of Contents

1. [What Is This?](#what-is-this)
2. [How It Works (Architecture)](#how-it-works-architecture)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Authentication Deep Dive](#authentication-deep-dive)
7. [Command Reference](#command-reference)
   - [Config Commands](#config-commands)
   - [Login / Logout](#login--logout)
   - [Computers](#computers)
   - [Scripts](#scripts)
   - [Packages](#packages)
   - [Users](#users)
8. [Output Formats](#output-formats)
9. [Landscape Query Syntax](#landscape-query-syntax)
10. [Using as a Python Library](#using-as-a-python-library)
11. [Project Structure](#project-structure)
12. [Development Guide](#development-guide)
13. [Testing](#testing)
14. [How the Two APIs Work](#how-the-two-apis-work)
15. [Troubleshooting](#troubleshooting)
16. [Roadmap](#roadmap)

---

## What Is This?

Landscape is Canonical's systems management tool for Ubuntu and other Linux machines. It provides:
- Package management (install, remove, upgrade) across a fleet
- Script execution on groups of machines
- OS user management
- Machine tagging and grouping
- Hardware/process inventory

**landscape-ctrl** (`lsctl`) gives you a fast terminal interface to all of this. Instead of clicking through the Landscape web UI, you can:

```bash
# See all machines tagged "webserver" that need a reboot
lsctl computers ls --tag webserver

# Install nginx on all webservers in one command
lsctl packages install nginx --query "tag:webserver" --yes

# Run a script on your database servers
lsctl scripts run --script-id 7 --query "tag:db-servers" --user ubuntu

# Check what users are on a machine
lsctl users ls --computers 42

# Pipe results to jq for scripting
lsctl computers ls --output json | jq '.[].hostname'
```

---

## How It Works (Architecture)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Your Terminal                            │
│                                                                 │
│   lsctl computers ls --tag webserver --output json              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CLI Layer (Typer)                           │
│                                                                 │
│  src/landscape_ctrl/cli/                                        │
│  ├── main.py          ← entry point, registers all subcommands  │
│  ├── output.py        ← Rich tables / JSON / CSV formatting     │
│  └── commands/                                                  │
│      ├── computers.py ← lsctl computers *                       │
│      ├── scripts.py   ← lsctl scripts *                         │
│      ├── packages.py  ← lsctl packages *                        │
│      └── users.py     ← lsctl users *                          │
└────────────────────────────┬────────────────────────────────────┘
                             │  calls endpoint functions
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Endpoint Wrappers Layer                       │
│                                                                 │
│  src/landscape_ctrl/api/endpoints/                              │
│  ├── computers.py  ← list_computers(), get_computer(), ...      │
│  ├── scripts.py    ← list_scripts(), execute_script(), ...      │
│  ├── packages.py   ← list_packages(), install_packages(), ...   │
│  ├── users.py      ← list_users(), add_user(), lock_user(), ... │
│  └── tags.py       ← add_tags(), remove_tags(), list_tags()     │
│                                                                 │
│  These functions translate high-level intent ("list computers   │
│  with tag X") into the right API call and return typed models.  │
└────────────────────────────┬────────────────────────────────────┘
                             │  uses LandscapeClient
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    HTTP Client Layer                            │
│                                                                 │
│  src/landscape_ctrl/api/client.py  (LandscapeClient)           │
│                                                                 │
│  • Wraps httpx.AsyncClient                                      │
│  • Injects JWT Bearer token on every request                    │
│  • Auto-retries once on 401 (token expired → re-login)          │
│  • Paginates automatically (follows `next` cursor)              │
│  • Signs legacy API calls with HMAC-SHA256                      │
│  • Handles errors uniformly → LandscapeAPIError / AuthError     │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────┴────────────────────┐
          │                                       │
          ▼                                       ▼
┌─────────────────────┐               ┌────────────────────────┐
│   REST v2 API       │               │   Legacy API           │
│                     │               │                        │
│  /api/v2/computers  │               │  /api/?action=...      │
│  /api/v2/scripts    │               │  HMAC-SHA256 signed    │
│  /api/v2/packages   │               │                        │
│  /api/v2/users      │               │  Used for:             │
│                     │               │  • Script execution    │
│  JWT Bearer auth    │               │  • Tag management      │
│  Landscape 24.04+   │               │  • Package mutations   │
└─────────────────────┘               └────────────────────────┘
```

### Data Flow for a Typical Command

Here is exactly what happens when you run `lsctl computers ls --tag webserver`:

```
1. Typer parses args → calls computers_ls(tag="webserver", output=OutputFormat.table)

2. computers_ls() calls list_computers(client, tag="webserver")

3. list_computers() builds: GET /api/v2/computers?query=tag:webserver&limit=1000

4. LandscapeClient._request_with_retry() adds:
     Authorization: Bearer <cached_jwt_token>
   and sends the request via httpx

5. If response is 401:
     a. get_secret_key() retrieves secret from OS keychain
     b. POST /api/v2/login/access-key → new JWT
     c. save_token() caches new token to ~/.local/share/lsctl/token
     d. Retry original request with new token

6. Response JSON is validated against Computer Pydantic model
   → list[Computer] returned

7. output.py renders a Rich table to the terminal
```

### Why Two APIs?

Landscape has two API generations:

| API | Version | Auth | What it's for |
|-----|---------|------|---------------|
| REST v2 | Landscape 24.04+ | JWT Bearer | Reading data: computers, scripts, packages, users |
| Legacy | All versions | HMAC-SHA256 | Mutations: executing scripts, tag management, installing packages |

REST v2 is the modern API but doesn't yet expose all operations. The legacy API has full mutation coverage but uses a more complex signing scheme. `lsctl` uses REST v2 as the primary API and transparently falls back to the legacy API for operations that aren't available in v2.

---

## Prerequisites

- Python 3.11 or newer
- A running Landscape instance (self-hosted or [Landscape SaaS](https://ubuntu.com/landscape))
- An API access key and secret key from your Landscape account settings
- `pipx` (recommended) or `pip`

---

## Installation

### Option 1: pipx (recommended — isolated environment)

```bash
pipx install landscape-ctrl
```

### Option 2: pip into a virtualenv

```bash
python -m venv .venv
source .venv/bin/activate
pip install landscape-ctrl
```

### Option 3: Development install from source

```bash
git clone https://github.com/gkelley/landscape-ctrl
cd landscape-ctrl
pip install -e ".[dev]"
```

After installation, the `lsctl` command is available globally.

---

## Configuration

Configuration lives in `~/.config/lsctl/config.toml`. You never need to edit this file directly.

### Initial Setup

```bash
lsctl config set \
  --url https://landscape.example.com \
  --access-key YOUR_ACCESS_KEY \
  --secret-key YOUR_SECRET_KEY \
  --account standalone
```

**Important:** The secret key is stored in your OS keychain (macOS Keychain, GNOME Keyring, KDE Wallet, etc.), **not** in the config file. This prevents accidental exposure in dotfiles or backups.

### View Current Config

```bash
lsctl config show
```

```
Configuration (/home/gkelley/.config/lsctl/config.toml)

  URL          : https://landscape.example.com
  Account      : standalone
  API version  : v2
  Verify SSL   : True
  SSL CA file  : (system default)
  Access key   : 1R3XGCT1...
  Secret key   : ************
```

### Self-Signed SSL Certificates

If your Landscape instance uses a self-signed certificate:

```bash
lsctl config set --ssl-ca-file /path/to/your/ca.pem
```

### Configuration File Format

```toml
[landscape]
url = "https://landscape.example.com"
account = "standalone"
ssl_ca_file = ""
api_version = "v2"
verify_ssl = true

[auth]
access_key = "1R3XGCT17NWIXKU5AM5J"
# secret_key is in OS keychain — never stored here
```

### Environment Variables

For CI/CD pipelines or scripting without a config file:

```bash
export LANDSCAPE_SECRET_KEY="your-secret-key"
lsctl login
```

---

## Authentication Deep Dive

### How JWT Authentication Works (REST v2)

```
┌─────┐                           ┌──────────────┐
│lsctl│                           │  Landscape   │
└──┬──┘                           └──────┬───────┘
   │                                     │
   │  POST /api/v2/login/access-key      │
   │  { access_key, secret_key }  ──────►│
   │                                     │
   │  { "token": "eyJhbGci..." }  ◄──────│
   │                                     │
   │  (token cached to disk)             │
   │                                     │
   │  GET /api/v2/computers              │
   │  Authorization: Bearer eyJhbGci... ►│
   │                                     │
   │  { "results": [...] }        ◄──────│
```

The JWT token is valid for **24 hours** by default (configurable). It is cached at `~/.local/share/lsctl/token` so you don't need to log in on every command.

When the token expires, `lsctl` automatically detects the 401 response, re-authenticates using the stored secret key, and retries the failed request — transparent to you.

### How HMAC-SHA256 Authentication Works (Legacy API)

For legacy API calls (script execution, tag management, package mutations), every request is signed:

```
1. Collect all parameters: action, access_key_id, timestamp, version, ...
2. Sort parameters alphabetically by key name
3. Percent-encode each key and value (RFC 3986)
4. Join as: key1=val1&key2=val2&...
5. Build string-to-sign:
     GET\n
     landscape.example.com\n
     /api/\n
     <canonicalized-params>
6. HMAC-SHA256(secret_key, string_to_sign) → Base64 → Signature parameter
```

This happens automatically inside `LandscapeClient.legacy_call()`.

### Getting API Keys

1. Log into your Landscape instance web UI
2. Go to **Settings** → **API credentials**
3. Create a new key pair
4. Copy the access key and secret key

---

## Command Reference

### Config Commands

#### `lsctl config set`

Set one or more configuration values.

```bash
lsctl config set [OPTIONS]

Options:
  --url TEXT          Landscape server URL
  --access-key TEXT   API access key
  --secret-key TEXT   API secret key (stored in OS keychain)
  --account TEXT      Landscape account name (default: standalone)
  --api-version TEXT  API version: v2 or legacy (default: v2)
  --ssl-ca-file TEXT  Path to custom CA certificate
  --no-verify-ssl     Disable SSL certificate verification
```

#### `lsctl config show`

Display current configuration with secret key masked.

```bash
lsctl config show
```

---

### Login / Logout

#### `lsctl login`

Authenticate and cache a JWT token (required before other commands).

```bash
# Login using access-key + secret-key from config/keychain (default)
lsctl login

# Login using email + password
lsctl login --email admin@example.com

# Set a shorter token lifetime (useful for shared machines)
lsctl login --expiry 60
```

#### `lsctl logout`

Clear the cached JWT token. Your credentials remain saved in the config.

```bash
lsctl logout
```

---

### Computers

Manage computers and devices registered with Landscape.

#### `lsctl computers ls`

List computers with optional filtering.

```bash
lsctl computers ls [OPTIONS]

Options:
  --tag, -t TEXT       Filter by tag name
  --query, -q TEXT     Raw Landscape query string
  --hostname, -H TEXT  Filter by hostname
  --limit, -l INT      Max results (default: 1000)
  --output, -o FORMAT  Output format: table|json|csv
```

Examples:

```bash
# List all computers
lsctl computers ls

# Filter by tag
lsctl computers ls --tag webserver

# Filter by hostname
lsctl computers ls --hostname db-01

# Complex query (see Query Syntax section)
lsctl computers ls --query "tag:webserver AND distribution:Ubuntu"

# JSON output for scripting
lsctl computers ls --output json | jq '.[].hostname'

# CSV for spreadsheets
lsctl computers ls --output csv > fleet.csv
```

Sample table output:
```
Computers (12 total)

 ID     Hostname              Distribution        IP Address      Tags              Reboot?  Last Seen
 ────────────────────────────────────────────────────────────────────────────────────────────────────
 42     db-01.example.com     Ubuntu 22.04 LTS    192.168.1.10   production, db    YES      2025-01-15
 43     web-01.example.com    Ubuntu 22.04 LTS    192.168.1.11   production, web   no       2025-01-15
```

#### `lsctl computers get`

Show full details for a single computer.

```bash
lsctl computers get 42
```

```
Computer #42
  Hostname              db-01.example.com
  Distribution          Ubuntu 22.04 LTS
  Tags                  production, db-servers
  Access Group          default
  Reboot Required       no
  Last Ping             2025-01-15 14:32
  RAM                   16384 MB
  Swap                  2048 MB

  Network Interfaces
    eth0         192.168.1.10, 10.0.0.10  MAC: aa:bb:cc:dd:ee:ff
```

#### `lsctl computers processes`

List running processes on a computer.

```bash
lsctl computers processes 42
lsctl computers processes 42 --output json
```

#### `lsctl computers packages`

List packages on a specific computer.

```bash
# All packages
lsctl computers packages 42

# Only packages with available upgrades
lsctl computers packages 42 --upgrade

# Only security updates
lsctl computers packages 42 --security

# JSON output
lsctl computers packages 42 --security --output json
```

#### `lsctl computers restart`

Schedule a restart for a computer.

```bash
# Restart as soon as possible (with confirmation prompt)
lsctl computers restart 42

# Schedule for a maintenance window
lsctl computers restart 42 --schedule 2025-01-20T02:00:00Z

# Skip confirmation
lsctl computers restart 42 --yes
```

---

### Scripts

Manage and execute scripts on Landscape-managed computers.

#### `lsctl scripts ls`

List all scripts available in your account.

```bash
lsctl scripts ls
lsctl scripts ls --output json
```

```
 ID    Title                          Interpreter   Time Limit  Run As
 ─────────────────────────────────────────────────────────────────────
 7     Deploy application             /bin/bash     300s        ubuntu
 12    Collect system info            /usr/bin/python3  60s     root
 15    Rotate logs                    /bin/bash     120s        -
```

#### `lsctl scripts get`

Show a script's details and its code.

```bash
lsctl scripts get 7
```

```
Script #7: Deploy application
  Interpreter : /bin/bash
  Run as      : ubuntu
  Time limit  : 300s

Code:
────────────────────────────────────────────────────────────
#!/bin/bash
set -e
cd /var/www/app
git pull origin main
systemctl restart app
────────────────────────────────────────────────────────────
```

#### `lsctl scripts run`

Execute a script on all computers matching a query.

```bash
lsctl scripts run [OPTIONS]

Required:
  --script-id, -s INT   Script ID to execute
  --query, -q TEXT      Computer selector (e.g. "tag:webserver")

Options:
  --user, -u TEXT       OS user to run script as (default: ubuntu)
  --schedule TEXT       Schedule execution (ISO 8601 datetime)
  --time-limit INT      Override script time limit (seconds)
  --output, -o FORMAT   Output format: table|json
  --yes, -y             Skip confirmation prompt
```

Examples:

```bash
# Run script #7 on all webservers as user "ubuntu"
lsctl scripts run --script-id 7 --query "tag:webserver" --user ubuntu

# Run as root on a single machine
lsctl scripts run --script-id 12 --query "hostname:db-01" --user root --yes

# Schedule for a maintenance window
lsctl scripts run \
  --script-id 15 \
  --query "tag:production" \
  --schedule 2025-01-20T02:00:00Z \
  --yes
```

After execution, you get activity IDs to track progress:

```
✓ Script #7 dispatched to 3 computer(s)

 Activity ID  Computer ID  Status       Return Code  Completed
 ──────────────────────────────────────────────────────────────
 1001         42           delivered    -            -
 1002         43           delivered    -            -
 1003         44           delivered    -            -

Check status:  lsctl scripts status 1001 1002 1003
```

#### `lsctl scripts status`

Check the status of script execution activities.

```bash
lsctl scripts status 1001 1002 1003
```

```
 Activity ID  Computer ID  Status       Return Code  Completed
 ──────────────────────────────────────────────────────────────
 1001         42           succeeded    0            2025-01-15 14:35
 1002         43           succeeded    0            2025-01-15 14:35
 1003         44           failed       1            2025-01-15 14:36
```

---

### Packages

Manage packages across your Landscape fleet.

#### `lsctl packages ls`

List packages visible across the account.

```bash
lsctl packages ls [OPTIONS]

Options:
  --name, -n TEXT      Filter by package name (repeatable)
  --query, -q TEXT     Computer query to scope results
  --upgrade, -u        Only show packages with upgrades available
  --security, -s       Only show security updates
  --installed, -i      Only show installed packages
  --limit, -l INT      Max results (default: 1000)
  --output, -o FORMAT  Output format: table|json|csv
```

Examples:

```bash
# All packages with upgrades across the fleet
lsctl packages ls --upgrade

# Security updates on production servers
lsctl packages ls --security --query "tag:production"

# Check specific packages
lsctl packages ls --name nginx --name curl

# Export for audit
lsctl packages ls --installed --output csv > packages-audit.csv
```

#### `lsctl packages install`

Install packages on matching computers.

```bash
# Install nginx on all webservers
lsctl packages install nginx --query "tag:webserver"

# Install multiple packages
lsctl packages install nginx curl vim --query "tag:webserver" --yes

# Schedule install for maintenance window
lsctl packages install postgresql \
  --query "hostname:db-01" \
  --schedule 2025-01-20T02:00:00Z
```

#### `lsctl packages remove`

Remove packages from matching computers.

```bash
lsctl packages remove apache2 --query "tag:webserver" --yes
lsctl packages remove telnet netcat --query "tag:production" --yes
```

#### `lsctl packages upgrade`

Upgrade packages on matching computers.

```bash
# Upgrade ALL packages on staging servers
lsctl packages upgrade --query "tag:staging" --yes

# Upgrade only specific packages
lsctl packages upgrade --query "tag:production" \
  --package openssl \
  --package libssl1.1

# Schedule full upgrade
lsctl packages upgrade --query "tag:all" \
  --schedule 2025-01-20T03:00:00Z \
  --yes
```

---

### Users

Manage OS users on Landscape-managed computers.

#### `lsctl users ls`

List users on specified computers.

```bash
lsctl users ls --computers 42
lsctl users ls --computers 1,2,3 --output json
```

#### `lsctl users add`

Add a new OS user to computers.

```bash
# Interactive password prompt
lsctl users add --username deploy --computers 42,43

# With all options
lsctl users add \
  --username ci-runner \
  --computers 10,11,12 \
  --name "CI Runner" \
  --shell /bin/bash \
  --home /srv/ci
```

#### `lsctl users remove`

Remove an OS user from computers.

```bash
lsctl users remove --username olduser --computers 42 --yes
lsctl users remove --username olduser --computers 42,43 --delete-home --yes
```

#### `lsctl users lock` / `lsctl users unlock`

Lock or unlock a user account (disable/re-enable login).

```bash
# Lock a compromised account immediately
lsctl users lock --username jdoe --computers 42,43,44

# Re-enable after investigation
lsctl users unlock --username jdoe --computers 42
```

---

## Output Formats

All commands support `--output` (or `-o`) with three formats:

### `table` (default)

Rich-formatted terminal tables with color highlighting. Best for interactive use.

```bash
lsctl computers ls --output table
```

### `json`

Raw JSON array, suitable for piping to `jq`, scripting, or feeding into other tools.

```bash
# Get just hostnames
lsctl computers ls --output json | jq -r '.[].hostname'

# Find computers needing a reboot
lsctl computers ls --output json | jq '[.[] | select(.reboot_required == true)]'

# Get all IP addresses of webservers
lsctl computers ls --tag webserver --output json | jq -r '.[].network_interfaces[0].ip_addresses[0]'
```

### `csv`

Comma-separated values, suitable for spreadsheets or further shell processing.

```bash
lsctl computers ls --output csv > fleet.csv
lsctl packages ls --security --output csv | column -t -s,
```

---

## Landscape Query Syntax

The `--query` flag accepts Landscape's built-in computer selector syntax. This is the same syntax used in the Landscape web UI.

| Query | Selects |
|-------|---------|
| `tag:webserver` | Computers tagged "webserver" |
| `hostname:db-01` | Exact hostname match |
| `distribution:ubuntu` | Ubuntu machines |
| `alert:package-upgrades` | Machines with pending upgrades |
| `id:42` | Single computer by ID |

Combine selectors with boolean operators:

```bash
# Ubuntu webservers
lsctl computers ls --query "tag:webserver AND distribution:ubuntu"

# Production but not database servers
lsctl computers ls --query "tag:production AND NOT tag:db-servers"

# Specific machine by ID
lsctl computers ls --query "id:42"
```

---

## Using as a Python Library

`lsctl` is also a usable Python library if you want to build your own automation on top of the Landscape API.

### Basic Usage

```python
import asyncio
from landscape_ctrl.config import LandscapeConfig
from landscape_ctrl.api.client import LandscapeClient
from landscape_ctrl.api.endpoints.computers import list_computers
from landscape_ctrl.api.endpoints.scripts import execute_script

async def main():
    cfg = LandscapeConfig(
        url="https://landscape.example.com",
        access_key="YOUR_ACCESS_KEY",
        api_version="v2",
    )

    async with LandscapeClient(cfg) as client:
        # Login first
        await client.login_with_access_key("YOUR_ACCESS_KEY", "YOUR_SECRET_KEY")

        # List all computers tagged "webserver"
        computers = await list_computers(client, tag="webserver")
        for computer in computers:
            print(f"{computer.id}: {computer.hostname} ({computer.ip})")

        # Execute a script on tagged computers
        activities = await execute_script(
            client,
            script_id=7,
            query="tag:webserver",
            username="ubuntu",
        )
        for activity in activities:
            print(f"Activity {activity.id}: {activity.status}")

asyncio.run(main())
```

### Pagination

For large fleets, use `stream_computers` to process machines one at a time without loading everything into memory:

```python
from landscape_ctrl.api.endpoints.computers import stream_computers

async with LandscapeClient(cfg) as client:
    async for computer in stream_computers(client, tag="production"):
        print(computer.hostname)
```

### Raw API Access

If you need an endpoint not yet wrapped, use the client directly:

```python
async with LandscapeClient(cfg) as client:
    # REST v2 call
    data = await client.get_json("/scripts/7/versions")

    # Legacy API call (HMAC-signed)
    data = await client.legacy_call("GetAccessGroups", {"names": "default"})

    # Paginate over any endpoint
    async for item in client.paginate("/computers/activities"):
        print(item)
```

---

## Project Structure

```
landscape-ctrl/
├── src/
│   └── landscape_ctrl/
│       ├── __init__.py              ← package version
│       ├── config.py                ← config file I/O, token cache
│       ├── api/
│       │   ├── __init__.py
│       │   ├── auth.py              ← JWT helpers, HMAC signer, keychain
│       │   ├── client.py            ← LandscapeClient (httpx wrapper)
│       │   ├── models.py            ← Pydantic response models
│       │   └── endpoints/
│       │       ├── computers.py     ← list_computers(), get_computer(), ...
│       │       ├── scripts.py       ← list_scripts(), execute_script(), ...
│       │       ├── packages.py      ← list_packages(), install_packages(), ...
│       │       ├── users.py         ← list_users(), add_user(), lock_user(), ...
│       │       └── tags.py          ← add_tags(), remove_tags(), list_tags()
│       └── cli/
│           ├── __init__.py
│           ├── main.py              ← Typer root app, config/login commands
│           ├── output.py            ← Rich/JSON/CSV formatters
│           └── commands/
│               ├── computers.py     ← `lsctl computers` subcommands
│               ├── scripts.py       ← `lsctl scripts` subcommands
│               ├── packages.py      ← `lsctl packages` subcommands
│               └── users.py         ← `lsctl users` subcommands
├── tests/
│   ├── unit/
│   │   ├── test_auth.py             ← HMAC signing tests (offline)
│   │   ├── test_config.py           ← config I/O tests (offline)
│   │   ├── test_models.py           ← Pydantic model tests (offline)
│   │   └── test_client.py           ← HTTP client tests (mocked with respx)
│   └── integration/
│       └── README.md                ← setup guide for integration tests
├── pyproject.toml                   ← project metadata, deps, tool config
├── Makefile                         ← dev task shortcuts
└── README.md                        ← this file
```

---

## Development Guide

### Setup

```bash
git clone https://github.com/gkelley/landscape-ctrl
cd landscape-ctrl

# Create virtual environment and install with dev dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Verify
lsctl --version
```

### Using Make

```bash
make install    # install dev dependencies
make test       # run unit tests
make lint       # ruff lint check
make fmt        # auto-format with ruff
make typecheck  # mypy type checking
make check      # lint + typecheck + test (run before committing)
make clean      # remove build artifacts
```

### Adding a New Command

1. Add endpoint function in `src/landscape_ctrl/api/endpoints/<module>.py`
2. Add CLI command in `src/landscape_ctrl/cli/commands/<module>.py`
3. Add output formatter in `src/landscape_ctrl/cli/output.py` if needed
4. Register the command with the Typer app in its command module
5. Add unit test in `tests/unit/`

### Adding a New Endpoint Module

If Landscape adds a new API category (e.g. `/api/v2/snaps`):

1. Create `src/landscape_ctrl/api/endpoints/snaps.py` with typed async functions
2. Create `src/landscape_ctrl/api/models.py` additions for the response shape
3. Create `src/landscape_ctrl/cli/commands/snaps.py` with Typer commands
4. Register the new Typer app in `cli/main.py`:
   ```python
   from landscape_ctrl.cli.commands import snaps
   app.add_typer(snaps.app, name="snaps")
   ```

---

## Testing

### Unit Tests (no network required)

```bash
pytest tests/unit/ -v
```

Unit tests use `respx` to mock all HTTP calls. No Landscape instance needed.

### Integration Tests (real Landscape required)

```bash
export LSCTL_URL="https://your-landscape.example.com"
export LSCTL_ACCESS_KEY="your-key"
export LANDSCAPE_SECRET_KEY="your-secret"

pytest tests/integration/ -v
```

### Coverage Report

```bash
pytest tests/unit/ --cov=landscape_ctrl --cov-report=html
open htmlcov/index.html
```

---

## How the Two APIs Work

### REST v2 API (primary)

- **Base URL**: `https://<host>/api/v2/`
- **Auth**: `Authorization: Bearer <JWT_TOKEN>`
- **Required**: Landscape 24.04 LTS or newer
- **Pagination**: `?limit=N&offset=N`, response includes `next` and `previous` URL cursors
- **Used for**: Reading computers, scripts, packages, users

Example raw request:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://landscape.example.com/api/v2/computers?query=tag:webserver"
```

### Legacy API (for mutations)

- **Base URL**: `https://<host>/api/`
- **Auth**: HMAC-SHA256 signed query parameters
- **Required**: All Landscape versions
- **Used for**: Script execution, tag management, package installs/upgrades

Example raw request (simplified — real requests require proper signing):
```bash
curl "https://landscape.example.com/api/?action=GetComputers&access_key_id=KEY&signature=..."
```

### Token Refresh Flow

```
lsctl command
    │
    ▼
Has cached token?
    │ Yes → Send request with token
    │           │
    │           ▼
    │       Got 401?
    │           │ No → Return data ✓
    │           │ Yes → Re-authenticate → Retry → Return data ✓
    │
    │ No  → Check config for access_key
    │           │ Has key → Login → Cache token → Retry
    │           │ No key → Error: "Run lsctl login"
    ▼
Error
```

---

## Troubleshooting

### `No config found at ~/.config/lsctl/config.toml`

Run the initial setup:
```bash
lsctl config set --url https://landscape.example.com --access-key KEY --secret-key SECRET
```

### `Authentication failed. Run: lsctl login`

Your token expired. Re-authenticate:
```bash
lsctl login
```

### `No secret key found`

The secret key is stored in the OS keychain. If you're on a new machine or after reinstalling:
```bash
lsctl config set --secret-key YOUR_SECRET_KEY
```

Or set the environment variable for CI:
```bash
export LANDSCAPE_SECRET_KEY="your-secret"
```

### SSL Certificate Errors

If your Landscape instance uses a custom/self-signed certificate:
```bash
lsctl config set --ssl-ca-file /path/to/ca.pem
```

For testing only (not for production):
```bash
lsctl config set --no-verify-ssl
```

### Legacy API Not Working (script execution, tags)

The legacy API requires both `access_key` and `secret_key`. Verify they are set:
```bash
lsctl config show
```

### Command Returns Empty Results

- Check that the query syntax is correct: `lsctl computers ls --query "tag:webserver"`
- Verify you have computers registered: `lsctl computers ls`
- Check Landscape server URL is correct: `lsctl config show`

---

## Roadmap

- [ ] `lsctl tags` subcommand (list, add, remove)
- [ ] `lsctl activities` subcommand (browse activity history)
- [ ] `lsctl snaps` subcommand (snap package management)
- [ ] `lsctl livepatch` subcommand (Livepatch kernel patching)
- [ ] Watch mode: `lsctl scripts status --watch 1001` (poll until complete)
- [ ] Shell completion: `lsctl --install-completion`
- [ ] Profile support: `--profile production` to switch between Landscape instances
- [ ] Async script polling with live output streaming (via activity polling)
- [ ] `lsctl computers bulk-restart --query "tag:staging"` (parallel restarts)

---

## License

MIT — see [LICENSE](LICENSE).
