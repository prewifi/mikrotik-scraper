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
    Route,
    IPPool,
    Scheduler,
    SystemResource,
)

logger = logging.getLogger(__name__)


def _safe_int(value: str | int | None, default: int = 0) -> int:
    """
    Safely convert a value to integer, handling non-numeric strings like 'auto'.

    Parameters:
        value: The value to convert (can be string, int, or None).
        default: Default value if conversion fails (default: 0).

    Returns:
        int: The converted integer or default value.
    """
    if value is None:
        return default
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


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
                    cpu_load=_safe_int(res.get("cpu-load", 0)),
                    free_memory=_safe_int(res.get("free-memory", 0)),
                    total_memory=_safe_int(res.get("total-memory", 0)),
                    free_hdd_space=_safe_int(res.get("free-hdd-space", 0)),
                    total_hdd_space=_safe_int(res.get("total-hdd-space", 0)),
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
                    mtu=_safe_int(iface.get("mtu")),
                    rx_byte=_safe_int(iface.get("rx-byte")),
                    tx_byte=_safe_int(iface.get("tx-byte")),
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

    def get_routes(self) -> List[Route]:
        """
        Get IP routes.

        Returns:
            List[Route]: List of route objects.
        """
        routes = []
        try:
            resource = self.api.get_resource("/ip/route")
            data = resource.get()

            for route_data in data:
                route = Route(
                    dst_address=route_data.get("dst-address", ""),
                    gateway=route_data.get("gateway", ""),
                    distance=route_data.get("distance", ""),
                    active=route_data.get("active", "false") == "true",
                    static=route_data.get("static", "false") == "true",
                    disabled=route_data.get("disabled", "false") == "true",
                    comment=route_data.get("comment", ""),
                    routing_table=route_data.get("routing-table", route_data.get("routing-mark", "")),
                )
                routes.append(route)

        except Exception as e:
            logger.error(f"Error getting routes: {e}")

        return routes

    def get_ip_pools(self) -> List[IPPool]:
        """
        Get IP address pools.

        Returns:
            List[IPPool]: List of IP pool objects.
        """
        pools = []
        try:
            resource = self.api.get_resource("/ip/pool")
            data = resource.get()

            for pool_data in data:
                pool = IPPool(
                    name=pool_data.get("name", ""),
                    ranges=pool_data.get("ranges", ""),
                    next_pool=pool_data.get("next-pool", ""),
                )
                pools.append(pool)

        except Exception as e:
            logger.error(f"Error getting IP pools: {e}")

        return pools

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
            system_resource = None
            schedulers = []
            routes = []
            ip_pools = []
            ospf_config = None

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

            if collection_options.get("system", True):
                system_resource = self.get_system_resource()

            if collection_options.get("schedulers", True):
                schedulers = self.get_schedulers()

            if collection_options.get("routes", True):
                routes = self.get_routes()

            if collection_options.get("ip_pools", True):
                ip_pools = self.get_ip_pools()

            if collection_options.get("ospf", True):
                ospf_config = self.collect_ospf_config()

            # Build router object
            router = Router(
                ip_address=self.host,
                identity=identity,
                connection_successful=True,
                interfaces=interfaces,
                ip_addresses=ip_addresses,
                neighbors=neighbors,
                pppoe_active=pppoe_active,
                system_resource=system_resource,
                schedulers=schedulers,
                routes=routes,
                ip_pools=ip_pools,
                ospf=ospf_config,
            )

            return router, None

        except Exception as e:
            logger.error(f"Error collecting data from {self.host}: {e}")
            return None, str(e)
