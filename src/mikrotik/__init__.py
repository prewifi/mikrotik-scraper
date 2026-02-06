"""
Mikrotik RouterOS API client package.

This package provides a modular client for connecting to Mikrotik routers
and performing various operations including data collection, backup, and configuration.
"""

from mikrotik.backup_ops import BackupOpsMixin
from mikrotik.client import MikrotikClientBase
from mikrotik.config_ops import ConfigOpsMixin
from mikrotik.data_collector import DataCollectorMixin


class MikrotikClient(MikrotikClientBase, DataCollectorMixin, BackupOpsMixin, ConfigOpsMixin):
    """
    Complete Mikrotik RouterOS API client.

    This class combines all functionality from the modular components:
    - MikrotikClientBase: Core connection and basic operations
    - DataCollectorMixin: Data collection methods
    - BackupOpsMixin: Backup and export operations
    - ConfigOpsMixin: Configuration operations (IP services, users, syslog, SNMP)

    Example usage:
        client = MikrotikClient("192.168.1.1", "admin", "password")
        if client.connect():
            router, error = client.collect_all_data()
            if router:
                print(f"Connected to {router.identity}")
            client.disconnect()
    """

    pass


__all__ = [
    "MikrotikClient",
    "MikrotikClientBase",
    "DataCollectorMixin",
    "BackupOpsMixin",
    "ConfigOpsMixin",
]
