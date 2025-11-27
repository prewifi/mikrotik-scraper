"""
Network analyzer for identifying links, topologies, and anomalies.

This module analyzes collected Mikrotik router data to identify:
- Backbone links between routers
- Point-to-Point (PTP) and Point-to-Multipoint (PTMP) wireless links
- PPPoE client-server relationships
- Configuration anomalies and potential issues
"""

import logging
from typing import Dict, List, Set, Tuple

from models import (
    Anomaly,
    Link,
    LinkType,
    NetworkInventory,
    Router,
)

logger = logging.getLogger(__name__)


class NetworkAnalyzer:
    """
    Analyzes network topology and identifies links and anomalies.

    This class processes collected router data to understand the network
    structure and detect potential configuration issues.
    """

    def __init__(self, routers: List[Router], config: Dict = None):
        """
        Initialize the network analyzer.

        Parameters:
            routers (List[Router]): List of routers with collected data.
            config (Dict): Analysis configuration options.
        """
        self.routers = routers
        self.router_map: Dict[str, Router] = {r.ip_address: r for r in routers}
        self.identity_map: Dict[str, Router] = {r.identity: r for r in routers}

        # Analysis configuration
        self.config = config or {}
        self.analyze_links = self.config.get("analyze_links", True)
        self.detect_anomalies_enabled = self.config.get("detect_anomalies", True)

    def _find_router_by_identity_or_ip(self, identifier: str) -> Router | None:
        """
        Find a router by identity or IP address.

        Parameters:
            identifier (str): Router identity or IP address.

        Returns:
            Router | None: Found router or None.
        """
        # Try direct IP match
        router = self.router_map.get(identifier)
        if router:
            return router

        # Try identity match
        router = self.identity_map.get(identifier)
        if router:
            return router

        # Try partial IP match (for cases where neighbor reports partial IP)
        for ip, router in self.router_map.items():
            if identifier in ip or ip in identifier:
                return router

        return None

    def analyze_neighbor_links(self) -> List[Link]:
        """
        Analyze neighbor data to identify direct links between routers.

        Returns:
            List[Link]: List of identified links.
        """
        links = []
        seen_pairs: Set[Tuple[str, str]] = set()

        for router in self.routers:
            for neighbor in router.neighbors:
                # Try to find the neighbor router in our inventory
                neighbor_router = self._find_router_by_identity_or_ip(neighbor.identity)

                if neighbor_router:
                    # Create a normalized pair to avoid duplicates
                    pair = tuple(sorted([router.ip_address, neighbor_router.ip_address]))

                    if pair not in seen_pairs:
                        seen_pairs.add(pair)

                        # Determine link type based on interface characteristics
                        link_type = self._determine_link_type(
                            router, neighbor.interface, neighbor_router
                        )

                        link = Link(
                            source_router=router.identity,
                            source_interface=neighbor.interface,
                            destination_router=neighbor_router.identity,
                            destination_interface=None,  # We might not know this
                            link_type=link_type,
                            confidence=0.9,
                            notes=f"Detected via neighbor discovery on {router.identity}",
                        )
                        links.append(link)
                        logger.info(
                            f"Identified {link_type.value} link: "
                            f"{router.identity} -> {neighbor_router.identity}"
                        )
                else:
                    logger.warning(
                        f"Neighbor '{neighbor.identity}' on {router.identity} "
                        f"not found in inventory"
                    )

        return links

    def _determine_link_type(
        self, source_router: Router, interface_name: str, dest_router: Router | None
    ) -> LinkType:
        """
        Determine the type of link based on interface characteristics.

        Parameters:
            source_router (Router): Source router.
            interface_name (str): Interface name on source router.
            dest_router (Router | None): Destination router if known.

        Returns:
            LinkType: Determined link type.
        """
        # Find the interface object
        interface = None
        for iface in source_router.interfaces:
            if iface.name == interface_name:
                interface = iface
                break

        if not interface:
            return LinkType.UNKNOWN

        # Wireless interfaces
        if interface.type == "wlan" or "wlan" in interface.name.lower():
            if interface.mode == "station":
                return LinkType.PTP
            elif interface.mode == "ap-bridge":
                return LinkType.PTMP
            else:
                return LinkType.PTP  # Default for wireless

        # Ethernet interfaces connecting to known routers are likely backbone
        if dest_router and interface.type == "ether":
            return LinkType.BACKBONE

        return LinkType.UNKNOWN

    def analyze_pppoe_links(self) -> List[Link]:
        """
        Analyze PPPoE connections to identify client-server relationships.

        Returns:
            List[Link]: List of PPPoE links.
        """
        links = []

        for router in self.routers:
            for active_conn in router.pppoe_active:
                link = Link(
                    source_router=router.identity,
                    source_interface="pppoe-server",
                    destination_router=active_conn.name,  # Client username
                    destination_interface=active_conn.caller_id,  # Client MAC
                    link_type=LinkType.PPPOE,
                    confidence=1.0,
                    notes=f"Active PPPoE: {active_conn.address}, uptime: {active_conn.uptime}",
                )
                links.append(link)

        logger.info(f"Identified {len(links)} PPPoE client connections")
        return links

    def detect_anomalies(self) -> List[Anomaly]:
        """
        Detect configuration anomalies and potential issues.

        Returns:
            List[Anomaly]: List of detected anomalies.
        """
        anomalies = []

        for router in self.routers:
            # Check for multiple IPs on same interface
            anomalies.extend(self._check_multiple_ips_per_interface(router))

            # Check for disabled interfaces with IPs
            anomalies.extend(self._check_disabled_interfaces_with_ips(router))

            # Check for neighbors not in inventory
            anomalies.extend(self._check_unknown_neighbors(router))

            # Check for PPPoE secrets without active connections
            anomalies.extend(self._check_inactive_pppoe_secrets(router))

            # Check for interface naming inconsistencies
            anomalies.extend(self._check_interface_naming(router))

            # Check for outdated RouterOS version
            anomalies.extend(self._check_routeros_version(router))

            # Check for active rollback schedulers
            anomalies.extend(self._check_active_rollback_schedulers(router))

        logger.info(f"Detected {len(anomalies)} anomalies across all routers")
        return anomalies

    def _check_multiple_ips_per_interface(self, router: Router) -> List[Anomaly]:
        """Check for multiple IP addresses on the same interface."""
        anomalies = []
        interface_ips: Dict[str, List[str]] = {}

        for ip_addr in router.ip_addresses:
            if not ip_addr.disabled:
                if ip_addr.interface not in interface_ips:
                    interface_ips[ip_addr.interface] = []
                interface_ips[ip_addr.interface].append(ip_addr.address)

        for interface, ips in interface_ips.items():
            if len(ips) > 1:
                anomaly = Anomaly(
                    router=router.identity,
                    anomaly_type="multiple_ips_per_interface",
                    severity="info",
                    description=f"Interface {interface} has {len(ips)} IP addresses",
                    affected_object=interface,
                    suggestion="Verify if multiple IPs are intentional",
                )
                anomalies.append(anomaly)

        return anomalies

    def _check_disabled_interfaces_with_ips(self, router: Router) -> List[Anomaly]:
        """Check for disabled interfaces that have IP addresses assigned."""
        anomalies = []
        disabled_interfaces = {i.name for i in router.interfaces if i.disabled}

        for ip_addr in router.ip_addresses:
            if ip_addr.interface in disabled_interfaces and not ip_addr.disabled:
                anomaly = Anomaly(
                    router=router.identity,
                    anomaly_type="ip_on_disabled_interface",
                    severity="warning",
                    description=f"Interface {ip_addr.interface} is disabled but has IP {ip_addr.address}",
                    affected_object=ip_addr.interface,
                    suggestion="Consider disabling the IP or enabling the interface",
                )
                anomalies.append(anomaly)

        return anomalies

    def _check_unknown_neighbors(self, router: Router) -> List[Anomaly]:
        """Check for neighbors not found in the inventory."""
        anomalies = []

        for neighbor in router.neighbors:
            neighbor_router = self._find_router_by_identity_or_ip(neighbor.identity)
            if not neighbor_router:
                anomaly = Anomaly(
                    router=router.identity,
                    anomaly_type="unknown_neighbor",
                    severity="info",
                    description=f"Neighbor '{neighbor.identity}' not found in inventory",
                    affected_object=neighbor.interface,
                    suggestion="Add the neighbor router to inventory or verify identity",
                )
                anomalies.append(anomaly)

        return anomalies

    def _check_inactive_pppoe_secrets(self, router: Router) -> List[Anomaly]:
        """Check for PPPoE secrets without active connections."""
        anomalies = []
        active_names = {conn.name for conn in router.pppoe_active}

        inactive_secrets = [
            secret
            for secret in router.pppoe_secrets
            if not secret.disabled and secret.name not in active_names
        ]

        if len(inactive_secrets) > 10:  # Only report if many inactive
            anomaly = Anomaly(
                router=router.identity,
                anomaly_type="many_inactive_pppoe_secrets",
                severity="info",
                description=f"{len(inactive_secrets)} PPPoE secrets have no active connections",
                affected_object="pppoe-secrets",
                suggestion="Review and clean up unused PPPoE accounts",
            )
            anomalies.append(anomaly)

        return anomalies

    def _check_interface_naming(self, router: Router) -> List[Anomaly]:
        """Check for interface naming inconsistencies."""
        anomalies = []
        uncommented_interfaces = [
            i
            for i in router.interfaces
            if not i.comment and not i.name.startswith("ether") and i.type not in ["bridge"]
        ]

        if uncommented_interfaces and len(uncommented_interfaces) > 3:
            anomaly = Anomaly(
                router=router.identity,
                anomaly_type="uncommented_interfaces",
                severity="info",
                description=f"{len(uncommented_interfaces)} interfaces lack descriptive comments",
                affected_object="interfaces",
                suggestion="Add comments to interfaces for better documentation",
            )
            anomalies.append(anomaly)

        return anomalies

    def _check_routeros_version(self, router: Router) -> List[Anomaly]:
        """Check for outdated RouterOS versions."""
        anomalies = []

        if router.system_resource and router.system_resource.version:
            version = router.system_resource.version
            # Simple check for very old versions (< 6.x)
            try:
                major_version = int(version.split(".")[0])
                if major_version < 6:
                    anomaly = Anomaly(
                        router=router.identity,
                        anomaly_type="outdated_routeros",
                        severity="warning",
                        description=f"RouterOS version {version} is outdated",
                        affected_object="system",
                        suggestion="Consider upgrading to a newer RouterOS version",
                    )
                    anomalies.append(anomaly)
            except (ValueError, IndexError):
                pass  # Can't parse version, skip

        return anomalies

    def _check_active_rollback_schedulers(self, router: Router) -> List[Anomaly]:
        """Check for active IP service rollback schedulers."""
        anomalies = []
        
        # Check for schedulers that look like rollback schedulers
        for scheduler in router.schedulers:
            # Check if it's a rollback scheduler (by name pattern and content)
            is_rollback_scheduler = (
                "rollback" in scheduler.name.lower() or
                (scheduler.on_event and "/ip service set" in scheduler.on_event)
            )
            
            if is_rollback_scheduler and not scheduler.disabled:
                anomaly = Anomaly(
                    router=router.identity,
                    anomaly_type="active_rollback_scheduler",
                    severity="warning",
                    description=f"Active rollback scheduler found: {scheduler.name}",
                    affected_object=scheduler.name,
                    suggestion=(
                        "This scheduler was likely created during IP service configuration. "
                        "If configuration was successful, this scheduler should have been removed. "
                        "Verify IP service configuration and remove scheduler manually if needed."
                    ),
                )
                anomalies.append(anomaly)
        
        return anomalies

    def analyze(self) -> NetworkInventory:
        """
        Perform complete network analysis.

        Returns:
            NetworkInventory: Complete inventory with links and anomalies.
        """
        logger.info(f"Starting analysis of {len(self.routers)} routers...")

        # Identify links (if enabled)
        all_links = []
        if self.analyze_links:
            neighbor_links = self.analyze_neighbor_links()
            pppoe_links = self.analyze_pppoe_links()
            all_links = neighbor_links + pppoe_links
        else:
            logger.info("Link analysis disabled - skipping")

        # Detect anomalies (if enabled)
        anomalies = []
        if self.detect_anomalies_enabled:
            anomalies = self.detect_anomalies()
        else:
            logger.info("Anomaly detection disabled - skipping")

        # Calculate statistics
        stats = {
            "total_routers": len(self.routers),
            "successful_connections": sum(1 for r in self.routers if r.connection_successful),
            "total_interfaces": sum(len(r.interfaces) for r in self.routers),
            "total_neighbors": sum(len(r.neighbors) for r in self.routers),
            "total_links": len(all_links),
            "backbone_links": sum(1 for l in all_links if l.link_type == LinkType.BACKBONE),
            "ptp_links": sum(1 for l in all_links if l.link_type == LinkType.PTP),
            "ptmp_links": sum(1 for l in all_links if l.link_type == LinkType.PTMP),
            "pppoe_connections": sum(1 for l in all_links if l.link_type == LinkType.PPPOE),
            "total_anomalies": len(anomalies),
            "critical_anomalies": sum(1 for a in anomalies if a.severity == "critical"),
            "warning_anomalies": sum(1 for a in anomalies if a.severity == "warning"),
        }

        inventory = NetworkInventory(
            routers=self.routers,
            links=all_links,
            anomalies=anomalies,
            stats=stats,
        )

        logger.info("Analysis complete:")
        logger.info(f"  - {stats['total_links']} links identified")
        logger.info(f"  - {stats['total_anomalies']} anomalies detected")

        return inventory
