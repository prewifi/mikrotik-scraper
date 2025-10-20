#!/usr/bin/env python3
"""
Test script with proper login handling for newer RouterOS versions.
"""

import sys
import logging

logging.basicConfig(level=logging.DEBUG)

try:
    from librouteros import connect
    from librouteros.login import plain, token
    from librouteros.exceptions import TrapError, FatalError, ConnectionClosed
except ImportError:
    print("Error: librouteros not installed")
    sys.exit(1)

def test_with_plain_login(host, username, password):
    """Test with plain text login (RouterOS 6.43+)."""
    print("\n" + "="*60)
    print(f"Testing PLAIN LOGIN to {host}")
    print("="*60 + "\n")
    
    try:
        # Try with plain login method (for RouterOS 6.43+)
        api = connect(
            host=host,
            username=username,
            password=password,
            port=8728,
            timeout=10,
            login_methods=(plain,)  # Force plain login
        )
        print("✓ Connected with plain login\n")
        
        # Test a command
        identity = list(api.path('/system/identity'))
        print(f"✓ Identity: {identity[0].get('name') if identity else 'unknown'}\n")
        
        api.close()
        return True
    except Exception as e:
        print(f"✗ Plain login failed: {e}\n")
        return False

def test_with_token_login(host, username, password):
    """Test with token login (older RouterOS)."""
    print("="*60)
    print(f"Testing TOKEN LOGIN to {host}")
    print("="*60 + "\n")
    
    try:
        # Try with token login method (older RouterOS)
        api = connect(
            host=host,
            username=username,
            password=password,
            port=8728,
            timeout=10,
            login_methods=(token,)  # Force token login
        )
        print("✓ Connected with token login\n")
        
        # Test a command
        identity = list(api.path('/system/identity'))
        print(f"✓ Identity: {identity[0].get('name') if identity else 'unknown'}\n")
        
        api.close()
        return True
    except Exception as e:
        print(f"✗ Token login failed: {e}\n")
        return False

def test_with_auto_login(host, username, password):
    """Test with automatic login method selection."""
    print("="*60)
    print(f"Testing AUTO LOGIN to {host}")
    print("="*60 + "\n")
    
    try:
        # Let librouteros choose the method
        api = connect(
            host=host,
            username=username,
            password=password,
            port=8728,
            timeout=10
        )
        print("✓ Connected with auto login\n")
        
        # Test a command
        identity = list(api.path('/system/identity'))
        print(f"✓ Identity: {identity[0].get('name') if identity else 'unknown'}\n")
        
        api.close()
        return True
    except Exception as e:
        print(f"✗ Auto login failed: {e}\n")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python test-login-methods.py <IP> <USERNAME> <PASSWORD>")
        sys.exit(1)
    
    host = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    
    # Try all methods
    methods_success = []
    
    if test_with_plain_login(host, username, password):
        methods_success.append("PLAIN")
    
    if test_with_token_login(host, username, password):
        methods_success.append("TOKEN")
    
    if test_with_auto_login(host, username, password):
        methods_success.append("AUTO")
    
    print("\n" + "="*60)
    if methods_success:
        print(f"✓ SUCCESS with methods: {', '.join(methods_success)}")
    else:
        print("✗ ALL METHODS FAILED")
    print("="*60 + "\n")
    
    sys.exit(0 if methods_success else 1)
