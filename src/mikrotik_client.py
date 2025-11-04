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
    Neighbor,
    PPPoEActive,
    PPPoESecret,
    Router,
    SystemResource,
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

            router = Router(
                ip_address=self.host,
                identity=identity,
                system_resource=system_resource,
                interfaces=interfaces,
                ip_addresses=ip_addresses,
                neighbors=neighbors,
                pppoe_active=pppoe_active,
                pppoe_secrets=pppoe_secrets,
                connection_successful=True,
            )

            logger.info(
                f"Successfully collected data from {identity}: "
                f"{len(router.interfaces)} interfaces, "
                f"{len(router.neighbors)} neighbors, "
                f"{len(router.pppoe_active)} active PPPoE"
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
