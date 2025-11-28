#!/usr/bin/env python3
"""
Test script for User and Group Management functionality.
"""

import argparse
import getpass
import logging
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from mikrotik_client import MikrotikClient
from models import UserConfig, UserGroupConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("test-user-mgmt")

def main():
    parser = argparse.ArgumentParser(description="Test User and Group Management")
    parser.add_argument("-H", "--host", default="192.168.1.1", help="Router IP address")
    parser.add_argument("-u", "--username", default="admin", help="Router username")
    parser.add_argument("-p", "--password", help="Router password")
    parser.add_argument("--port", type=int, default=8728, help="Router API port")
    parser.add_argument("--skip-config-test", action="store_true", help="Skip configuration test (read-only)")
    
    args = parser.parse_args()
    
    password = args.password
    if not password:
        password = getpass.getpass(f"Password for {args.username}@{args.host}: ")

    client = MikrotikClient(args.host, args.username, password, args.port)

    if not client.connect():
        logger.error("Failed to connect to router")
        sys.exit(1)

    logger.info(f"Connected to {args.host}")
    
    try:
        # 1. Test Reading Groups
        logger.info("Reading user groups...")
        groups = client.get_user_groups()
        for g in groups:
            logger.info(f"Found group: {g.get('name')} (Policy: {g.get('policy')})")
            
        # 2. Test Reading Users
        logger.info("Reading users...")
        users = client.get_users()
        for u in users:
            logger.info(f"Found user: {u.get('name')} (Group: {u.get('group')})")
            
        if args.skip_config_test:
            logger.info("Skipping configuration test as requested")
            return

        # 3. Test Creating/Updating Group
        test_group = UserGroupConfig(
            name="test_automation_group",
            policy="ssh,read,test,api",
            comment="Created by test script",
            skin="default"
        )
        
        logger.info(f"Ensuring group {test_group.name}...")
        changed = client.ensure_user_group(test_group)
        logger.info(f"Group change status: {changed}")
        
        # Verify group
        groups = client.get_user_groups()
        found_group = next((g for g in groups if g.get("name") == test_group.name), None)
        if found_group:
            logger.info(f"Group verified: {found_group.get('name')}")
        else:
            logger.error("Group verification failed!")
            
        # 4. Test Creating/Updating User
        test_user = UserConfig(
            name="test_automation_user",
            group="test_automation_group",
            password="TestPassword123!",
            address="192.168.100.0/24",
            comment="Created by test script"
        )
        
        logger.info(f"Ensuring user {test_user.name}...")
        changed = client.ensure_user(test_user)
        logger.info(f"User change status: {changed}")
        
        # Verify user
        users = client.get_users()
        found_user = next((u for u in users if u.get("name") == test_user.name), None)
        if found_user:
            logger.info(f"User verified: {found_user.get('name')} (Group: {found_user.get('group')}, Address: {found_user.get('address')})")
        else:
            logger.error("User verification failed!")
            
        # 5. Test Additive Logic (Merge)
        logger.info("Testing additive logic (merge)...")
        
        # Add a new policy to the config
        test_group.policy = "ssh,read,test,api,reboot" # Added reboot
        logger.info(f"Adding 'reboot' policy to group {test_group.name}...")
        changed_group = client.ensure_user_group(test_group)
        logger.info(f"Group merge status: {changed_group}")
        
        # Verify merge
        groups = client.get_user_groups()
        g = next((g for g in groups if g.get("name") == test_group.name), {})
        if "reboot" in g.get("policy", ""):
             logger.info("Group merge PASSED: 'reboot' policy added")
        else:
             logger.error(f"Group merge FAILED: 'reboot' policy missing. Current: {g.get('policy')}")

        # Add a new ACL to the user
        test_user.address = "192.168.100.0/24,10.0.0.1" # Added 10.0.0.1
        logger.info(f"Adding '10.0.0.1' ACL to user {test_user.name}...")
        changed_user = client.ensure_user(test_user)
        logger.info(f"User merge status: {changed_user}")
        
        # Verify merge
        users = client.get_users()
        u = next((u for u in users if u.get("name") == test_user.name), {})
        if "10.0.0.1" in u.get("address", ""):
             logger.info("User merge PASSED: '10.0.0.1' ACL added")
        else:
             logger.error(f"User merge FAILED: '10.0.0.1' ACL missing. Current: {u.get('address')}")

        # 6. Test Idempotency (Run again)
        logger.info("Testing idempotency (running ensure again)...")
        changed_group = client.ensure_user_group(test_group)
        changed_user = client.ensure_user(test_user)
        
        if not changed_group and not changed_user:
            logger.info("Idempotency test PASSED (no changes made)")
        else:
            logger.warning(f"Idempotency test FAILED (changes made: Group={changed_group}, User={changed_user})")

            
        # Cleanup
        logger.info("Cleaning up test resources...")
        try:
            # Remove user
            user_res = client.api.get_resource("/user")
            u = user_res.get(name=test_user.name)
            if u:
                user_res.remove(id=u[0]["id"])
                logger.info(f"Removed user {test_user.name}")
                
            # Remove group
            group_res = client.api.get_resource("/user/group")
            g = group_res.get(name=test_group.name)
            if g:
                group_res.remove(id=g[0]["id"])
                logger.info(f"Removed group {test_group.name}")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()
