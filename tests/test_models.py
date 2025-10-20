"""
Unit tests for the Mikrotik inventory system models.
"""

import pytest
from datetime import datetime
from src.models import (
    Router,
    Interface,
    IPAddress,
    Neighbor,
    PPPoEActive,
    PPPoESecret,
    SystemResource,
    Link,
    LinkType,
    Anomaly,
    NetworkInventory,
)


def test_interface_creation():
    """Test Interface model creation."""
    interface = Interface(
        name="ether1",
        type="ether",
        mtu=1500,
        mac_address="00:11:22:33:44:55",
        disabled=False,
        running=True,
    )
    assert interface.name == "ether1"
    assert interface.type == "ether"
    assert interface.running is True


def test_ip_address_creation():
    """Test IPAddress model creation."""
    ip_addr = IPAddress(
        address="192.168.1.1/24",
        network="192.168.1.0",
        interface="ether1",
    )
    assert ip_addr.address == "192.168.1.1/24"
    assert ip_addr.interface == "ether1"
    assert ip_addr.disabled is False


def test_router_creation():
    """Test Router model creation."""
    router = Router(
        ip_address="192.168.1.1",
        identity="router-01",
    )
    assert router.ip_address == "192.168.1.1"
    assert router.identity == "router-01"
    assert len(router.interfaces) == 0
    assert router.connection_successful is True


def test_link_creation():
    """Test Link model creation."""
    link = Link(
        source_router="router-01",
        source_interface="ether1",
        destination_router="router-02",
        destination_interface="ether1",
        link_type=LinkType.BACKBONE,
    )
    assert link.source_router == "router-01"
    assert link.link_type == LinkType.BACKBONE
    assert link.confidence == 1.0


def test_anomaly_creation():
    """Test Anomaly model creation."""
    anomaly = Anomaly(
        router="router-01",
        anomaly_type="multiple_ips",
        severity="warning",
        description="Multiple IPs on same interface",
    )
    assert anomaly.router == "router-01"
    assert anomaly.severity == "warning"


def test_network_inventory_creation():
    """Test NetworkInventory model creation."""
    router1 = Router(ip_address="192.168.1.1", identity="router-01")
    router2 = Router(ip_address="192.168.1.2", identity="router-02")
    
    link = Link(
        source_router="router-01",
        source_interface="ether1",
        destination_router="router-02",
        link_type=LinkType.BACKBONE,
    )
    
    inventory = NetworkInventory(
        routers=[router1, router2],
        links=[link],
        stats={"total_routers": 2, "total_links": 1},
    )
    
    assert len(inventory.routers) == 2
    assert len(inventory.links) == 1
    assert inventory.stats["total_routers"] == 2


def test_system_resource_creation():
    """Test SystemResource model creation."""
    resource = SystemResource(
        uptime="1w2d3h",
        version="6.49.6",
        cpu="MIPS 24Kc",
        cpu_load=15,
        free_memory=50000000,
        total_memory=128000000,
    )
    assert resource.version == "6.49.6"
    assert resource.cpu_load == 15


def test_pppoe_active_creation():
    """Test PPPoEActive model creation."""
    pppoe = PPPoEActive(
        name="client1",
        caller_id="AA:BB:CC:DD:EE:FF",
        address="10.0.0.100",
        uptime="1d2h3m",
    )
    assert pppoe.name == "client1"
    assert pppoe.address == "10.0.0.100"


def test_pppoe_secret_creation():
    """Test PPPoESecret model creation."""
    secret = PPPoESecret(
        name="client1",
        profile="default",
        password="secret123",
        remote_address="10.0.0.100",
    )
    assert secret.name == "client1"
    assert secret.profile == "default"
    assert secret.disabled is False


def test_neighbor_creation():
    """Test Neighbor model creation."""
    neighbor = Neighbor(
        interface="ether1",
        identity="neighbor-router",
        address="192.168.1.2",
        platform="MikroTik",
    )
    assert neighbor.identity == "neighbor-router"
    assert neighbor.interface == "ether1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
