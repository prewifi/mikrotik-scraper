"""
Inventory management for saving and loading network data.

This module handles serialization and deserialization of network inventory
to JSON and YAML formats, with support for pretty printing and validation.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from models import NetworkInventory, Router

logger = logging.getLogger(__name__)


class InventoryManager:
    """
    Manages network inventory persistence in JSON and YAML formats.

    This class provides methods to save and load network inventory data,
    supporting both JSON and YAML formats with proper validation.
    """

    def __init__(self, output_dir: str = "output"):
        """
        Initialize the inventory manager.

        Parameters:
            output_dir (str): Directory for saving inventory files (default: "output").
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_json(self, inventory: NetworkInventory, filename: Optional[str] = None) -> Path:
        """
        Save inventory to a JSON file.

        Parameters:
            inventory (NetworkInventory): The inventory to save.
            filename (Optional[str]): Custom filename (default: auto-generated with pattern {Hostname}_{YYYYMMDD}_{HHMMSS}).

        Returns:
            Path: Path to the saved file.
        """
        if filename is None:
            # Generate filename with pattern: {Hostname}_{YYYYMMDD}_{HHMMSS}.json
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Use first router's identity as hostname
            if inventory.routers and len(inventory.routers) > 0:
                hostname = inventory.routers[0].identity.replace(" ", "_").replace("/", "_")
                filename = f"{hostname}_{timestamp}.json"
            else:
                filename = f"inventory_{timestamp}.json"

        filepath = self.output_dir / filename

        try:
            # Convert Pydantic model to dict, handling datetime serialization
            inventory_dict = inventory.model_dump(mode="json")

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(inventory_dict, f, indent=2, ensure_ascii=False)

            logger.info(f"Inventory saved to JSON: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error saving inventory to JSON: {e}")
            raise

    def save_router_json(self, router: Router, filename: Optional[str] = None) -> Path:
        """
        Save a single router's data to a JSON file.

        Parameters:
            router (Router): The router to save.
            filename (Optional[str]): Custom filename (default: auto-generated).

        Returns:
            Path: Path to the saved file.
        """
        if filename is None:
            # Generate filename with pattern: {RouterIdentity}_{YYYYMMDD}_{HHMMSS}.json
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            hostname = router.identity.replace(" ", "_").replace("/", "_")
            filename = f"{hostname}_{timestamp}.json"

        filepath = self.output_dir / filename

        try:
            # Create inventory with single router
            inventory = NetworkInventory(routers=[router])
            inventory_dict = inventory.model_dump(mode="json")

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(inventory_dict, f, indent=2, ensure_ascii=False)

            logger.info(f"Router data saved to JSON: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error saving router data to JSON: {e}")
            raise

    def save_yaml(self, inventory: NetworkInventory, filename: Optional[str] = None) -> Path:
        """
        Save inventory to a YAML file.

        Parameters:
            inventory (NetworkInventory): The inventory to save.
            filename (Optional[str]): Custom filename (default: auto-generated with pattern {Hostname}_{YYYYMMDD}_{HHMMSS}).

        Returns:
            Path: Path to the saved file.
        """
        if filename is None:
            # Generate filename with pattern: {Hostname}_{YYYYMMDD}_{HHMMSS}.yaml
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Use first router's identity as hostname
            if inventory.routers and len(inventory.routers) > 0:
                hostname = inventory.routers[0].identity.replace(" ", "_").replace("/", "_")
                filename = f"{hostname}_{timestamp}.yaml"
            else:
                filename = f"inventory_{timestamp}.yaml"

        filepath = self.output_dir / filename

        try:
            # Convert Pydantic model to dict
            inventory_dict = inventory.model_dump(mode="json")

            with open(filepath, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    inventory_dict,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            logger.info(f"Inventory saved to YAML: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error saving inventory to YAML: {e}")
            raise

    def save_router_yaml(self, router: Router, filename: Optional[str] = None) -> Path:
        """
        Save a single router's data to a YAML file.

        Parameters:
            router (Router): The router to save.
            filename (Optional[str]): Custom filename (default: auto-generated).

        Returns:
            Path: Path to the saved file.
        """
        if filename is None:
            # Generate filename with pattern: {RouterIdentity}_{YYYYMMDD}_{HHMMSS}.yaml
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            hostname = router.identity.replace(" ", "_").replace("/", "_")
            filename = f"{hostname}_{timestamp}.yaml"

        filepath = self.output_dir / filename

        try:
            # Create inventory with single router
            inventory = NetworkInventory(routers=[router])
            inventory_dict = inventory.model_dump(mode="json")

            with open(filepath, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    inventory_dict,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            logger.info(f"Router data saved to YAML: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error saving router data to YAML: {e}")
            raise

    def load_json(self, filepath: Path | str) -> NetworkInventory:
        """
        Load inventory from a JSON file.

        Parameters:
            filepath (Path | str): Path to the JSON file.

        Returns:
            NetworkInventory: Loaded inventory.
        """
        filepath = Path(filepath)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            inventory = NetworkInventory(**data)
            logger.info(f"Inventory loaded from JSON: {filepath}")
            return inventory

        except Exception as e:
            logger.error(f"Error loading inventory from JSON: {e}")
            raise

    def load_yaml(self, filepath: Path | str) -> NetworkInventory:
        """
        Load inventory from a YAML file.

        Parameters:
            filepath (Path | str): Path to the YAML file.

        Returns:
            NetworkInventory: Loaded inventory.
        """
        filepath = Path(filepath)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            inventory = NetworkInventory(**data)
            logger.info(f"Inventory loaded from YAML: {filepath}")
            return inventory

        except Exception as e:
            logger.error(f"Error loading inventory from YAML: {e}")
            raise

    def save_summary(self, inventory: NetworkInventory, filename: Optional[str] = None) -> Path:
        """
        Save a human-readable summary of the inventory.

        Parameters:
            inventory (NetworkInventory): The inventory to summarize.
            filename (Optional[str]): Custom filename (default: auto-generated).

        Returns:
            Path: Path to the saved file.
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"summary_{timestamp}.txt"

        filepath = self.output_dir / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("MIKROTIK NETWORK INVENTORY SUMMARY\n")
                f.write("=" * 80 + "\n\n")

                f.write(f"Generated: {inventory.generated_at}\n\n")

                # Statistics
                f.write("STATISTICS\n")
                f.write("-" * 80 + "\n")
                for key, value in inventory.stats.items():
                    f.write(f"  {key.replace('_', ' ').title()}: {value}\n")
                f.write("\n")

                # Routers
                f.write("ROUTERS\n")
                f.write("-" * 80 + "\n")
                for router in inventory.routers:
                    status = "✓" if router.connection_successful else "✗"
                    version = router.system_resource.version if router.system_resource else "N/A"
                    f.write(f"  {status} {router.identity} ({router.ip_address}) - v{version}\n")
                    f.write(f"      Interfaces: {len(router.interfaces)}, ")
                    f.write(f"Neighbors: {len(router.neighbors)}, ")
                    f.write(f"PPPoE Active: {len(router.pppoe_active)}\n")
                f.write("\n")

                # Links
                f.write("NETWORK LINKS\n")
                f.write("-" * 80 + "\n")
                for link_type in ["backbone", "ptp", "ptmp", "pppoe"]:
                    type_links = [l for l in inventory.links if l.link_type == link_type]
                    if type_links:
                        f.write(f"\n  {link_type.upper()} Links ({len(type_links)}):\n")
                        for link in type_links[:10]:  # Show first 10
                            f.write(
                                f"    {link.source_router} [{link.source_interface}] -> "
                                f"{link.destination_router}\n"
                            )
                        if len(type_links) > 10:
                            f.write(f"    ... and {len(type_links) - 10} more\n")
                f.write("\n")

                # Anomalies
                if inventory.anomalies:
                    f.write("ANOMALIES\n")
                    f.write("-" * 80 + "\n")
                    for severity in ["critical", "warning", "info"]:
                        sev_anomalies = [a for a in inventory.anomalies if a.severity == severity]
                        if sev_anomalies:
                            f.write(f"\n  {severity.upper()} ({len(sev_anomalies)}):\n")
                            for anomaly in sev_anomalies[:20]:  # Show first 20
                                f.write(f"    [{anomaly.router}] {anomaly.description}\n")
                                if anomaly.suggestion:
                                    f.write(f"      → {anomaly.suggestion}\n")
                            if len(sev_anomalies) > 20:
                                f.write(f"    ... and {len(sev_anomalies) - 20} more\n")
                f.write("\n")

                f.write("=" * 80 + "\n")

            logger.info(f"Summary saved to: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error saving summary: {e}")
            raise

    def list_inventories(self, format: str = "json") -> list[Path]:
        """
        List all saved inventory files.

        Parameters:
            format (str): File format to list ('json' or 'yaml').

        Returns:
            list[Path]: List of inventory file paths.
        """
        pattern = f"inventory_*.{format}"
        files = sorted(self.output_dir.glob(pattern), reverse=True)
        return files

    def get_latest_inventory(self, format: str = "json") -> Optional[Path]:
        """
        Get the most recent inventory file.

        Parameters:
            format (str): File format ('json' or 'yaml').

        Returns:
            Optional[Path]: Path to the latest inventory file or None.
        """
        files = self.list_inventories(format)
        return files[0] if files else None

    def get_backup_directory(self) -> Path:
        """
        Get or create the backup directory.

        Returns:
            Path: Path to the backup directory.
        """
        backup_dir = self.output_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    def get_router_backup_directory(self, router_identity: str) -> Path:
        """
        Get or create the backup directory for a specific router.

        Parameters:
            router_identity (str): Router identity/hostname.

        Returns:
            Path: Path to the router's backup directory.
        """
        # Sanitize router identity for use in path
        safe_identity = router_identity.replace(" ", "_").replace("/", "_").lower()
        backup_dir = self.get_backup_directory()
        router_dir = backup_dir / safe_identity

        router_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Router backup directory: {router_dir}")

        return router_dir

    def cleanup_old_backups(
        self,
        router_identity: str,
        keep_count: int = 5,
        file_types: list = None,
    ) -> int:
        """
        Clean up old backup files, keeping only the most recent ones.

        Parameters:
            router_identity (str): Router identity/hostname.
            keep_count (int): Number of most recent backups to keep (default: 5).
            file_types (list): File extensions to clean (default: ['.backup', '.rsc']).

        Returns:
            int: Number of files deleted.
        """
        if file_types is None:
            file_types = [".backup", ".rsc"]

        try:
            router_dir = self.get_router_backup_directory(router_identity)
            deleted_count = 0

            for file_ext in file_types:
                # Get all files of this type sorted by modification time
                files = sorted(
                    router_dir.glob(f"*{file_ext}"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )

                # Delete old files
                if len(files) > keep_count:
                    for old_file in files[keep_count:]:
                        try:
                            old_file.unlink()
                            deleted_count += 1
                            logger.info(f"Deleted old backup: {old_file}")
                        except Exception as e:
                            logger.warning(f"Error deleting old backup {old_file}: {e}")

            return deleted_count

        except Exception as e:
            logger.error(f"Error during backup cleanup: {e}")
            return 0

    def get_backup_statistics(self, router_identity: str) -> dict:
        """
        Get statistics about backups for a router.

        Parameters:
            router_identity (str): Router identity/hostname.

        Returns:
            dict: Dictionary with backup statistics.
        """
        try:
            router_dir = self.get_router_backup_directory(router_identity)

            backup_files = list(router_dir.glob("*.backup"))
            rsc_files = list(router_dir.glob("*.rsc"))

            total_size = sum(f.stat().st_size for f in backup_files + rsc_files)

            return {
                "router": router_identity,
                "backup_count": len(backup_files),
                "rsc_count": len(rsc_files),
                "total_files": len(backup_files) + len(rsc_files),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "backup_dir": str(router_dir),
            }

        except Exception as e:
            logger.error(f"Error getting backup statistics: {e}")
            return {}

