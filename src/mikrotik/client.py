"""
Mikrotik RouterOS API client - Core module.

This module provides the base client for connecting to Mikrotik routers via the RouterOS API.
"""

import logging
from typing import Dict, List, Optional

import routeros_api

logger = logging.getLogger(__name__)


class MikrotikClientBase:
    """Base client for connecting to Mikrotik routers.

    This class handles the connection to RouterOS API and provides basic methods.
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
        self._connected = False

    def connect(self) -> bool:
        """
        Establish connection to the router.

        Returns:
            bool: True if connection successful, False otherwise.
        """
        try:
            connection = routeros_api.RouterOsApiPool(
                host=self.host,
                username=self.username,
                password=self.password,
                port=self.port,
                plaintext_login=True,
            )
            self.connection = connection
            self.api = connection.get_api()
            self._connected = True
            logger.info(f"Successfully connected to {self.host}")
            return True

        except routeros_api.exceptions.RouterOsApiConnectionError as e:
            logger.error(f"Connection error to {self.host}: {e}")
            self._connected = False
            return False
        except routeros_api.exceptions.RouterOsApiCommunicationError as e:
            logger.error(f"Communication error with {self.host}: {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to {self.host}: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Close the connection to the router."""
        if self.connection:
            try:
                self.connection.disconnect()
                logger.info(f"Disconnected from {self.host}")
            except Exception as e:
                logger.error(f"Error disconnecting from {self.host}: {e}")
            finally:
                self.connection = None
                self.api = None
                self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected and self.api is not None

    def get_identity(self) -> Optional[str]:
        """
        Get the router's system identity.

        Returns:
            Optional[str]: Router identity or None if error.
        """
        try:
            resource = self.api.get_resource("/system/identity")
            data = resource.get()
            if data:
                return data[0].get("name", self.host)
            return self.host
        except Exception as e:
            logger.error(f"Error getting identity from {self.host}: {e}")
            return None

    def get_system_identity(self) -> str:
        """
        Get the router identity/hostname.

        Returns:
            str: Router identity.
        """
        try:
            resource = self.api.get_resource("/system/identity")
            data = resource.get()
            if data:
                return data[0].get("name", self.host)
            return self.host
        except Exception as e:
            logger.error(f"Error getting system identity: {e}")
            return self.host

    def _execute_command(self, path: str) -> List[Dict]:
        """
        Execute a RouterOS API command.

        Parameters:
            path (str): API path (e.g., '/interface/print').

        Returns:
            List[Dict]: List of dictionaries with command results.
        """
        if not self.is_connected:
            logger.error("Not connected to router")
            return []

        try:
            # Split path into resource and action
            # Example: '/interface/print' -> resource='/interface', action='print'
            parts = path.rsplit("/", 1)
            if len(parts) == 2:
                resource_path, action = parts
                if not resource_path:
                    resource_path = "/"
            else:
                resource_path = path
                action = "print"

            resource = self.api.get_resource(resource_path)

            if action == "print":
                return resource.get()
            else:
                # For other actions, we need to construct the command
                logger.warning(f"Action '{action}' not directly supported, using 'print'")
                return resource.get()

        except routeros_api.exceptions.RouterOsApiCommunicationError as e:
            logger.error(f"API communication error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error executing command '{path}': {e}")
            return []
