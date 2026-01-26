"""
Data models for Mikrotik network inventory.

This module contains Pydantic models for representing network devices,
interfaces, neighbors, PPPoE connections, and related network entities.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, IPvAnyAddress


class LinkType(str, Enum):
    """Type of network link."""

    BACKBONE = "backbone"
    PTP = "ptp"
    PTMP = "ptmp"
    PPPOE = "pppoe"
    UNKNOWN = "unknown"


class InterfaceType(str, Enum):
    """Type of network interface."""

    ETHER = "ether"
    BRIDGE = "bridge"
    WLAN = "wlan"
    VLAN = "vlan"
    PPPOE_CLIENT = "pppoe-client"
    PPPOE_SERVER = "pppoe-server"
    OTHER = "other"


class IPAddress(BaseModel):
    """Represents an IP address configuration on an interface."""

    address: str = Field(..., description="IP address with CIDR notation")
    network: str = Field(..., description="Network address")
    interface: str = Field(..., description="Interface name")
    disabled: bool = Field(default=False, description="Whether the IP is disabled")
    comment: Optional[str] = Field(None, description="Optional comment")


class Neighbor(BaseModel):
    """Represents a network neighbor discovered via LLDP or similar."""

    interface: str = Field(..., description="Local interface name")
    identity: str = Field(..., description="Remote device identity")
    address: Optional[str] = Field(None, description="Remote device address")
    platform: Optional[str] = Field(None, description="Remote device platform")
    version: Optional[str] = Field(None, description="Remote device version")
    mac_address: Optional[str] = Field(None, description="Remote device MAC address")


class PPPoEActive(BaseModel):
    """Represents an active PPPoE connection."""

    name: str = Field(..., description="Connection name")
    service: Optional[str] = Field(None, description="Service name")
    caller_id: str = Field(..., description="Client MAC address")
    address: str = Field(..., description="Assigned IP address")
    uptime: str = Field(..., description="Connection uptime")
    encoding: Optional[str] = Field(None, description="Encoding information")


class PPPoESecret(BaseModel):
    """Represents a PPPoE secret (client credentials)."""

    name: str = Field(..., description="Username")
    password: Optional[str] = Field(None, description="Password (if readable)")
    service: Optional[str] = Field(None, description="Service name")
    profile: str = Field(..., description="Profile name")
    local_address: Optional[str] = Field(None, description="Local (server) IP")
    remote_address: Optional[str] = Field(None, description="Remote (client) IP")
    disabled: bool = Field(default=False, description="Whether the secret is disabled")
    comment: Optional[str] = Field(None, description="Optional comment")


class Interface(BaseModel):
    """Represents a network interface."""

    name: str = Field(..., description="Interface name")
    type: str = Field(..., description="Interface type")
    mtu: Optional[int] = Field(None, description="Maximum transmission unit")
    mac_address: Optional[str] = Field(None, description="MAC address")
    disabled: bool = Field(default=False, description="Whether the interface is disabled")
    running: bool = Field(default=False, description="Whether the interface is running")
    comment: Optional[str] = Field(None, description="Optional comment")

    # Additional fields for wireless interfaces
    ssid: Optional[str] = Field(None, description="SSID for wireless interfaces")
    mode: Optional[str] = Field(None, description="Mode (ap-bridge, station, etc.)")
    frequency: Optional[str] = Field(None, description="Operating frequency")


class SystemResource(BaseModel):
    """Represents system resources and information."""

    uptime: str = Field(..., description="System uptime")
    version: str = Field(..., description="RouterOS version")
    cpu: Optional[str] = Field(None, description="CPU type")
    cpu_load: Optional[int] = Field(None, description="CPU load percentage")
    free_memory: Optional[int] = Field(None, description="Free memory in bytes")
    total_memory: Optional[int] = Field(None, description="Total memory in bytes")
    architecture_name: Optional[str] = Field(None, description="Architecture name")
    board_name: Optional[str] = Field(None, description="Board name")


class Scheduler(BaseModel):
    """Represents a system scheduler on a Mikrotik router."""

    name: str = Field(..., description="Scheduler name")
    start_date: Optional[str] = Field(None, description="Start date")
    start_time: Optional[str] = Field(None, description="Start time")
    interval: Optional[str] = Field(None, description="Execution interval")
    on_event: Optional[str] = Field(None, description="Script/commands to execute")
    policy: Optional[str] = Field(None, description="Policy settings")
    disabled: bool = Field(default=False, description="Whether the scheduler is disabled")
    run_count: Optional[int] = Field(None, description="Number of times executed")
    next_run: Optional[str] = Field(None, description="Next scheduled run time")



class Router(BaseModel):
    """Represents a Mikrotik router with all its collected information."""

    ip_address: str = Field(..., description="Management IP address")
    identity: str = Field(..., description="Router identity/hostname")
    system_resource: Optional[SystemResource] = Field(None, description="System information")

    # Collected data
    interfaces: List[Interface] = Field(default_factory=list, description="Network interfaces")
    ip_addresses: List[IPAddress] = Field(default_factory=list, description="IP addresses")
    neighbors: List[Neighbor] = Field(default_factory=list, description="Network neighbors")
    pppoe_active: List[PPPoEActive] = Field(
        default_factory=list, description="Active PPPoE connections"
    )
    pppoe_secrets: List[PPPoESecret] = Field(default_factory=list, description="PPPoE secrets")
    schedulers: List[Scheduler] = Field(default_factory=list, description="System schedulers")


    # Metadata
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Last update timestamp"
    )
    connection_successful: bool = Field(default=True, description="Connection status")
    connection_error: Optional[str] = Field(None, description="Connection error message")


class Link(BaseModel):
    """Represents a network link between two devices."""

    source_router: str = Field(..., description="Source router IP or identity")
    source_interface: str = Field(..., description="Source interface name")
    destination_router: str = Field(..., description="Destination router IP or identity")
    destination_interface: Optional[str] = Field(None, description="Destination interface name")
    link_type: LinkType = Field(..., description="Type of link")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence level of link detection"
    )
    notes: Optional[str] = Field(None, description="Additional notes or observations")


class Anomaly(BaseModel):
    """Represents a detected anomaly or configuration issue."""

    router: str = Field(..., description="Router IP or identity")
    anomaly_type: str = Field(..., description="Type of anomaly")
    severity: str = Field(..., description="Severity level (info, warning, critical)")
    description: str = Field(..., description="Detailed description")
    affected_object: Optional[str] = Field(None, description="Affected object (interface, etc.)")
    suggestion: Optional[str] = Field(None, description="Suggested remediation")


class IPService(BaseModel):
    """Represents an IP service configuration on a Mikrotik router."""

    name: str = Field(..., description="Service name (api, ssh, www, etc.)")
    port: int = Field(..., description="Service port number")
    disabled: bool = Field(default=False, description="Whether the service is disabled")
    address: Optional[str] = Field(None, description="Allowed IP addresses/networks (comma-separated)")
    certificate: Optional[str] = Field(None, description="Certificate name (for HTTPS services)")


class IPServiceConfig(BaseModel):
    """Represents IP service configuration to apply to a router."""

    service_name: str = Field(..., description="Service name to configure")
    addresses: str = Field(..., description="Comma-separated list of allowed IP addresses/networks")


class IPServiceRollbackInfo(BaseModel):
    """Stores rollback information for IP service configuration."""

    router_ip: str = Field(..., description="Router IP address")
    scheduler_name: str = Field(..., description="Name of the rollback scheduler created")
    original_config: Dict[str, str] = Field(..., description="Original IP service configuration")
    applied_at: datetime = Field(default_factory=datetime.now, description="When configuration was applied")
    rollback_timeout: int = Field(default=300, description="Rollback timeout in seconds")


class UserGroupConfig(BaseModel):
    """Represents a RouterOS user group configuration."""

    name: str = Field(..., description="Group name")
    policy: str = Field(..., description="Comma-separated list of policies")
    skin: Optional[str] = Field(None, description="Skin name")
    comment: Optional[str] = Field(None, description="Comment")


class UserConfig(BaseModel):
    """Represents a RouterOS user configuration."""

    name: str = Field(..., description="Username")
    group: str = Field(..., description="User group")
    password: Optional[str] = Field(None, description="User password")
    address: Optional[str] = Field(None, description="Allowed IP address (ACL)")
    comment: Optional[str] = Field(None, description="Comment")


class SyslogConfig(BaseModel):
    """Represents syslog remote action configuration."""

    remote_server: str = Field(..., description="Remote syslog server IP/hostname")
    remote_port: int = Field(default=514, description="Remote syslog port")
    bsd_syslog: bool = Field(default=True, description="Use BSD syslog format")
    syslog_facility: str = Field(default="local0", description="Syslog facility (local0-local7)")
    syslog_severity: str = Field(default="auto", description="Syslog severity (auto, debug, info, etc.)")


class LoggingTopicConfig(BaseModel):
    """Represents a logging topic configuration."""

    topics: str = Field(..., description="Comma-separated list of topics (e.g., 'info,warning,error')")
    action: str = Field(default="remote", description="Logging action to use (default: remote)")
    prefix: Optional[str] = Field(None, description="Optional prefix for log messages")
    disabled: bool = Field(default=False, description="Whether the logging rule is disabled")


class NetworkInventory(BaseModel):
    """Complete network inventory with routers, links, and anomalies."""

    routers: List[Router] = Field(default_factory=list, description="All routers in inventory")
    links: List[Link] = Field(default_factory=list, description="Detected network links")
    anomalies: List[Anomaly] = Field(default_factory=list, description="Detected anomalies")
    generated_at: datetime = Field(
        default_factory=datetime.now, description="Inventory generation timestamp"
    )
    stats: Dict[str, int] = Field(
        default_factory=dict, description="Statistics about the inventory"
    )
