#!/usr/bin/env python3
"""
Simple debug script to test librouteros connection.
"""

import sys
import logging

logging.basicConfig(level=logging.DEBUG)

try:
    from librouteros import connect
    from librouteros.exceptions import TrapError, FatalError, ConnectionClosed
except ImportError:
    print("Error: librouteros not installed")
    print("Install with: pip install librouteros")
    sys.exit(1)

def test_connection(host, username, password):
    """Test basic connection and commands."""
    print(f"\n{'='*60}")
    print(f"Testing connection to {host}")
    print(f"{'='*60}\n")
    
    api = None
    try:
        # Connect
        print(f"1. Connecting to {host}:8728...")
        api = connect(
            host=host,
            username=username,
            password=password,
            port=8728,
            timeout=10
        )
        print("✓ Connected successfully\n")
        
        # Test identity
        print("2. Getting system identity...")
        try:
            identity_path = api.path('/system/identity')
            identity = list(identity_path)
            print(f"✓ Identity: {identity}")
            if identity:
                print(f"   Router name: {identity[0].get('name', 'unknown')}")
        except Exception as e:
            print(f"✗ Error getting identity: {e}")
        
        print()
        
        # Test system resource
        print("3. Getting system resource...")
        try:
            resource_path = api.path('/system/resource')
            resource = list(resource_path)
            print(f"✓ Resource data received")
            if resource:
                res = resource[0]
                print(f"   Version: {res.get('version', 'N/A')}")
                print(f"   Board: {res.get('board-name', 'N/A')}")
                print(f"   Uptime: {res.get('uptime', 'N/A')}")
        except Exception as e:
            print(f"✗ Error getting resource: {e}")
        
        print()
        
        # Test interfaces
        print("4. Getting interfaces...")
        try:
            interface_path = api.path('/interface')
            interfaces = list(interface_path)
            print(f"✓ Found {len(interfaces)} interfaces")
            for i, iface in enumerate(interfaces[:3], 1):
                name = iface.get('name', 'unknown')
                iface_type = iface.get('type', 'unknown')
                running = iface.get('running', False)
                status = "UP" if running else "DOWN"
                print(f"   {i}. {name} ({iface_type}) - {status}")
            if len(interfaces) > 3:
                print(f"   ... and {len(interfaces) - 3} more")
        except Exception as e:
            print(f"✗ Error getting interfaces: {e}")
        
        print()
        
        # Test IP addresses
        print("5. Getting IP addresses...")
        try:
            ip_path = api.path('/ip/address')
            ips = list(ip_path)
            print(f"✓ Found {len(ips)} IP addresses")
            for i, ip in enumerate(ips[:3], 1):
                addr = ip.get('address', 'unknown')
                iface = ip.get('interface', 'unknown')
                print(f"   {i}. {addr} on {iface}")
            if len(ips) > 3:
                print(f"   ... and {len(ips) - 3} more")
        except Exception as e:
            print(f"✗ Error getting IPs: {e}")
        
        print()
        print(f"{'='*60}")
        print("✓ All tests completed successfully!")
        print(f"{'='*60}\n")
        
    except TrapError as e:
        print(f"\n✗ RouterOS API Error: {e}")
        return False
    except FatalError as e:
        print(f"\n✗ Fatal Error: {e}")
        return False
    except ConnectionClosed as e:
        print(f"\n✗ Connection Closed: {e}")
        return False
    except OSError as e:
        print(f"\n✗ OS Error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if api:
            try:
                print("\nClosing connection...")
                api.close()
                print("✓ Connection closed")
            except Exception as e:
                print(f"Warning: Error closing connection: {e}")
    
    return True


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python test-debug.py <IP> <USERNAME> <PASSWORD>")
        print("\nExample:")
        print("  python test-debug.py 192.168.1.1 admin password")
        sys.exit(1)
    
    host = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    
    success = test_connection(host, username, password)
    sys.exit(0 if success else 1)
