#!/usr/bin/env python3
"""
Test script for IP Services configuration.

This script demonstrates how to configure IP services on Mikrotik routers
using the new set_ip_service_addresses method with automatic rollback.
"""

import argparse
import getpass
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mikrotik_client import MikrotikClient
from models import IPServiceConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_get_ip_services(client: MikrotikClient):
    """Test getting current IP services configuration."""
    print("\n" + "=" * 70)
    print("TEST 1: Get current IP services configuration")
    print("=" * 70)
    
    services = client.get_ip_services()
    
    if services:
        print(f"\nFound {len(services)} IP services:")
        for service in services:
            print(f"\n  Service: {service.name}")
            print(f"    Port: {service.port}")
            print(f"    Disabled: {service.disabled}")
            print(f"    Address: {service.address if service.address else '(any)'}")
        return True
    else:
        print("\n  ✗ Failed to retrieve IP services")
        return False


def test_set_ip_service(client: MikrotikClient):
    """Test setting IP service addresses with rollback."""
    print("\n" + "=" * 70)
    print("TEST 2: Configure IP services with rollback protection")
    print("=" * 70)
    
    # Example configuration - modify these addresses as needed
    test_configs = [
        IPServiceConfig(
            service_name="api",
            addresses="192.168.0.0/16,10.0.0.0/8"
        ),
    ]
    
    print("\nConfiguring services:")
    for config in test_configs:
        print(f"  {config.service_name}: {config.addresses}")
    
    print("\nApplying configuration with 60s rollback timeout...")
    print("(If connection is lost, configuration will auto-revert in 60 seconds)")
    
    success, scheduler_name, error = client.set_ip_service_addresses(
        service_configs=test_configs,
        create_rollback=True,
        rollback_timeout=60,  # Shorter timeout for testing
    )
    
    if success:
        print("\n  ✓ Configuration applied successfully!")
        print("  ✓ Rollback scheduler was created and removed (connection verified)")
        return True
    else:
        print(f"\n  ✗ Configuration failed: {error}")
        if scheduler_name:
            print(f"  ⚠ Rollback scheduler is active: {scheduler_name}")
            print("    Configuration will revert automatically")
        return False


def test_get_specific_service(client: MikrotikClient):
    """Test getting a specific IP service."""
    print("\n" + "=" * 70)
    print("TEST 3: Get specific IP service (api)")
    print("=" * 70)
    
    api_service = client.get_ip_service_by_name("api")
    
    if api_service:
        print(f"\n  Service: {api_service.name}")
        print(f"    Port: {api_service.port}")
        print(f"    Disabled: {api_service.disabled}")
        print(f"    Address: {api_service.address if api_service.address else '(any)'}")
        return True
    else:
        print("\n  ✗ API service not found")
        return False


def main():
    """Main test function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Test IP Services configuration on Mikrotik routers"
    )
    parser.add_argument(
        "-H", "--host",
        default="192.168.1.1",
        help="Router IP address (default: 192.168.1.1)"
    )
    parser.add_argument(
        "-u", "--username",
        default="admin",
        help="Router username (default: admin)"
    )
    parser.add_argument(
        "-p", "--password",
        help="Router password (will prompt if not provided)"
    )
    parser.add_argument(
        "--skip-config-test",
        action="store_true",
        help="Skip the configuration test (only read current config)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("MIKROTIK IP SERVICES CONFIGURATION TEST")
    print("=" * 70)
    
    # Get password if not provided
    if not args.password:
        try:
            args.password = getpass.getpass("Enter password: ")
        except (EOFError, KeyboardInterrupt):
            print("\nError: Password is required")
            sys.exit(1)
    
    if not args.password:
        print("Error: Password is required")
        sys.exit(1)
    
    print(f"\nConnecting to {args.host}...")
    
    # Create client
    client = MikrotikClient(
        host=args.host,
        username=args.username,
        password=args.password,
        port=8728,
        timeout=10
    )
    
    # Connect
    if not client.connect():
        print(f"✗ Failed to connect to {args.host}")
        sys.exit(1)
    
    print(f"✓ Connected to {args.host}")
    
    try:
        # Run tests
        results = []
        
        # Test 1: Get current configuration
        results.append(("Get IP Services", test_get_ip_services(client)))
        
        # Test 2: Configuration test (optional)
        if not args.skip_config_test:
            print("\n" + "=" * 70)
            print("Testing IP service configuration...")
            results.append(("Set IP Services", test_set_ip_service(client)))
            
            # Verify configuration was applied
            print("\n" + "=" * 70)
            print("Verifying configuration...")
            results.append(("Verify Configuration", test_get_specific_service(client)))
        else:
            print("\nSkipping configuration test (use without --skip-config-test to test)")
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        for test_name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"  {test_name}: {status}")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n✓ All tests passed!")
            return 0
        else:
            print("\n✗ Some tests failed")
            return 1
            
    finally:
        client.disconnect()
        print("\nDisconnected from router")


if __name__ == "__main__":
    sys.exit(main())
