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
