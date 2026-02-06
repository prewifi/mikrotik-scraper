"""
Mikrotik RouterOS API client - Data collection module.

This module provides methods for collecting data from Mikrotik routers.
"""

import logging
from typing import Dict, List, Optional, Tuple

from models import (
    Interface,
    IPAddress,
    Neighbor,
    PPPoEActive,
    PPPoESecret,
    Router,
    Scheduler,
    SystemResource,
)

logger = logging.getLogger(__name__)


class DataCollectorMixin:
    """Mixin class for data collection methods."""

    def get_system_resource(self) -> Optional[SystemResource]:
        """
        Get system resources and version information.

        Returns:
            Optional[SystemResource]: System resource information or None.
        """
        try:
            resource = self.api.get_resource("/system/resource")
            data = resource.get()

            if data:
                res = data[0]
                return SystemResource(
                    uptime=res.get("uptime", ""),
                    version=res.get("version", ""),
                    cpu_load=int(res.get("cpu-load", 0)),
                    free_memory=int(res.get("free-memory", 0)),
                    total_memory=int(res.get("total-memory", 0)),
                    free_hdd_space=int(res.get("free-hdd-space", 0)),
                    total_hdd_space=int(res.get("total-hdd-space", 0)),
                    architecture_name=res.get("architecture-name", ""),
                    board_name=res.get("board-name", ""),
                    platform=res.get("platform", ""),
                )
            return None

        except Exception as e:
            logger.error(f"Error getting system resources: {e}")
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
            resource = self.api.get_resource("/interface")
            data = resource.get()

            for iface in data:
                interface = Interface(
                    name=iface.get("name", ""),
                    type=iface.get("type", ""),
                    mac_address=iface.get("mac-address", ""),
                    running=iface.get("running", "false") == "true",
                    disabled=iface.get("disabled", "false") == "true",
                    mtu=int(iface.get("mtu", 0)) if iface.get("mtu") else 0,
                    rx_byte=int(iface.get("rx-byte", 0)) if iface.get("rx-byte") else 0,
                    tx_byte=int(iface.get("tx-byte", 0)) if iface.get("tx-byte") else 0,
                )
                interfaces.append(interface)

        except Exception as e:
            logger.error(f"Error getting interfaces: {e}")

        return interfaces

    def get_ip_addresses(self) -> List[IPAddress]:
        """
        Get all configured IP addresses.

        Returns:
            List[IPAddress]: List of IP address objects.
        """
        addresses = []
        try:
            resource = self.api.get_resource("/ip/address")
            data = resource.get()

            for addr in data:
                ip_addr = IPAddress(
                    address=addr.get("address", ""),
                    interface=addr.get("interface", ""),
                    network=addr.get("network", ""),
                    disabled=addr.get("disabled", "false") == "true",
                )
                addresses.append(ip_addr)

        except Exception as e:
            logger.error(f"Error getting IP addresses: {e}")

        return addresses

    def get_neighbors(self) -> List[Neighbor]:
        """
        Get network neighbors (LLDP/CDP discovery).

        Returns:
            List[Neighbor]: List of neighbor objects.
        """
        neighbors = []
        try:
            resource = self.api.get_resource("/ip/neighbor")
            data = resource.get()

            for neigh in data:
                neighbor = Neighbor(
                    interface=neigh.get("interface", ""),
                    address=neigh.get("address", ""),
                    mac_address=neigh.get("mac-address", ""),
                    identity=neigh.get("identity", ""),
                    platform=neigh.get("platform", ""),
                    version=neigh.get("version", ""),
                )
                neighbors.append(neighbor)

        except Exception as e:
            logger.error(f"Error getting neighbors: {e}")

        return neighbors

    def get_pppoe_active(self) -> List[PPPoEActive]:
        """
        Get active PPPoE connections.

        Returns:
            List[PPPoEActive]: List of active PPPoE connection objects.
        """
        connections = []
        try:
            resource = self.api.get_resource("/ppp/active")
            data = resource.get()

            for conn in data:
                pppoe = PPPoEActive(
                    name=conn.get("name", ""),
                    service=conn.get("service", ""),
                    caller_id=conn.get("caller-id", ""),
                    address=conn.get("address", ""),
                    uptime=conn.get("uptime", ""),
                )
                connections.append(pppoe)

        except Exception as e:
            logger.error(f"Error getting active PPPoE connections: {e}")

        return connections

    def get_pppoe_secrets(self) -> List[PPPoESecret]:
        """
        Get PPPoE secrets (client credentials).

        Returns:
            List[PPPoESecret]: List of PPPoE secret objects.
        """
        secrets = []
        try:
            resource = self.api.get_resource("/ppp/secret")
            data = resource.get()

            for secret in data:
                pppoe_secret = PPPoESecret(
                    name=secret.get("name", ""),
                    password=secret.get("password", ""),
                    service=secret.get("service", ""),
                    profile=secret.get("profile", ""),
                    local_address=secret.get("local-address", ""),
                    remote_address=secret.get("remote-address", ""),
                    disabled=secret.get("disabled", "false") == "true",
                )
                secrets.append(pppoe_secret)

        except Exception as e:
            logger.error(f"Error getting PPPoE secrets: {e}")

        return secrets

    def get_schedulers(self) -> List[Scheduler]:
        """
        Get system schedulers.

        Returns:
            List[Scheduler]: List of scheduler objects.
        """
        schedulers = []
        try:
            resource = self.api.get_resource("/system/scheduler")
            data = resource.get()

            for sched in data:
                scheduler = Scheduler(
                    name=sched.get("name", ""),
                    start_time=sched.get("start-time", ""),
                    interval=sched.get("interval", ""),
                    on_event=sched.get("on-event", ""),
                    disabled=sched.get("disabled", "false") == "true",
                )
                schedulers.append(scheduler)

        except Exception as e:
            logger.error(f"Error getting schedulers: {e}")

        return schedulers

    def collect_all_data(
        self, collection_options: Optional[Dict] = None
    ) -> Tuple[Optional[Router], Optional[str]]:
        """
        Collect all data from the router based on collection options.

        Parameters:
            collection_options (Optional[Dict]): Dictionary specifying what data to collect.
                Defaults to collecting all data.

        Returns:
            Tuple[Optional[Router], Optional[str]]: Router object with collected data and error message if any.
        """
        if collection_options is None:
            collection_options = {}

        try:
            # Connect if not connected
            if not self.is_connected:
                if not self.connect():
                    return None, f"Failed to connect to {self.host}"

            # Get identity
            identity = self.get_identity() or self.host

            # Collect data based on options
            interfaces = []
            ip_addresses = []
            neighbors = []
            pppoe_active = []
            pppoe_secrets = []
            system_resource = None
            schedulers = []

            if collection_options.get("interfaces", True):
                interfaces = self.get_interfaces(
                    include_wireless=collection_options.get("wireless", True)
                )

            if collection_options.get("ip_addresses", True):
                ip_addresses = self.get_ip_addresses()

            if collection_options.get("neighbors", True):
                neighbors = self.get_neighbors()

            if collection_options.get("pppoe", True):
                pppoe_active = self.get_pppoe_active()
                pppoe_secrets = self.get_pppoe_secrets()

            if collection_options.get("system", True):
                system_resource = self.get_system_resource()

            if collection_options.get("schedulers", True):
                schedulers = self.get_schedulers()

            # Build router object
            router = Router(
                ip_address=self.host,
                identity=identity,
                connection_successful=True,
                interfaces=interfaces,
                ip_addresses=ip_addresses,
                neighbors=neighbors,
                pppoe_active=pppoe_active,
                pppoe_secrets=pppoe_secrets,
                system_resource=system_resource,
                schedulers=schedulers,
            )

            return router, None

        except Exception as e:
            logger.error(f"Error collecting data from {self.host}: {e}")
            return None, str(e)
