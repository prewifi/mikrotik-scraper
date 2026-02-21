"""
Mikrotik RouterOS API client - Backup operations module.

This module provides methods for creating backups and exporting configurations.
"""

import logging
import time
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class BackupOpsMixin:
    """Mixin class for backup and export operations."""

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
        try:
            # Generate backup name if not provided
            if not backup_name:
                identity = self.get_identity() or "backup"
                clean_identity = identity.replace(" ", "_").replace("/", "_").upper()
                timestamp = time.strftime("%Y%m%d")
                backup_name = f"{timestamp}_{clean_identity}"

            # Prepare backup command parameters
            backup_params = {"name": backup_name}
            if password:
                backup_params["password"] = password

            # Execute backup command
            resource = self.api.get_resource("/system/backup")
            resource.call("save", backup_params)

            # Wait for backup to be created
            time.sleep(wait_time)

            logger.info(f"Backup created: {backup_name}.backup")
            return True, backup_name

        except Exception as e:
            logger.error(f"Error creating backup: {e}")
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
        try:
            # Generate export name if not provided
            if not export_name:
                identity = self.get_identity() or "export"
                clean_identity = identity.replace(" ", "_").replace("/", "_").upper()
                timestamp = time.strftime("%Y%m%d")
                export_name = f"{timestamp}_{clean_identity}"

            # Note: RouterOS API doesn't directly support /export command
            # This would typically need to be done via SSH
            logger.warning(
                "API-based export not fully supported. Use SSH for export operations."
            )

            return False, None

        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            return False, None

    def export_configuration_verbose(
        self,
        export_name: Optional[str] = None,
        wait_time: int = 10,
        ssh_client=None,
    ) -> Tuple[bool, List[str]]:
        """
        Export the router configuration in both normal and verbose modes as RSC scripts via SSH.

        This method uses SSH to execute /export commands directly on the router.

        Parameters:
            export_name (Optional[str]): Base name for the export files (without extension).
            wait_time (int): Seconds to wait after export for files to be written (default: 10).
            ssh_client: SFTPClientManager instance for SSH command execution.

        Returns:
            Tuple[bool, List[str]]: (Success status, list of export filenames if successful).
        """
        try:
            # Generate export name if not provided
            if not export_name:
                identity = self.get_identity() or "export"
                clean_identity = identity.replace(" ", "_").replace("/", "_").upper()
                timestamp = time.strftime("%Y%m%d")
                export_name = f"{timestamp}_{clean_identity}"

            export_files = []

            if ssh_client:
                # Normal export
                export_cmd = f'/export file="{export_name}"'
                success, stdout, stderr = ssh_client.execute_command(export_cmd, timeout=30)

                if success:
                    export_files.append(export_name)
                    logger.info(f"Normal export created: {export_name}.rsc")
                else:
                    logger.error(f"Normal export failed: {stderr}")

                # Verbose export
                verbose_name = f"{export_name}_verbose"
                export_cmd_verbose = f'/export verbose file="{verbose_name}"'
                success_v, stdout_v, stderr_v = ssh_client.execute_command(
                    export_cmd_verbose, timeout=30
                )

                if success_v:
                    export_files.append(verbose_name)
                    logger.info(f"Verbose export created: {verbose_name}.rsc")
                else:
                    logger.error(f"Verbose export failed: {stderr_v}")

                # Wait for files to be written
                time.sleep(wait_time)

                return len(export_files) > 0, export_files
            else:
                logger.warning("SSH client not provided. Cannot perform export via SSH.")
                return False, []

        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            return False, []

    def list_backup_files(self) -> Optional[List[str]]:
        """
        List available backup files on the router.

        Returns:
            Optional[List[str]]: List of backup filenames, or None if error occurs.
        """
        try:
            resource = self.api.get_resource("/file")
            files = resource.get()

            backup_files = []
            for f in files:
                name = f.get("name", "")
                if name.endswith(".backup"):
                    backup_files.append(name)

            return backup_files

        except Exception as e:
            logger.error(f"Error listing backup files: {e}")
            return None

    def list_rsc_files(self) -> Optional[List[str]]:
        """
        List available RSC (export) files on the router.

        Returns:
            Optional[List[str]]: List of RSC filenames, or None if error occurs.
        """
        try:
            resource = self.api.get_resource("/file")
            files = resource.get()

            rsc_files = []
            for f in files:
                name = f.get("name", "")
                if name.endswith(".rsc"):
                    rsc_files.append(name)

            return rsc_files

        except Exception as e:
            logger.error(f"Error listing RSC files: {e}")
            return None
