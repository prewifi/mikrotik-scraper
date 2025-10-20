#!/usr/bin/env python3
"""
Simple test script to verify connection to a Mikrotik router.

Usage:
    python examples/test_connection.py <IP> <USERNAME> <PASSWORD>
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from mikrotik_client import MikrotikClient
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "mikrotik_client",
        Path(__file__).parent.parent / "src" / "mikrotik-client.py"
    )
    mikrotik_client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mikrotik_client)
    MikrotikClient = mikrotik_client.MikrotikClient


def test_connection(ip: str, username: str, password: str) -> None:
    """
    Test connection to a Mikrotik router.
    
    Parameters:
        ip (str): Router IP address.
        username (str): RouterOS username.
        password (str): RouterOS password.
    """
    print(f"Testing connection to {ip}...")
    print("-" * 60)

    client = MikrotikClient(ip, username, password)

    if not client.connect():
        print(f"❌ Failed to connect to {ip}")
        return

    print(f"✓ Connected successfully to {ip}")

    # Get identity
    identity = client.get_system_identity()
    print(f"\nRouter Identity: {identity}")

    # Get system resources
    resources = client.get_system_resource()
    if resources:
        print(f"\nSystem Information:")
        print(f"  Version: {resources.version}")
        print(f"  Board: {resources.board_name}")
        print(f"  Architecture: {resources.architecture_name}")
        print(f"  Uptime: {resources.uptime}")
        print(f"  CPU Load: {resources.cpu_load}%")
        print(f"  Memory: {resources.free_memory}/{resources.total_memory} bytes free")

    # Get interfaces
    interfaces = client.get_interfaces()
    print(f"\nInterfaces ({len(interfaces)}):")
    for iface in interfaces[:5]:  # Show first 5
        status = "UP" if iface.running else "DOWN"
        print(f"  [{status}] {iface.name} ({iface.type})")
    if len(interfaces) > 5:
        print(f"  ... and {len(interfaces) - 5} more")

    # Get IP addresses
    ip_addresses = client.get_ip_addresses()
    print(f"\nIP Addresses ({len(ip_addresses)}):")
    for ip_addr in ip_addresses[:5]:  # Show first 5
        print(f"  {ip_addr.address} on {ip_addr.interface}")
    if len(ip_addresses) > 5:
        print(f"  ... and {len(ip_addresses) - 5} more")

    # Get neighbors
    neighbors = client.get_neighbors()
    print(f"\nNeighbors ({len(neighbors)}):")
    for neighbor in neighbors:
        print(f"  {neighbor.identity} on {neighbor.interface}")

    # Get PPPoE
    pppoe_active = client.get_pppoe_active()
    print(f"\nActive PPPoE Connections: {len(pppoe_active)}")

    pppoe_secrets = client.get_pppoe_secrets()
    print(f"PPPoE Secrets: {len(pppoe_secrets)}")

    client.disconnect()
    print("\n" + "=" * 60)
    print("✓ Connection test completed successfully!")


def main():
    """Main entry point."""
    if len(sys.argv) != 4:
        print("Usage: python test_connection.py <IP> <USERNAME> <PASSWORD>")
        print("\nExample:")
        print("  python test_connection.py 192.168.1.1 admin password123")
        sys.exit(1)

    ip = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]

    test_connection(ip, username, password)


if __name__ == "__main__":
    main()
