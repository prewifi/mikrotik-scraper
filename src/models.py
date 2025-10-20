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
