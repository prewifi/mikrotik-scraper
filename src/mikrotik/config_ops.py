"""
Mikrotik RouterOS API client - Configuration operations module.

This module provides methods for configuring router settings
(IP services, users, syslog, SNMP).
"""

import logging
from typing import Dict, List, Optional, Tuple

from models import (
    IPService,
    IPServiceConfig,
    LoggingTopicConfig,
    SNMPCommunityConfig,
    SNMPConfig,
    SyslogConfig,
    UserConfig,
    UserGroupConfig,
)

logger = logging.getLogger(__name__)


class ConfigOpsMixin:
    """Mixin class for configuration operations."""

    def get_ip_services(self) -> List[IPService]:
        """
        Get all IP services configuration.

        Returns:
            List[IPService]: List of IP service objects.
        """
        services = []
        try:
            resource = self.api.get_resource("/ip/service")
            data = resource.get()

            for svc in data:
                service = IPService(
                    name=svc.get("name", ""),
                    port=int(svc.get("port", 0)),
                    addresses=svc.get("address", ""),
                    disabled=svc.get("disabled", "false") == "true",
                )
                services.append(service)

        except Exception as e:
            logger.error(f"Error getting IP services: {e}")

        return services

    def get_ip_service_by_name(self, service_name: str) -> Optional[IPService]:
        """
        Get a specific IP service configuration by name.

        Parameters:
            service_name (str): Name of the service (e.g., 'api', 'ssh', 'www').

        Returns:
            Optional[IPService]: Service configuration or None if not found.
        """
        services = self.get_ip_services()
        for svc in services:
            if svc.name == service_name:
                return svc
        return None

    def set_ip_service_addresses(
        self,
        service_configs: List[IPServiceConfig],
        create_rollback: bool = True,
        rollback_timeout: int = 300,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Set IP service addresses with automatic rollback mechanism.

        This method applies IP service configuration and creates a rollback scheduler
        that will automatically revert changes if verification fails.

        Parameters:
            service_configs (List[IPServiceConfig]): List of service configurations to apply.
            create_rollback (bool): Whether to create rollback scheduler (default: True).
            rollback_timeout (int): Timeout in seconds for rollback (default: 300).

        Returns:
            Tuple[bool, Optional[str], Optional[str]]: 
                (Success status, scheduler name if rollback created, error message if any).
        """
        scheduler_name = None

        try:
            # Store original values for rollback
            original_values = {}
            for config in service_configs:
                current = self.get_ip_service_by_name(config.service_name)
                if current:
                    original_values[config.service_name] = current.addresses

            # Create rollback scheduler if enabled
            if create_rollback and original_values:
                rollback_commands = []
                for service_name, original_addr in original_values.items():
                    rollback_commands.append(
                        f'/ip service set [find name="{service_name}"] address="{original_addr}"'
                    )

                rollback_script = ";".join(rollback_commands)
                rollback_script += ';/system scheduler remove [find name~"rollback_"]'

                scheduler_name = f"rollback_{int(__import__('time').time())}"

                scheduler_resource = self.api.get_resource("/system/scheduler")
                scheduler_resource.call(
                    "add",
                    {
                        "name": scheduler_name,
                        "start-time": "startup",
                        "interval": f"{rollback_timeout}s",
                        "on-event": rollback_script,
                    },
                )
                logger.info(f"Created rollback scheduler: {scheduler_name}")

            # Apply new configurations
            service_resource = self.api.get_resource("/ip/service")

            for config in service_configs:
                try:
                    # Find service ID
                    services = service_resource.get()
                    service_id = None
                    for svc in services:
                        if svc.get("name") == config.service_name:
                            service_id = svc.get("id")
                            break

                    if service_id:
                        service_resource.call(
                            "set",
                            {"id": service_id, "address": config.addresses},
                        )
                        logger.info(
                            f"Updated {config.service_name} addresses to: {config.addresses}"
                        )
                    else:
                        logger.warning(f"Service not found: {config.service_name}")

                except Exception as e:
                    logger.error(f"Error setting {config.service_name}: {e}")
                    raise

            return True, scheduler_name, None

        except Exception as e:
            logger.error(f"Error setting IP service addresses: {e}")
            return False, scheduler_name, str(e)

    def get_user_groups(self) -> List[Dict]:
        """Get all user groups."""
        try:
            resource = self.api.get_resource("/user/group")
            return resource.get()
        except Exception as e:
            logger.error(f"Error getting user groups: {e}")
            return []

    def ensure_user_group(self, config: UserGroupConfig) -> bool:
        """
        Ensure a user group exists with the specified configuration.

        Returns:
            bool: True if changes were made, False otherwise.
        """
        try:
            resource = self.api.get_resource("/user/group")
            groups = resource.get()

            # Check if group exists
            existing_group = None
            for group in groups:
                if group.get("name") == config.name:
                    existing_group = group
                    break

            params = {"name": config.name, "policy": config.policy}
            if config.comment:
                params["comment"] = config.comment

            if existing_group:
                # Update existing group
                params["id"] = existing_group.get("id")
                resource.call("set", params)
                logger.info(f"Updated user group: {config.name}")
            else:
                # Create new group
                resource.call("add", params)
                logger.info(f"Created user group: {config.name}")

            return True

        except Exception as e:
            logger.error(f"Error ensuring user group {config.name}: {e}")
            return False

    def get_users(self) -> List[Dict]:
        """Get all users."""
        try:
            resource = self.api.get_resource("/user")
            return resource.get()
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []

    def ensure_user(self, config: UserConfig) -> bool:
        """
        Ensure a user exists with the specified configuration.

        Returns:
            bool: True if changes were made, False otherwise.
        """
        try:
            resource = self.api.get_resource("/user")
            users = resource.get()

            # Check if user exists
            existing_user = None
            for user in users:
                if user.get("name") == config.name:
                    existing_user = user
                    break

            params = {"name": config.name, "group": config.group}
            if config.password:
                params["password"] = config.password
            if config.address:
                params["address"] = config.address
            if config.comment:
                params["comment"] = config.comment

            if existing_user:
                # Update existing user
                params["id"] = existing_user.get("id")
                resource.call("set", params)
                logger.info(f"Updated user: {config.name}")
            else:
                # Create new user
                resource.call("add", params)
                logger.info(f"Created user: {config.name}")

            return True

        except Exception as e:
            logger.error(f"Error ensuring user {config.name}: {e}")
            return False

    def configure_syslog(self, config: SyslogConfig, src_address: str) -> bool:
        """
        Configure the 'remote' syslog action.

        Parameters:
            config (SyslogConfig): Syslog configuration.
            src_address (str): Source address (RouterBoard IP).

        Returns:
            bool: True if changes were made, False otherwise.
        """
        try:
            resource = self.api.get_resource("/system/logging/action")
            actions = resource.get()

            # Find 'remote' action
            remote_action = None
            for action in actions:
                if action.get("name") == "remote":
                    remote_action = action
                    break

            if remote_action:
                params = {
                    "id": remote_action.get("id"),
                    "remote": config.remote_server,
                    "remote-port": str(config.remote_port),
                    "bsd-syslog": "yes" if config.bsd_syslog else "no",
                    "syslog-facility": config.syslog_facility,
                    "syslog-severity": config.syslog_severity,
                    "src-address": src_address,
                }
                resource.call("set", params)
                logger.info(f"Configured syslog to {config.remote_server}:{config.remote_port}")
                return True
            else:
                logger.warning("Remote syslog action not found")
                return False

        except Exception as e:
            logger.error(f"Error configuring syslog: {e}")
            return False

    def configure_logging_topics(self, topics_config: List[LoggingTopicConfig]) -> bool:
        """
        Configure logging topics to use the 'remote' action.

        Parameters:
            topics_config (List[LoggingTopicConfig]): List of topic configurations.

        Returns:
            bool: True if changes were made, False otherwise.
        """
        try:
            resource = self.api.get_resource("/system/logging")
            rules = resource.get()

            for topic_config in topics_config:
                # Find existing rule for this topic
                existing_rule = None
                for rule in rules:
                    if rule.get("topics") == topic_config.topics:
                        existing_rule = rule
                        break

                params = {
                    "topics": topic_config.topics,
                    "action": topic_config.action or "remote",
                    "prefix": topic_config.prefix or "",
                }

                if existing_rule:
                    params["id"] = existing_rule.get("id")
                    resource.call("set", params)
                    logger.info(f"Updated logging rule for topic: {topic_config.topics}")
                else:
                    resource.call("add", params)
                    logger.info(f"Created logging rule for topic: {topic_config.topics}")

            return True

        except Exception as e:
            logger.error(f"Error configuring logging topics: {e}")
            return False

    def configure_snmp(self, config: SNMPConfig, system_identity: Optional[str] = None) -> bool:
        """
        Configure SNMP general settings on the router.

        Parameters:
            config (SNMPConfig): SNMP configuration settings.
            system_identity (Optional[str]): System identity to use as location if not specified.

        Returns:
            bool: True if changes were made, False otherwise.
        """
        try:
            resource = self.api.get_resource("/snmp")
            
            params = {
                "enabled": "yes" if config.enabled else "no",
                "trap-community": config.trap_community,
                "trap-version": str(config.trap_version),
            }

            if config.contact:
                params["contact"] = config.contact

            if config.location:
                params["location"] = config.location
            elif system_identity:
                params["location"] = system_identity

            resource.call("set", params)
            logger.info("Configured SNMP settings")

            # Configure communities if provided
            if config.communities:
                self.configure_snmp_communities(config.communities)

            return True

        except Exception as e:
            logger.error(f"Error configuring SNMP: {e}")
            return False

    def configure_snmp_communities(self, communities: List[SNMPCommunityConfig]) -> bool:
        """
        Configure SNMP communities on the router.

        Parameters:
            communities (List[SNMPCommunityConfig]): List of community configurations.

        Returns:
            bool: True if changes were made, False otherwise.
        """
        try:
            resource = self.api.get_resource("/snmp/community")
            existing = resource.get()

            for comm_config in communities:
                # Find existing community
                existing_comm = None
                for comm in existing:
                    if comm.get("name") == comm_config.name:
                        existing_comm = comm
                        break

                params = {
                    "name": comm_config.name,
                    "addresses": comm_config.addresses or "",
                    "read-access": "yes" if comm_config.read_access else "no",
                    "write-access": "yes" if comm_config.write_access else "no",
                    "security": comm_config.security or "none",
                }

                if comm_config.authentication_protocol:
                    params["authentication-protocol"] = comm_config.authentication_protocol
                if comm_config.authentication_password:
                    params["authentication-password"] = comm_config.authentication_password
                if comm_config.encryption_protocol:
                    params["encryption-protocol"] = comm_config.encryption_protocol
                if comm_config.encryption_password:
                    params["encryption-password"] = comm_config.encryption_password

                if existing_comm:
                    params["id"] = existing_comm.get("id")
                    resource.call("set", params)
                    logger.info(f"Updated SNMP community: {comm_config.name}")
                else:
                    resource.call("add", params)
                    logger.info(f"Created SNMP community: {comm_config.name}")

            return True

        except Exception as e:
            logger.error(f"Error configuring SNMP communities: {e}")
            return False
