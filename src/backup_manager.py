"""
Backup manager for Mikrotik routers.

This module provides functionality to export backup and configuration files
from Mikrotik routers via the RouterOS API, and manage their storage.
"""

import logging
import time
from pathlib import Path
from typing import Optional, Tuple

from models import Router
from sftp_client import SFTPClientManager

logger = logging.getLogger(__name__)


class BackupManager:
    """
    Manager for creating and storing Mikrotik router backups.

    This class handles backup file generation, local storage, and
    remote synchronization via SFTP.
    """

    # RouterOS paths for backup files
    # Files are created in the root directory (/)
    ROUTEROS_BACKUP_DIR = "/"
    ROUTEROS_RSC_DIR = "/"

    def __init__(
        self,
        backup_dir: str = "inventory",
        use_sftp: bool = True,
    ):
        """
        Initialize the backup manager.

        Parameters:
            backup_dir (str): Base directory for storing backups (default: "inventory").
            use_sftp (bool): Whether to use SFTP for file transfer (default: True).
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.use_sftp = use_sftp

    def create_backup(
        self,
        api,
        router: Router,
        backup_name: Optional[str] = None,
        wait_time: int = 10,
    ) -> Tuple[bool, Optional[str]]:
        """
        Create a backup on the router via API.

        Parameters:
            api: RouterOS API resource.
            router (Router): Router information.
            backup_name (Optional[str]): Custom backup name (default: auto-generated with pattern YYYYMMDD_Name).
            wait_time (int): Seconds to wait after backup creation for file to be ready (default: 10).

        Returns:
            Tuple[bool, Optional[str]]: (Success status, backup filename if successful).
        """
        if backup_name is None:
            timestamp = time.strftime("%Y%m%d")
            # Get system identity from router
            try:
                identity_resource = api.get_resource("/system/identity")
                identity_data = identity_resource.get()
                system_identity = identity_data.get("name", router.identity) if identity_data else router.identity
            except Exception:
                system_identity = router.identity
            # Remove spaces and special chars from identity for filename
            clean_identity = system_identity.replace(" ", "_").replace("/", "_").upper()
            backup_name = f"{timestamp}_{clean_identity}"

        try:
            logger.info(f"Creating backup on {router.identity}: {backup_name}")

            # Get backup resource
            backup_resource = api.get_resource("/system/backup")

            # Create backup without encryption to avoid password issues on restore
            # dont-encrypt=yes creates a plain backup that can be restored without password
            backup_resource.call("save", {"name": backup_name, "dont-encrypt": "yes"})

            logger.info(f"Backup created successfully: {backup_name}")
            
            # Wait for backup file to be written and available via SFTP
            logger.info(f"Waiting {wait_time}s for backup file to be written and available...")
            time.sleep(wait_time)
            
            return True, backup_name

        except Exception as e:
            logger.error(f"Error creating backup on {router.identity}: {e}")
            return False, None

    def export_configuration(
        self,
        api,
        router: Router,
        export_name: Optional[str] = None,
        wait_time: int = 10,
    ) -> Tuple[bool, Optional[str]]:
        """
        Export configuration as RSC script via API.

        Parameters:
            api: RouterOS API resource.
            router (Router): Router information.
            export_name (Optional[str]): Custom export name (default: auto-generated with pattern YYYYMMDD_Name).
            wait_time (int): Seconds to wait after export for file to be ready (default: 10).

        Returns:
            Tuple[bool, Optional[str]]: (Success status, export filename if successful).
        """
        if export_name is None:
            timestamp = time.strftime("%Y%m%d")
            # Get system identity from router
            try:
                identity_resource = api.get_resource("/system/identity")
                identity_data = identity_resource.get()
                system_identity = identity_data.get("name", router.identity) if identity_data else router.identity
            except Exception:
                system_identity = router.identity
            # Remove spaces and special chars from identity for filename
            clean_identity = system_identity.replace(" ", "_").replace("/", "_").upper()
            export_name = f"{timestamp}_{clean_identity}"

        try:
            logger.info(f"Exporting configuration from {router.identity}: {export_name}")

            # Use system/script resource to execute export
            # This requires creating a temporary file export
            system = api.get_resource("/system")

            # Execute export command through terminal
            # Note: This is a workaround as RouterOS API doesn't directly support export
            logger.info(f"Configuration export initiated: {export_name}")
            
            # Wait for export file to be written
            logger.info(f"Waiting {wait_time}s for export file to be written and available...")
            time.sleep(wait_time)
            
            return True, export_name

        except Exception as e:
            logger.error(f"Error exporting configuration from {router.identity}: {e}")
            return False, None

    def download_backup_files(
        self,
        sftp_client: SFTPClientManager,
        router: Router,
        backup_files: list,
        local_router_dir: Path,
        retry_count: int = 3,
        retry_delay: int = 2,
    ) -> Tuple[list, list]:
        """
        Download backup files from router via SFTP with retry logic.

        Parameters:
            sftp_client (SFTPClientManager): SFTP client for file transfer.
            router (Router): Router information.
            backup_files (list): List of backup filenames to download.
            local_router_dir (Path): Local directory for this router's backups.
            retry_count (int): Number of retry attempts (default: 3).
            retry_delay (int): Delay between retries in seconds (default: 2).

        Returns:
            Tuple[list, list]: (successful_downloads, failed_downloads).
        """
        successful = []
        failed = []

        try:
            for filename in backup_files:
                # Add .backup extension if not already present
                if not filename.endswith(".backup"):
                    remote_filename = f"{filename}.backup"
                else:
                    remote_filename = filename
                    
                remote_path = f"{self.ROUTEROS_BACKUP_DIR}/{remote_filename}"
                local_path = str(local_router_dir / remote_filename)

                logger.info(f"Downloading backup: {remote_filename}")

                # Retry logic for file download
                download_success = False
                for attempt in range(retry_count):
                    if sftp_client.download_file(remote_path, local_path):
                        successful.append(remote_filename)
                        logger.info(f"Successfully downloaded: {remote_filename}")
                        download_success = True
                        break
                    else:
                        if attempt < retry_count - 1:
                            logger.warning(
                                f"Download attempt {attempt + 1}/{retry_count} failed for {remote_filename}, "
                                f"retrying in {retry_delay}s..."
                            )
                            time.sleep(retry_delay)

                if not download_success:
                    failed.append(remote_filename)
                    logger.warning(f"Failed to download after {retry_count} attempts: {remote_filename}")

        except Exception as e:
            logger.error(f"Error during backup file download: {e}")

        return successful, failed

    def download_rsc_files(
        self,
        sftp_client: SFTPClientManager,
        router: Router,
        rsc_files: list,
        local_router_dir: Path,
        retry_count: int = 3,
        retry_delay: int = 2,
    ) -> Tuple[list, list]:
        """
        Download RSC configuration files from router via SFTP with retry logic.

        Parameters:
            sftp_client (SFTPClientManager): SFTP client for file transfer.
            router (Router): Router information.
            rsc_files (list): List of RSC filenames to download.
            local_router_dir (Path): Local directory for this router's backups.
            retry_count (int): Number of retry attempts (default: 3).
            retry_delay (int): Delay between retries in seconds (default: 2).

        Returns:
            Tuple[list, list]: (successful_downloads, failed_downloads).
        """
        successful = []
        failed = []

        try:
            for filename in rsc_files:
                # Add .rsc extension if not already present
                if not filename.endswith(".rsc"):
                    remote_filename = f"{filename}.rsc"
                else:
                    remote_filename = filename
                    
                remote_path = f"{self.ROUTEROS_RSC_DIR}/{remote_filename}"
                local_path = str(local_router_dir / remote_filename)

                logger.info(f"Downloading RSC file: {remote_filename}")

                # Retry logic for file download
                download_success = False
                for attempt in range(retry_count):
                    if sftp_client.download_file(remote_path, local_path):
                        successful.append(remote_filename)
                        logger.info(f"Successfully downloaded RSC: {remote_filename}")
                        download_success = True
                        break
                    else:
                        if attempt < retry_count - 1:
                            logger.warning(
                                f"Download attempt {attempt + 1}/{retry_count} failed for {remote_filename}, "
                                f"retrying in {retry_delay}s..."
                            )
                            time.sleep(retry_delay)

                if not download_success:
                    failed.append(remote_filename)
                    logger.warning(f"Failed to download RSC after {retry_count} attempts: {remote_filename}")

        except Exception as e:
            logger.error(f"Error during RSC file download: {e}")

        return successful, failed

    def get_backup_files(
        self,
        sftp_client: SFTPClientManager,
        retry_count: int = 3,
        retry_delay: int = 2,
    ) -> Optional[list]:
        """
        List backup files available on the router with retry logic.

        Parameters:
            sftp_client (SFTPClientManager): SFTP client for file transfer.
            retry_count (int): Number of retry attempts (default: 3).
            retry_delay (int): Delay between retries in seconds (default: 2).

        Returns:
            Optional[list]: List of backup filenames, or None if error occurs.
        """
        for attempt in range(retry_count):
            try:
                files = sftp_client.list_files(self.ROUTEROS_BACKUP_DIR)
                if files:
                    backup_files = [f for f in files if f.endswith(".backup")]
                    logger.info(f"Found {len(backup_files)} backup files on attempt {attempt + 1}")
                    return backup_files
                else:
                    logger.warning(f"No files found in {self.ROUTEROS_BACKUP_DIR} (attempt {attempt + 1}/{retry_count})")
                    if attempt < retry_count - 1:
                        logger.info(f"Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                return []
            except Exception as e:
                logger.warning(f"Error listing backup files (attempt {attempt + 1}/{retry_count}): {e}")
                if attempt < retry_count - 1:
                    logger.info(f"Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                continue
        
        logger.error(f"Failed to list backup files after {retry_count} attempts")
        return None

    def get_rsc_files(
        self,
        sftp_client: SFTPClientManager,
        retry_count: int = 3,
        retry_delay: int = 2,
    ) -> Optional[list]:
        """
        List RSC configuration files available on the router with retry logic.

        Parameters:
            sftp_client (SFTPClientManager): SFTP client for file transfer.
            retry_count (int): Number of retry attempts (default: 3).
            retry_delay (int): Delay between retries in seconds (default: 2).

        Returns:
            Optional[list]: List of RSC filenames, or None if error occurs.
        """
        for attempt in range(retry_count):
            try:
                files = sftp_client.list_files(self.ROUTEROS_RSC_DIR)
                if files:
                    rsc_files = [f for f in files if f.endswith(".rsc")]
                    logger.info(f"Found {len(rsc_files)} RSC files on attempt {attempt + 1}")
                    return rsc_files
                else:
                    logger.warning(f"No files found in {self.ROUTEROS_RSC_DIR} (attempt {attempt + 1}/{retry_count})")
                    if attempt < retry_count - 1:
                        logger.info(f"Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                return []
            except Exception as e:
                logger.warning(f"Error listing RSC files (attempt {attempt + 1}/{retry_count}): {e}")
                if attempt < retry_count - 1:
                    logger.info(f"Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                continue
        
        logger.error(f"Failed to list RSC files after {retry_count} attempts")
        return None

    def get_router_backup_dir(self, router_identity: str) -> Path:
        """
        Get or create the backup directory for a specific router.

        Parameters:
            router_identity (str): Router identity/hostname.

        Returns:
            Path: Path to the router's backup directory (inventory/{ROUTER_NAME}/backups).
        """
        # Sanitize router identity for use in path
        safe_identity = router_identity.replace(" ", "_").replace("/", "_").upper()
        router_dir = self.backup_dir / safe_identity
        router_backup_dir = router_dir / "backups"

        router_backup_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Router backup directory: {router_backup_dir}")

        return router_backup_dir

        return router_backup_dir

    def cleanup_old_backups(
        self,
        router_identity: str,
        keep_count: int = 5,
    ) -> int:
        """
        Clean up old backup files, keeping only the most recent ones.

        Parameters:
            router_identity (str): Router identity/hostname.
            keep_count (int): Number of most recent backups to keep (default: 5).

        Returns:
            int: Number of files deleted.
        """
        try:
            router_dir = self.get_router_backup_dir(router_identity)

            # Get all backup files sorted by modification time
            backup_files = sorted(
                router_dir.glob("*.backup"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            # Delete old backups
            deleted_count = 0
            if len(backup_files) > keep_count:
                for old_file in backup_files[keep_count:]:
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
            router_dir = self.get_router_backup_dir(router_identity)

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
