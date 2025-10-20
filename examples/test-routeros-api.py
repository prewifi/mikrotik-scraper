#!/usr/bin/env python3
"""
Test connection using routeros-api library (alternative to librouteros).
"""

import sys

try:
    import routeros_api
except ImportError:
    print("Error: routeros-api not installed")
    print("Install with: pip install routeros-api")
    sys.exit(1)

def test_routeros_api(host, username, password):
    """Test connection with routeros-api library."""
    print(f"\nTesting connection to {host} using routeros-api...")
    print("="*60 + "\n")
    
    try:
        # Create connection
        print("1. Connecting...")
        connection = routeros_api.RouterOsApiPool(
            host=host,
            username=username,
            password=password,
            port=8728,
            plaintext_login=True  # Try plain login first
        )
        
        api = connection.get_api()
        print("✓ Connected successfully\n")
        
        # Test identity
        print("2. Getting system identity...")
        identity_resource = api.get_resource('/system/identity')
        identity = identity_resource.get()
        if identity:
            router_name = identity[0].get('name', 'unknown')
            print(f"✓ Router Name: {router_name}\n")
        
        # Test system resource
        print("3. Getting system resource...")
        resource = api.get_resource('/system/resource')
        res_data = resource.get()
        if res_data:
            res = res_data[0]
            print(f"✓ Version: {res.get('version', 'N/A')}")
            print(f"   Board: {res.get('board-name', 'N/A')}")
            print(f"   Uptime: {res.get('uptime', 'N/A')}\n")
        
        # Test interfaces
        print("4. Getting interfaces...")
        interfaces = api.get_resource('/interface')
        iface_list = interfaces.get()
        print(f"✓ Found {len(iface_list)} interfaces:")
        for i, iface in enumerate(iface_list[:5], 1):
            name = iface.get('name', 'unknown')
            iface_type = iface.get('type', 'unknown')
            running = iface.get('running', 'false') == 'true'
            status = "UP" if running else "DOWN"
            print(f"   {i}. {name} ({iface_type}) - {status}")
        if len(iface_list) > 5:
            print(f"   ... and {len(iface_list) - 5} more\n")
        
        # Test IP addresses
        print("5. Getting IP addresses...")
        ip_resource = api.get_resource('/ip/address')
        ips = ip_resource.get()
        print(f"✓ Found {len(ips)} IP addresses:")
        for i, ip in enumerate(ips[:5], 1):
            addr = ip.get('address', 'unknown')
            iface = ip.get('interface', 'unknown')
            print(f"   {i}. {addr} on {iface}")
        if len(ips) > 5:
            print(f"   ... and {len(ips) - 5} more\n")
        
        # Disconnect
        connection.disconnect()
        print("="*60)
        print("✓ All tests passed! routeros-api works correctly.")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python test-routeros-api.py <IP> <USERNAME> <PASSWORD>")
        sys.exit(1)
    
    success = test_routeros_api(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if success else 1)
