"""
Test the updated MikrotikClient with routeros-api.
"""

import sys
import logging
import importlib.util
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Import module with hyphen in name
spec = importlib.util.spec_from_file_location(
    "mikrotik_client",
    Path(__file__).parent.parent / 'src' / 'mikrotik-client.py'
)
mikrotik_client_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mikrotik_client_module)
MikrotikClient = mikrotik_client_module.MikrotikClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <host> <username> <password>")
        sys.exit(1)
    
    host = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    
    print(f"\nTesting MikrotikClient with {host}...")
    print("=" * 60)
    
    # Create client
    client = MikrotikClient(host, username, password)
    
    # Connect
    print("\n1. Connecting...")
    if not client.connect():
        print("✗ Connection failed!")
        sys.exit(1)
    print("✓ Connected successfully")
    
    # Get identity
    print("\n2. Getting system identity...")
    identity = client.get_system_identity()
    print(f"✓ Router Name: {identity}")
    
    # Get system resources
    print("\n3. Getting system resources...")
    resource = client.get_system_resource()
    if resource:
        print(f"✓ Version: {resource.version}")
        print(f"   Board: {resource.board_name}")
        print(f"   Uptime: {resource.uptime}")
    else:
        print("✗ Failed to get system resources")
    
    # Get interfaces
    print("\n4. Getting interfaces...")
    interfaces = client.get_interfaces()
    print(f"✓ Found {len(interfaces)} interfaces")
    if interfaces:
        for i, iface in enumerate(interfaces[:5], 1):
            status = "UP" if not iface.disabled and iface.running else "DOWN"
            print(f"   {i}. {iface.name} ({iface.type}) - {status}")
        if len(interfaces) > 5:
            print(f"   ... and {len(interfaces) - 5} more")
    
    # Get IP addresses
    print("\n5. Getting IP addresses...")
    addresses = client.get_ip_addresses()
    print(f"✓ Found {len(addresses)} IP addresses")
    if addresses:
        for i, addr in enumerate(addresses[:5], 1):
            print(f"   {i}. {addr.address} on {addr.interface}")
        if len(addresses) > 5:
            print(f"   ... and {len(addresses) - 5} more")
    
    # Get neighbors
    print("\n6. Getting IP neighbors...")
    neighbors = client.get_neighbors()
    print(f"✓ Found {len(neighbors)} neighbors")
    if neighbors:
        for i, neighbor in enumerate(neighbors[:5], 1):
            print(f"   {i}. {neighbor.address} on {neighbor.interface}")
        if len(neighbors) > 5:
            print(f"   ... and {len(neighbors) - 5} more")
    
    # Disconnect
    print("\n7. Disconnecting...")
    client.disconnect()
    print("✓ Disconnected")
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
