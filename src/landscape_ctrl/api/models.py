"""
Pydantic models for Landscape API responses.

These map directly to the JSON shapes returned by:
  - REST v2: /api/v2/computers, /api/v2/scripts, etc.
  - Legacy API: action responses

All fields use Optional with defaults so partial responses don't crash.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared / base
# ---------------------------------------------------------------------------


class PaginatedResponse(BaseModel):
    """Envelope for paginated list responses from REST v2."""

    count: int = 0
    next: str | None = None
    previous: str | None = None
    results: list[Any] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Computer / Device
# ---------------------------------------------------------------------------


class NetworkInterface(BaseModel):
    name: str = ""
    ip_addresses: list[str] = Field(default_factory=list)
    mac_address: str = ""


class Computer(BaseModel):
    id: int
    hostname: str = ""
    title: str = ""
    distribution: str | None = ""
    tags: list[str] = Field(default_factory=list)
    access_group: str = ""
    reboot_required: bool = Field(default=False, alias="reboot_required_flag")
    last_ping: datetime | None = None
    last_package_report: datetime | None = None
    total_swap: int | None = None         # bytes
    total_memory: int | None = None       # bytes
    network_interfaces: list[NetworkInterface] = Field(default_factory=list)
    # REST v2 extended fields
    vm_type: str | None = None
    container_info: str | None = None
    comment: str = ""
    clone_id: int | None = None
    last_exchange_time: datetime | None = None
    update_manager_prompt: str | None = None
    cloud_instance_metadata: dict[str, Any] | None = None
    ubuntu_pro_info: dict[str, Any] | None = None
    is_wsl_instance: bool = False
    children: list[int] = Field(default_factory=list)
    parent: int | None = None
    archived: bool = False
    registered_at: datetime | None = None
    distribution_info: dict[str, Any] | None = None

    model_config = {"populate_by_name": True}

    @property
    def ip(self) -> str:
        """Return the first IP address across all interfaces, or empty string."""
        for iface in self.network_interfaces:
            if iface.ip_addresses:
                return iface.ip_addresses[0]
        return ""


class Process(BaseModel):
    pid: int
    name: str = ""
    username: str = ""
    state: str = ""
    vm_size: int | None = None   # KB
    vm_rss: int | None = None    # KB
    cpu: float | None = None


# ---------------------------------------------------------------------------
# Script
# ---------------------------------------------------------------------------


class Script(BaseModel):
    id: int
    title: str = ""
    interpreter: str = ""
    code: str = ""
    time_limit: int | None = None  # seconds
    username: str | None = None
    attachments: list[dict] = Field(default_factory=list)


class ScriptResult(BaseModel):
    computer_id: int
    computer_title: str = ""
    output: str = ""
    return_code: int | None = None
    status: str = ""   # "succeeded", "failed", "timed-out"


class ActivityResult(BaseModel):
    """Generic activity/job result from the legacy API."""
    id: int
    creator: dict | None = None
    creation_time: datetime | None = None
    completion_time: datetime | None = None
    deliver_delay_window: int | None = None
    type: str = ""
    status: str = ""   # "undelivered", "delivered", "succeeded", "failed"
    activity_status: str | None = Field(default=None, alias="activity_status")
    result_code: int | None = None
    result_text: str = ""
    computer_id: int | None = None
    summary: str = ""
    progress: int | None = None
    parent_id: int | None = None
    delivery_time: datetime | None = None
    modification_time: datetime | None = None

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Package
# ---------------------------------------------------------------------------


class Package(BaseModel):
    name: str
    version: str = ""
    architecture: str = ""
    component: str = ""
    section: str = ""
    summary: str = ""
    installed: bool = False
    available: bool = False
    upgrade: bool = False
    held: bool = False
    security: bool = False
    computer_ids: list[int] = Field(default_factory=list)
    # v2 format fields
    current_version: str = ""
    available_version: str = ""


# ---------------------------------------------------------------------------
# Snap
# ---------------------------------------------------------------------------


class Snap(BaseModel):
    name: str
    version: str = ""
    revision: str = ""
    channel: str = ""
    publisher: str = ""
    confinement: str = ""
    description: str = ""


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------


class Alert(BaseModel):
    id: int
    name: str = ""
    description: str = ""
    severity: str = ""
    computer_ids: list[int] = Field(default_factory=list)
    active: bool = True
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Administrator
# ---------------------------------------------------------------------------


class Administrator(BaseModel):
    id: int
    name: str = ""
    email: str = ""
    role: str = ""
    enabled: bool = True


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class Repository(BaseModel):
    id: int
    name: str = ""
    description: str = ""
    mode: str = ""
    uri: str = ""
    distribution: str = ""
    components: list[str] = Field(default_factory=list)
    enabled: bool = True


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------


class Profile(BaseModel):
    """Base profile model shared by all profile types."""
    id: int
    name: str = ""
    description: str = ""
    enabled: bool = True
    access_group: str = ""
    tags: list[str] = Field(default_factory=list)


class PackageProfile(Profile):
    packages: list[str] = Field(default_factory=list)


class ScriptProfile(Profile):
    script_id: int | None = None
    username: str = ""
    time_limit: int | None = None


class SecurityProfile(Profile):
    auto_approve: bool = False
    upgrade_type: str = ""


class RebootProfile(Profile):
    schedule: str = ""
    reboot_window: int | None = None


class RepositoryProfile(Profile):
    repository_id: int | None = None


class RemovalProfile(Profile):
    packages: list[str] = Field(default_factory=list)


class UpgradeProfile(Profile):
    upgrade_type: str = ""
    schedule: str = ""


# ---------------------------------------------------------------------------
# GPG Key
# ---------------------------------------------------------------------------


class GPGKey(BaseModel):
    id: int
    fingerprint: str = ""
    key_id: str = ""
    name: str = ""
    has_secret: bool = False


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------


class Token(BaseModel):
    id: int
    token: str = ""
    title: str = ""
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Event Log
# ---------------------------------------------------------------------------


class EventLogEntry(BaseModel):
    id: int
    event_type: str = ""
    message: str = ""
    timestamp: datetime | None = None
    administrator: str = ""
    computer_id: int | None = None


# ---------------------------------------------------------------------------
# Saved Search
# ---------------------------------------------------------------------------


class SavedSearch(BaseModel):
    id: int
    name: str = ""
    query: str = ""
    default: bool = False


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


class Permission(BaseModel):
    name: str = ""
    scope: str = ""


class Role(BaseModel):
    id: int
    name: str = ""
    description: str = ""
    permissions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


class OSUser(BaseModel):
    name: str
    uid: int | None = None
    gid: int | None = None
    gecos: str = ""
    home: str = ""
    shell: str = ""
    enabled: bool = True
    groups: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Tags / Access Groups
# ---------------------------------------------------------------------------


class AccessGroup(BaseModel):
    name: str
    title: str = ""
    parent: str | None = None


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class LoginResponse(BaseModel):
    token: str
