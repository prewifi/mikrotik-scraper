
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional

# Mock logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

# Mock Models
@dataclass
class UserGroupConfig:
    name: str
    policy: str
    skin: str = "default"
    comment: str = None

@dataclass
class UserConfig:
    name: str
    group: str
    password: str = None
    address: str = None
    comment: str = None

# Mock Client with the logic to test
class MockClient:
    def __init__(self):
        self.host = "mock-router"
        self.mock_groups = []
        self.mock_users = []
        self.api = self

    def get_resource(self, path):
        return self

    def set(self, id, **kwargs):
        logger.info(f"SET called on {id} with {kwargs}")
        if "policy" in kwargs:
             # Update mock group policy for verification
             for g in self.mock_groups:
                 if g[".id"] == id:
                     g["policy"] = kwargs["policy"]
        if "comment" in kwargs:
             for g in self.mock_groups:
                 if g[".id"] == id:
                     g["comment"] = kwargs["comment"]
             for u in self.mock_users:
                 if u[".id"] == id:
                     u["comment"] = kwargs["comment"]

    def add(self, **kwargs):
        logger.info(f"ADD called with {kwargs}")

    def get(self, id):
        # Mock get for verification
        return [{}] 

    def ensure_user_group(self, config: UserGroupConfig) -> bool:
        existing_group = next((g for g in self.mock_groups if g.get("name") == config.name), None)
        
        properties = {
            "policy": config.policy,
        }
        if config.skin:
            properties["skin"] = config.skin
        if config.comment:
            properties["comment"] = config.comment

        if existing_group:
            # Check if update is needed
            current_policy = existing_group.get("policy", "")
            # Normalize policies for comparison (sort them)
            current_policies = set(p.strip() for p in current_policy.split(",") if p.strip())
            target_policies = set(p.strip() for p in config.policy.split(",") if p.strip())

            # Logic to merge and resolve conflicts (remove !policy if policy is requested)
            final_policies = current_policies.copy()
            
            for target_p in target_policies:
                final_policies.add(target_p)
                # Remove negated version if present (e.g. remove '!ftp' if adding 'ftp')
                negated_p = f"!{target_p}"
                if negated_p in final_policies:
                    final_policies.remove(negated_p)
            
            needs_update = False
            if final_policies != current_policies:
                needs_update = True
                properties["policy"] = ",".join(sorted(final_policies))
                added = final_policies - current_policies
                removed = current_policies - final_policies
                logger.info(f"Adjusting policies for group {config.name}. Added: {added}, Removed: {removed}")
            else:
                if "policy" in properties:
                    del properties["policy"]

            if config.skin and existing_group.get("skin") != config.skin:
                needs_update = True
            
            # Check comment
            if config.comment is not None:
                current_comment = existing_group.get("comment", "")
                if current_comment != config.comment:
                    needs_update = True
                    properties["comment"] = config.comment
            else:
                if "comment" in properties:
                    del properties["comment"]

            if needs_update:
                group_id = existing_group.get(".id") or existing_group.get("id")
                logger.info(f"Updating user group {config.name} on {self.host}")
                self.api.get_resource("/user/group").set(id=group_id, **properties)
                return True
            else:
                logger.info(f"User group {config.name} already correctly configured")
                return False
        else:
            return True # Create path not tested here

# Test Cases
def run_tests():
    client = MockClient()
    
    # Test 1: Policy Merge with Negation
    print("\n--- Test 1: Policy Merge with Negation ---")
    client.mock_groups = [{
        ".id": "*1", 
        "name": "test_group", 
        "policy": "ssh,read,!ftp,write", 
        "skin": "default",
        "comment": "old comment"
    }]
    
    config = UserGroupConfig(name="test_group", policy="ftp,reboot", comment="old comment")
    
    client.ensure_user_group(config)
    
    updated_group = client.mock_groups[0]
    print(f"Final Policy: {updated_group['policy']}")
    
    if "ftp" in updated_group['policy'] and "!ftp" not in updated_group['policy']:
        print("PASS: 'ftp' added and '!ftp' removed")
    else:
        print("FAIL: Negation logic failed")

    # Test 2: Comment Update
    print("\n--- Test 2: Comment Update ---")
    config_comment = UserGroupConfig(name="test_group", policy="ssh", comment="new comment")
    client.ensure_user_group(config_comment)
    
    updated_group = client.mock_groups[0]
    print(f"Final Comment: {updated_group['comment']}")
    
    if updated_group['comment'] == "new comment":
        print("PASS: Comment updated")
    else:
        print("FAIL: Comment not updated")

    # Test 3: Comment Update when existing is missing
    print("\n--- Test 3: Comment Update (Existing Missing) ---")
    client.mock_groups = [{
        ".id": "*2", 
        "name": "group2", 
        "policy": "ssh", 
        # No comment field
    }]
    config_comment_2 = UserGroupConfig(name="group2", policy="ssh", comment="added comment")
    client.ensure_user_group(config_comment_2)
    
    updated_group_2 = client.mock_groups[0]
    print(f"Final Comment: {updated_group_2.get('comment')}")
    
    if updated_group_2.get('comment') == "added comment":
        print("PASS: Missing comment added")
    else:
        print("FAIL: Missing comment not added")

if __name__ == "__main__":
    run_tests()
