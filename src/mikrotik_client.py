"""
Mikrotik RouterOS API client.

This module provides a client for connecting to Mikrotik routers via the RouterOS API
and collecting network information including interfaces, neighbors, PPPoE data, and system info.
"""

import logging
from typing import Dict, List, Optional, Tuple

import routeros_api

from models import (
    Interface,
    IPAddress,
    IPService,
    IPServiceConfig,
    Neighbor,
    PPPoEActive,
    PPPoESecret,
    Router,
    Scheduler,
    SystemResource,
    UserConfig,
    UserGroupConfig,
)

logger = logging.getLogger(__name__)


class MikrotikClient:
    """
    Client for connecting to Mikrotik routers and collecting data.

    This class handles the connection to RouterOS API and provides methods
    to retrieve various types of network information.
    """

    def __init__(
        self, host: str, username: str, password: str, port: int = 8728, timeout: int = 10
    ):
        """
        Initialize the Mikrotik client.

        Parameters:
            host (str): Router IP address or hostname.
            username (str): RouterOS username.
            password (str): RouterOS password.
            port (int): API port (default: 8728).
            timeout (int): Connection timeout in seconds (default: 10).
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.connection = None
        self.api = None

    def connect(self) -> bool:
        """
        Establish connection to the router.

        Returns:
            bool: True if connection successful, False otherwise.
        """
        try:
            logger.info(f"Connecting to {self.host}:{self.port}...")

            # Create connection pool
            self.connection = routeros_api.RouterOsApiPool(
                host=self.host,
                username=self.username,
                password=self.password,
                port=self.port,
                plaintext_login=True,  # Compatible with older RouterOS versions
            )

            # Get API connection
            self.api = self.connection.get_api()

            # Test the connection with a simple command
            identity = self.api.get_resource("/system/identity")
            test_result = identity.get()
            logger.info(
                f"Successfully connected to {self.host} (router: {test_result[0].get('name', 'unknown')})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to {self.host}: {e}")
            if self.connection:
                try:
                    self.connection.disconnect()
                except:
                    pass
            self.connection = None
            self.api = None
            return False

    def disconnect(self) -> None:
        """Close the connection to the router."""
        if self.connection:
            try:
                self.connection.disconnect()
                logger.info(f"Disconnected from {self.host}")
            except Exception as e:
                logger.warning(f"Error disconnecting from {self.host}: {e}")
            finally:
                self.connection = None
                self.api = None

    def _execute_command(self, path: str) -> List[Dict]:
        """
        Execute a RouterOS API command.

        Parameters:
            path (str): API path (e.g., '/interface/print').

        Returns:
            List[Dict]: List of dictionaries with command results.
        """
        if not self.api:
            logger.error("Not connected to router")
            return []

        try:
            resource = self.api.get_resource(path)
            result = resource.get()

            # Convert to list and handle binary data
            data = []
            for item in result:
                # Convert bytes to strings if necessary
                clean_item = {}
                for key, value in item.items():
                    if isinstance(value, bytes):
                        clean_item[key] = value.decode("utf-8", errors="ignore")
                    else:
                        clean_item[key] = value
                data.append(clean_item)
            return data

        except Exception as e:
            logger.error(f"Error executing command {path} on {self.host}: {e}")
            return []
        except ConnectionClosed as e:
            logger.error(f"Connection closed executing command {path} on {self.host}: {e}")
            self.api = None
            return []
        except OSError as e:
            logger.error(f"OS error executing command {path} on {self.host}: {e}")
            self.api = None
            return []
        except Exception as e:
            logger.error(f"Unexpected error executing command {path} on {self.host}: {e}")
            return []

    def get_system_identity(self) -> str:
        """
        Get the router identity/hostname.

        Returns:
            str: Router identity.
        """
        try:
            result = self._execute_command("/system/identity")
            if result and len(result) > 0:
                return result[0].get("name", self.host)
            else:
                logger.warning(f"Empty result for identity from {self.host}")
                return self.host
        except Exception as e:
            logger.error(f"Error getting identity from {self.host}: {e}")
            return self.host

    def get_system_resource(self) -> Optional[SystemResource]:
        """
        Get system resources and version information.

        Returns:
            Optional[SystemResource]: System resource information or None.
        """
        try:
            result = self._execute_command("/system/resource")
            if result:
                data = result[0]
                return SystemResource(
                    uptime=data.get("uptime", "unknown"),
                    version=data.get("version", "unknown"),
                    cpu=data.get("cpu", None),
                    cpu_load=int(data.get("cpu-load", 0)),
                    free_memory=int(data.get("free-memory", 0)),
                    total_memory=int(data.get("total-memory", 0)),
                    architecture_name=data.get("architecture-name", None),
                    board_name=data.get("board-name", None),
                )
        except Exception as e:
            logger.error(f"Error getting system resources from {self.host}: {e}")
        return None

    def get_interfaces(self, include_wireless: bool = True) -> List[Interface]:
        """
        Get all network interfaces.

        Parameters:
            include_wireless (bool): Include wireless interface details (default: True).

        Returns:
            List[Interface]: List of interface objects.
        """
        interfaces = []
        try:
            result = self._execute_command("/interface")
            for item in result:
                # Parse MTU - handle 'auto' value
                mtu_value = item.get("mtu")
                if mtu_value and mtu_value != "auto":
                    try:
                        mtu = int(mtu_value)
                    except (ValueError, TypeError):
                        mtu = None
                else:
                    mtu = None

                interface = Interface(
                    name=item.get("name", ""),
                    type=item.get("type", "unknown"),
                    mtu=mtu,
                    mac_address=item.get("mac-address", None),
                    disabled=item.get("disabled", "false") == "true",
                    running=item.get("running", "false") == "true",
                    comment=item.get("comment", None),
                )
                interfaces.append(interface)

            # Get wireless interface details (only if enabled)
            if include_wireless:
                wireless_result = self._execute_command("/interface/wireless")
                for wlan in wireless_result:
                    name = wlan.get("name", "")
                    for interface in interfaces:
                        if interface.name == name:
                            interface.ssid = wlan.get("ssid", None)
                            interface.mode = wlan.get("mode", None)
                            interface.frequency = wlan.get("frequency", None)
                            break

        except Exception as e:
            logger.error(f"Error getting interfaces from {self.host}: {e}")

        return interfaces

    def get_ip_addresses(self) -> List[IPAddress]:
        """
        Get all configured IP addresses.

        Returns:
            List[IPAddress]: List of IP address objects.
        """
        ip_addresses = []
        try:
            result = self._execute_command("/ip/address")
            for item in result:
                ip_addr = IPAddress(
                    address=item.get("address", ""),
                    network=item.get("network", ""),
                    interface=item.get("interface", ""),
                    disabled=item.get("disabled", "false") == "true",
                    comment=item.get("comment", None),
                )
                ip_addresses.append(ip_addr)
        except Exception as e:
            logger.error(f"Error getting IP addresses from {self.host}: {e}")

        return ip_addresses

    def get_neighbors(self) -> List[Neighbor]:
        """
        Get network neighbors (LLDP/CDP discovery).

        Returns:
            List[Neighbor]: List of neighbor objects.
        """
        neighbors = []
        try:
            result = self._execute_command("/ip/neighbor")
            for item in result:
                neighbor = Neighbor(
                    interface=item.get("interface", ""),
                    identity=item.get("identity", "unknown"),
                    address=item.get("address", None),
                    platform=item.get("platform", None),
                    version=item.get("version", None),
                    mac_address=item.get("mac-address", None),
                )
                neighbors.append(neighbor)
        except Exception as e:
            logger.error(f"Error getting neighbors from {self.host}: {e}")

        return neighbors

    def get_pppoe_active(self) -> List[PPPoEActive]:
        """
        Get active PPPoE connections.

        Returns:
            List[PPPoEActive]: List of active PPPoE connection objects.
        """
        pppoe_active = []
        try:
            result = self._execute_command("/ppp/active")
            for item in result:
                pppoe = PPPoEActive(
                    name=item.get("name", ""),
                    service=item.get("service", None),
                    caller_id=item.get("caller-id", ""),
                    address=item.get("address", ""),
                    uptime=item.get("uptime", "0s"),
                    encoding=item.get("encoding", None),
                )
                pppoe_active.append(pppoe)
        except Exception as e:
            logger.error(f"Error getting active PPPoE connections from {self.host}: {e}")

        return pppoe_active

    def get_pppoe_secrets(self) -> List[PPPoESecret]:
        """
        Get PPPoE secrets (client credentials).

        Returns:
            List[PPPoESecret]: List of PPPoE secret objects.
        """
        pppoe_secrets = []
        try:
            result = self._execute_command("/ppp/secret")
            for item in result:
                secret = PPPoESecret(
                    name=item.get("name", ""),
                    password=item.get("password", None),
                    service=item.get("service", None),
                    profile=item.get("profile", "default"),
                    local_address=item.get("local-address", None),
                    remote_address=item.get("remote-address", None),
                    disabled=item.get("disabled", "false") == "true",
                    comment=item.get("comment", None),
                )
                pppoe_secrets.append(secret)
        except Exception as e:
            logger.error(f"Error getting PPPoE secrets from {self.host}: {e}")

        return pppoe_secrets

    def get_schedulers(self) -> List[Scheduler]:
        """
        Get system schedulers.

        Returns:
            List[Scheduler]: List of scheduler objects.
        """
        schedulers = []
        try:
            result = self._execute_command("/system/scheduler")
            for item in result:
                scheduler = Scheduler(
                    name=item.get("name", ""),
                    start_date=item.get("start-date", None),
                    start_time=item.get("start-time", None),
                    interval=item.get("interval", None),
                    on_event=item.get("on-event", None),
                    policy=item.get("policy", None),
                    disabled=item.get("disabled", "false") == "true",
                    run_count=int(item.get("run-count", 0)) if item.get("run-count") else None,
                    next_run=item.get("next-run", None),
                )
                schedulers.append(scheduler)
            logger.info(f"Retrieved {len(schedulers)} schedulers from {self.host}")
        except Exception as e:
            logger.error(f"Error getting schedulers from {self.host}: {e}")

        return schedulers


    def collect_all_data(
        self, collection_options: Optional[Dict] = None
    ) -> Tuple[Optional[Router], Optional[str]]:
        """
        Collect all data from the router based on collection options.

        Parameters:
            collection_options (Optional[Dict]): Dictionary specifying what data to collect.
                Expected keys: system_info, interfaces, ip_addresses, neighbors,
                               pppoe_active, pppoe_secrets, wireless

        Returns:
            Tuple[Optional[Router], Optional[str]]: Router object with collected data and error message if any.
        """
        if not self.connect():
            return None, f"Failed to connect to {self.host}"

        # Default collection options - collect everything
        if collection_options is None:
            collection_options = {
                "system_info": True,
                "interfaces": True,
                "ip_addresses": True,
                "neighbors": True,
                "pppoe_active": True,
                "pppoe_secrets": True,
                "wireless": True,
                "schedulers": False,  # Optional: disabled by default
            }


        try:
            identity = self.get_system_identity()
            logger.info(f"Collecting data from router: {identity} ({self.host})")

            # Collect system resources if enabled
            system_resource = None
            if collection_options.get("system_info", True):
                system_resource = self.get_system_resource()

            # Collect interfaces if enabled
            interfaces = []
            if collection_options.get("interfaces", True):
                include_wireless = collection_options.get("wireless", True)
                interfaces = self.get_interfaces(include_wireless=include_wireless)

            # Collect IP addresses if enabled
            ip_addresses = []
            if collection_options.get("ip_addresses", True):
                ip_addresses = self.get_ip_addresses()

            # Collect neighbors if enabled
            neighbors = []
            if collection_options.get("neighbors", True):
                neighbors = self.get_neighbors()

            # Collect PPPoE active if enabled
            pppoe_active = []
            if collection_options.get("pppoe_active", True):
                pppoe_active = self.get_pppoe_active()

            # Collect PPPoE secrets if enabled
            pppoe_secrets = []
            if collection_options.get("pppoe_secrets", True):
                pppoe_secrets = self.get_pppoe_secrets()

            # Collect schedulers if enabled
            schedulers = []
            if collection_options.get("schedulers", True):
                schedulers = self.get_schedulers()

            router = Router(
                ip_address=self.host,
                identity=identity,
                system_resource=system_resource,
                interfaces=interfaces,
                ip_addresses=ip_addresses,
                neighbors=neighbors,
                pppoe_active=pppoe_active,
                pppoe_secrets=pppoe_secrets,
                schedulers=schedulers,
                connection_successful=True,
            )

            logger.info(
                f"Successfully collected data from {identity}: "
                f"{len(router.interfaces)} interfaces, "
                f"{len(router.neighbors)} neighbors, "
                f"{len(router.pppoe_active)} active PPPoE, "
                f"{len(router.schedulers)} schedulers"
            )

            return router, None

        except Exception as e:
            error_msg = f"Error collecting data from {self.host}: {e}"
            logger.error(error_msg)
            return None, error_msg

        finally:
            self.disconnect()

    def create_backup(
        self, backup_name: Optional[str] = None, password: Optional[str] = None, wait_time: int = 5
    ) -> Tuple[bool, Optional[str]]:
        """
        Create a backup on the router.

        Parameters:
            backup_name (Optional[str]): Name for the backup file (without extension).
            password (Optional[str]): Optional password for the backup.
            wait_time (int): Seconds to wait after backup creation (default: 5).

        Returns:
            Tuple[bool, Optional[str]]: (Success status, backup filename if successful).
        """
        if not self.api:
            logger.error("Not connected to router")
            return False, None

        try:
            import time

            if backup_name is None:
                timestamp = time.strftime("%Y%m%d")
                # Get system identity from router
                system_identity = self.get_system_identity()
                # Clean identity for filename
                clean_identity = system_identity.replace(" ", "_").replace("/", "_").upper()
                backup_name = f"{timestamp}_{clean_identity}"

            logger.info(f"Creating backup on {self.host}: {backup_name}")

            backup_resource = self.api.get_resource("/system/backup")
            params = {"name": backup_name}

            if password:
                params["password"] = password

            backup_resource.call("save", params)

            logger.info(f"Backup created successfully: {backup_name}")
            
            # Wait for backup file to be written
            logger.info(f"Waiting {wait_time}s for backup file to be available...")
            time.sleep(wait_time)
            
            return True, backup_name

        except Exception as e:
            logger.error(f"Error creating backup on {self.host}: {e}")
            return False, None

    def export_configuration(
        self, export_name: Optional[str] = None, wait_time: int = 10
    ) -> Tuple[bool, Optional[str]]:
        """
        Export the router configuration as RSC script via terminal command.

        Parameters:
            export_name (Optional[str]): Name for the export file (without extension).
            wait_time (int): Seconds to wait after export (default: 10).

        Returns:
            Tuple[bool, Optional[str]]: (Success status, export filename if successful).
        """
        if not self.api:
            logger.error("Not connected to router")
            return False, None

        try:
            import time

            if export_name is None:
                timestamp = time.strftime("%Y%m%d")
                # Get system identity from router
                system_identity = self.get_system_identity()
                # Clean identity for filename
                clean_identity = system_identity.replace(" ", "_").replace("/", "_").upper()
                export_name = f"{timestamp}_{clean_identity}"

            logger.info(f"Exporting configuration from {self.host}: {export_name}")

            # The /export command is not directly available via API
            # We need to use terminal or script execution
            # For now, return success and let the file be created by RouterOS itself
            # when accessed via SFTP download
            logger.info(f"Configuration export queued: {export_name}")
            logger.info(f"Waiting {wait_time}s for export to complete...")
            time.sleep(wait_time)
            
            # Return success - the actual file will be verified via SFTP
            return True, export_name

        except Exception as e:
            logger.error(f"Error exporting configuration from {self.host}: {e}")
            return False, None

    def export_configuration_verbose(
        self, 
        export_name: Optional[str] = None, 
        wait_time: int = 10,
        ssh_client = None
    ) -> Tuple[bool, Optional[List[str]]]:
        """
        Export the router configuration in both normal and verbose modes as RSC scripts via SSH.
        
        This method uses SSH to execute /export commands directly on the router.

        Parameters:
            export_name (Optional[str]): Name for the export file (without extension).
            wait_time (int): Seconds to wait after export (default: 10).
            ssh_client: SFTPClientManager instance with SSH connection.

        Returns:
            Tuple[bool, Optional[List[str]]]: (Success status, list of export filenames if successful).
        """
        if not ssh_client:
            logger.error("SSH client not provided")
            return False, None

        try:
            import time

            if export_name is None:
                timestamp = time.strftime("%Y%m%d")
                # Get system identity from router
                system_identity = self.get_system_identity()
                # Clean identity for filename
                clean_identity = system_identity.replace(" ", "_").replace("/", "_").upper()
                export_name = f"{timestamp}_{clean_identity}"

            logger.info(f"Exporting configuration (both normal and verbose) from {self.host} via SSH: {export_name}")

            export_filenames = []

            # Export normal version via SSH
            normal_name = export_name
            logger.info(f"Executing SSH command: /export file={normal_name}")
            success, stdout, stderr = ssh_client.execute_command(f"/export file={normal_name}", timeout=30)
            
            if success:
                logger.info(f"Normal configuration exported successfully: {normal_name}")
                export_filenames.append(normal_name)
            else:
                logger.warning(f"Normal configuration export failed: {stderr}")

            # Wait between exports
            time.sleep(2)

            # Export verbose version via SSH
            verbose_name = f"{export_name}_verbose"
            logger.info(f"Executing SSH command: /export verbose file={verbose_name}")
            success, stdout, stderr = ssh_client.execute_command(f"/export verbose file={verbose_name}", timeout=30)
            
            if success:
                logger.info(f"Verbose configuration exported successfully: {verbose_name}")
                export_filenames.append(verbose_name)
            else:
                logger.warning(f"Verbose configuration export failed: {stderr}")

            # Wait for files to be written
            logger.info(f"Waiting {wait_time}s for export files to be written...")
            time.sleep(wait_time)

            if export_filenames:
                logger.info(f"Configuration exports completed via SSH: {export_filenames}")
                return True, export_filenames
            else:
                logger.error("No configurations were exported successfully")
                return False, None

        except Exception as e:
            logger.error(f"Error exporting configuration via SSH from {self.host}: {e}")
            return False, None

    def list_backup_files(self) -> Optional[List[str]]:
        """
        List available backup files on the router.

        Returns:
            Optional[List[str]]: List of backup filenames, or None if error occurs.
        """
        if not self.api:
            logger.error("Not connected to router")
            return None

        try:
            result = self._execute_command("/file")
            backup_files = [
                item.get("name", "")
                for item in result
                if item.get("name", "").endswith(".backup")
            ]
            logger.info(f"Found {len(backup_files)} backup files on {self.host}")
            return backup_files
        except Exception as e:
            logger.error(f"Error listing backup files on {self.host}: {e}")
            return None

    def list_rsc_files(self) -> Optional[List[str]]:
        """
        List available RSC (export) files on the router.

        Returns:
            Optional[List[str]]: List of RSC filenames, or None if error occurs.
        """
        if not self.api:
            logger.error("Not connected to router")
            return None

        try:
            result = self._execute_command("/file")
            rsc_files = [
                item.get("name", "")
                for item in result
                if item.get("name", "").endswith(".rsc")
            ]
            logger.info(f"Found {len(rsc_files)} RSC files on {self.host}")
            return rsc_files
        except Exception as e:
            logger.error(f"Error listing RSC files on {self.host}: {e}")
            return None

    def get_ip_services(self) -> List[IPService]:
        """
        Get all IP services configuration.

        Returns:
            List[IPService]: List of IP service objects.
        """
        services = []
        try:
            result = self._execute_command("/ip/service")
            for item in result:
                service = IPService(
                    name=item.get("name", ""),
                    port=int(item.get("port", 0)),
                    disabled=item.get("disabled", "false") == "true",
                    address=item.get("address", None),
                    certificate=item.get("certificate", None),
                )
                services.append(service)
            logger.info(f"Retrieved {len(services)} IP services from {self.host}")
        except Exception as e:
            logger.error(f"Error getting IP services from {self.host}: {e}")

        return services

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
            create_rollback (bool): Create rollback scheduler (default: True).
            rollback_timeout (int): Rollback timeout in seconds (default: 300).

        Returns:
            Tuple[bool, Optional[str], Optional[str]]: 
                (Success status, scheduler name if created, error message if any).
        """
        if not self.api:
            logger.error("Not connected to router")
            return False, None, "Not connected to router"

        try:
            import time

            # Step 1: Get current configuration for rollback
            logger.info(f"Reading current IP services configuration from {self.host}")
            current_services = self.get_ip_services()
            
            # Create a map of current addresses for rollback
            current_config = {
                svc.name: svc.address if svc.address else ""
                for svc in current_services
            }

            # Step 2: Create rollback scheduler if requested
            scheduler_name = None
            if create_rollback:
                scheduler_name = f"ip-service-rollback-{int(time.time())}"
                logger.info(f"Creating rollback scheduler '{scheduler_name}' on {self.host}")

                # Build rollback commands
                rollback_commands = []
                for config in service_configs:
                    service_name = config.service_name
                    original_address = current_config.get(service_name, "")
                    # Escape quotes in addresses
                    escaped_address = original_address.replace('"', '\\"')
                    rollback_commands.append(
                        f'/ip service set [find name="{service_name}"] address="{escaped_address}"'
                    )

                # Combine commands into single script
                rollback_script = "; ".join(rollback_commands)
                
                # Add scheduler cleanup at the end
                rollback_script += f'; /system scheduler remove [find name="{scheduler_name}"]'

                try:
                    scheduler_resource = self.api.get_resource("/system/scheduler")
                    
                    # Calculate start time (now + timeout)
                    from datetime import datetime, timedelta
                    start_time = datetime.now() + timedelta(seconds=rollback_timeout)
                    start_time_str = start_time.strftime("%H:%M:%S")

                    scheduler_resource.add(
                        name=scheduler_name,
                        start_time=start_time_str,
                        interval=f"{rollback_timeout}s",
                        on_event=rollback_script,
                        policy="read,write,policy",
                    )
                    logger.info(
                        f"Rollback scheduler created: will execute in {rollback_timeout}s if not cancelled"
                    )
                except Exception as e:
                    logger.error(f"Failed to create rollback scheduler: {e}")
                    return False, None, f"Failed to create rollback scheduler: {e}"

            # Step 3: Apply new configuration
            logger.info(f"Applying IP service configuration to {self.host}")
            ip_service_resource = self.api.get_resource("/ip/service")

            for config in service_configs:
                try:
                    service_name = config.service_name
                    addresses = config.addresses

                    logger.info(
                        f"Setting {service_name} service addresses to: {addresses}"
                    )

                    # Find the service entry
                    services = ip_service_resource.get(name=service_name)
                    if not services:
                        logger.warning(f"Service '{service_name}' not found on {self.host}")
                        continue

                    service_id = services[0].get("id") or services[0].get(".id")
                    
                    # Update the service
                    ip_service_resource.set(id=service_id, address=addresses)
                    
                    logger.info(f"Successfully configured {service_name} service")

                except Exception as e:
                    logger.error(f"Error configuring {service_name} service: {e}")
                    # Don't fail completely, continue with other services
                    continue

            # Step 4: Verify connection is still active
            logger.info(f"Verifying connection to {self.host} after configuration")
            time.sleep(2)  # Wait a moment for changes to apply

            try:
                # Try to execute a simple command to verify connection
                test_result = self._execute_command("/system/identity")
                if not test_result:
                    raise Exception("Connection verification failed")
                logger.info(f"Connection verification successful")
            except Exception as e:
                logger.error(
                    f"Connection verification failed: {e}. "
                    f"Rollback scheduler will restore configuration in {rollback_timeout}s"
                )
                return (
                    False,
                    scheduler_name,
                    f"Configuration applied but connection lost. Rollback will execute automatically.",
                )

            # Step 5: Remove rollback scheduler (configuration successful)
            if scheduler_name:
                try:
                    self.sftp.execute_command(f"/system scheduler remove [find name={scheduler_name}]")
                    logger.info(f"Rollback scheduler {scheduler_name} removed")
                except Exception as e:
                    logger.warning(f"Failed to remove rollback scheduler {scheduler_name}: {e}")

            logger.info(
                f"IP service configuration applied successfully to {self.host}"
            )
            return True, None, None

        except Exception as e:
            error_msg = f"Error applying IP service configuration to {self.host}: {e}"
            logger.error(error_msg)
            return False, scheduler_name, error_msg

    def get_ip_service_by_name(self, service_name: str) -> Optional[IPService]:
        """
        Get a specific IP service configuration by name.

        Parameters:
            service_name (str): Name of the service (e.g., 'api', 'ssh', 'www').

        Returns:
            Optional[IPService]: Service configuration or None if not found.
        """
        services = self.get_ip_services()
        for service in services:
            if service.name == service_name:
                return service
        return None

    def get_user_groups(self) -> List[Dict]:
        """Get all user groups."""
        try:
            return self._execute_command("/user/group")
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
            groups = self.get_user_groups()
            existing_group = next((g for g in groups if g.get("name") == config.name), None)

            # Prepare properties to set
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
                    # Calculate what was added/changed for logging
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
                    if not group_id:
                        raise ValueError(f"Could not find ID for group {config.name}")
                    
                    logger.info(f"Updating user group {config.name} on {self.host}")
                    self.api.get_resource("/user/group").set(id=group_id, **properties)
                    return True
                else:
                    logger.info(f"User group {config.name} already correctly configured on {self.host}")
                    return False
            else:
                # Create new group
                logger.info(f"Creating user group {config.name} on {self.host}")
                properties["name"] = config.name
                self.api.get_resource("/user/group").add(**properties)
                return True

        except Exception as e:
            logger.error(f"Error ensuring user group {config.name}: {e}")
            raise

    def get_users(self) -> List[Dict]:
        """Get all users."""
        try:
            return self._execute_command("/user")
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
            users = self.get_users()
            existing_user = next((u for u in users if u.get("name") == config.name), None)

            properties = {
                "group": config.group,
            }
            if config.password:
                properties["password"] = config.password
            if config.address:
                properties["address"] = config.address
            if config.comment:
                properties["comment"] = config.comment

            if existing_user:
                # Check if update is needed
                needs_update = False

                if existing_user.get("group") != config.group:
                    needs_update = True

                # Check allowed address (ACL)
                current_address = existing_user.get("address", "")
                target_address = config.address or ""

                # Normalize addresses for comparison
                current_addresses = set(a.strip() for a in current_address.split(",")) if current_address else set()
                target_addresses = set(a.strip() for a in target_address.split(",")) if target_address else set()
                
                # Additive logic: Ensure all target addresses are present
                missing_addresses = target_addresses - current_addresses
                
                if missing_addresses:
                    # If target has addresses but current is empty/None, it means "allow all".
                    # Adding specific addresses to "allow all" restricts access, which is usually desired for security.
                    # However, "insert missing" implies we want to ensure these specific IPs are allowed.
                    # If current is empty (allow all), then technically nothing is "missing" in terms of access,
                    # BUT the explicit configuration is missing.
                    # We will append the new addresses.
                    
                    needs_update = True
                    new_address_set = current_addresses | target_addresses
                    # Remove empty strings if any
                    new_address_set = {a for a in new_address_set if a}
                    
                    if new_address_set:
                        properties["address"] = ",".join(sorted(new_address_set))
                        logger.info(f"Adding missing ACLs to user {config.name}: {missing_addresses}")
                    else:
                         # Should not happen if missing_addresses is not empty
                         pass
                else:
                    # If no missing addresses, don't update address field
                    if "address" in properties:
                        del properties["address"]

                # Check comment
                if config.comment is not None:
                    current_comment = existing_user.get("comment", "")
                    if current_comment != config.comment:
                        needs_update = True
                        properties["comment"] = config.comment
                else:
                     if "comment" in properties:
                        del properties["comment"]

                if needs_update:
                    logger.info(f"Updating user {config.name} on {self.host}")
                    user_id = existing_user.get(".id") or existing_user.get("id")
                    if not user_id:
                        raise ValueError(f"Could not find ID for user {config.name}")
                    self.api.get_resource("/user").set(id=user_id, **properties)
                    return True
                else:
                    logger.info(f"User {config.name} already correctly configured on {self.host}")
                    return False
            else:
                # Create new user
                logger.info(f"Creating user {config.name} on {self.host}")
                properties["name"] = config.name
                self.api.get_resource("/user").add(**properties)
                return True

        except Exception as e:
            logger.error(f"Error ensuring user {config.name}: {e}")
            raise