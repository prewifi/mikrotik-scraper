"""
Mikrotik RouterOS API client - OSPF configuration collector.

This module provides methods for collecting OSPF routing configuration
(Instances, Areas, Networks, Interfaces) from Mikrotik routers.
It outputs ordered, human-readable summaries without LSA analysis.
"""

import logging
from typing import Dict, List, Optional, Tuple

from models import OSPFArea, OSPFInstance, OSPFInterface, OSPFNetwork

logger = logging.getLogger(__name__)


class OSPFCollectorMixin:
    """Mixin class for OSPF configuration collection."""

    def get_ospf_instances(self) -> List[OSPFInstance]:
        """
        Get all OSPF instances.

        Returns:
            List[OSPFInstance]: List of OSPF instance objects.
        """
        instances: list[OSPFInstance] = []
        try:
            resource = self.api.get_resource("/routing/ospf/instance")
            data = resource.get()

            for item in data:
                instance = OSPFInstance(
                    name=item.get("name", "default"),
                    router_id=item.get("router-id"),
                    redistribute_connected=item.get("redistribute-connected"),
                    redistribute_static=item.get("redistribute-static"),
                    redistribute_other_ospf=item.get("redistribute-other-ospf"),
                    metric_default=item.get("metric-default"),
                    disabled=item.get("disabled", "false") == "true",
                    comment=item.get("comment"),
                )
                instances.append(instance)

        except Exception as e:
            logger.error(f"Error getting OSPF instances: {e}")

        return instances

    def get_ospf_areas(self) -> List[OSPFArea]:
        """
        Get all OSPF areas.

        Returns:
            List[OSPFArea]: List of OSPF area objects.
        """
        areas: list[OSPFArea] = []
        try:
            resource = self.api.get_resource("/routing/ospf/area")
            data = resource.get()

            for item in data:
                area = OSPFArea(
                    name=item.get("name", ""),
                    area_id=item.get("area-id", "0.0.0.0"),
                    instance=item.get("instance"),
                    area_type=item.get("type"),
                    disabled=item.get("disabled", "false") == "true",
                    comment=item.get("comment"),
                )
                areas.append(area)

        except Exception as e:
            logger.error(f"Error getting OSPF areas: {e}")

        return areas

    def get_ospf_networks(self) -> List[OSPFNetwork]:
        """
        Get all OSPF network advertisements.

        Returns:
            List[OSPFNetwork]: List of OSPF network objects.
        """
        networks: list[OSPFNetwork] = []
        try:
            resource = self.api.get_resource("/routing/ospf/network")
            data = resource.get()

            for item in data:
                network = OSPFNetwork(
                    network=item.get("network", ""),
                    area=item.get("area"),
                    disabled=item.get("disabled", "false") == "true",
                    comment=item.get("comment"),
                )
                networks.append(network)

        except Exception as e:
            logger.error(f"Error getting OSPF networks: {e}")

        return networks

    def get_ospf_interfaces(self) -> List[OSPFInterface]:
        """
        Get all OSPF interface configurations.

        Returns:
            List[OSPFInterface]: List of OSPF interface objects.
        """
        ospf_interfaces: list[OSPFInterface] = []
        try:
            resource = self.api.get_resource("/routing/ospf/interface")
            data = resource.get()

            for item in data:
                ospf_iface = OSPFInterface(
                    interface=item.get("interface", ""),
                    network_type=item.get("network-type"),
                    cost=item.get("cost"),
                    priority=item.get("priority"),
                    authentication=item.get("authentication"),
                    instance_id=item.get("instance-id"),
                    area=item.get("area"),
                    passive=item.get("passive", "false") == "true",
                    disabled=item.get("disabled", "false") == "true",
                    comment=item.get("comment"),
                )
                ospf_interfaces.append(ospf_iface)

        except Exception as e:
            logger.error(f"Error getting OSPF interfaces: {e}")

        return ospf_interfaces

    def collect_ospf_config(self) -> Dict:
        """
        Collect all OSPF configuration from the router.

        Returns:
            Dict: Dictionary with keys 'instances', 'areas', 'networks', 'interfaces'.
        """
        return {
            "instances": self.get_ospf_instances(),
            "areas": self.get_ospf_areas(),
            "networks": self.get_ospf_networks(),
            "interfaces": self.get_ospf_interfaces(),
        }
