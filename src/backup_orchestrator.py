"""
Backup orchestration for Mikrotik Network Inventory System.

This module handles creating and downloading backups from routers.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table

from backup_manager import BackupManager
from mikrotik_client import MikrotikClient
from models import Router
from sftp_client import SFTPClientManager

console = Console()
logger = logging.getLogger(__name__)


def backup_router_data(
    router: Router,
    ip: str,
    username: str,
    password: str,
    port: int,
    timeout: int,
    sftp_username: Optional[str],
    sftp_password: Optional[str],
    sftp_port: int,
    sftp_timeout: int,
    backup_config: Dict,
) -> Tuple[bool, str]:
    """
    Create and download backup files from a single router.

    Parameters:
        router (Router): Router object.
        ip (str): Router IP address.
        username (str): API username.
        password (str): API password.
        port (int): API port.
        timeout (int): API connection timeout.
        sftp_username (Optional[str]): SFTP username.
        sftp_password (Optional[str]): SFTP password.
        sftp_port (int): SFTP port.
        sftp_timeout (int): SFTP connection timeout.
        backup_config (Dict): Backup configuration.

    Returns:
        Tuple[bool, str]: Success status and message.
    """
    try:
        backup_manager = BackupManager(
            backup_dir=backup_config.get("directory", "inventory"),
            use_sftp=backup_config.get("use_sftp", True),
        )

        router_backup_dir = backup_manager.get_router_backup_dir(router.identity)

        # Connect to router via API for creating backups
        api_client = MikrotikClient(ip, username, password, port, timeout)
        if not api_client.connect():
            return False, f"Failed to connect to {router.identity} via API"

        # Create new backup if configured
        backup_filename = None
        export_filenames = []

        if backup_config.get("create_backup", True):
            # First, connect to SFTP to check if backup already exists
            sftp_client = SFTPClientManager(
                host=ip,
                username=sftp_username or username,
                password=sftp_password or password,
                port=sftp_port,
                timeout=sftp_timeout,
            )

            if not sftp_client.connect():
                return False, f"Failed to connect to {router.identity} via SFTP for pre-check"

            try:
                # Generate the backup name that would be created
                timestamp = time.strftime("%Y%m%d")
                try:
                    identity_resource = api_client.api.get_resource("/system/identity")
                    identity_data = identity_resource.get()
                    system_identity = (
                        identity_data.get("name", router.identity)
                        if identity_data
                        else router.identity
                    )
                except Exception:
                    system_identity = router.identity
                clean_identity = (
                    system_identity.replace(" ", "_").replace("/", "_").upper()
                )
                expected_backup_name = f"{timestamp}_{clean_identity}"
                backup_remote_path = f"/{expected_backup_name}.backup"

                # Check if backup already exists
                if sftp_client.file_exists(backup_remote_path):
                    console.print(
                        f"  [cyan]→[/cyan] Backup already exists: {expected_backup_name}.backup"
                    )
                    backup_filename = expected_backup_name
                else:
                    # Backup doesn't exist, create it
                    console.print(
                        f"  [yellow]→[/yellow] Creating backup on {router.identity}..."
                    )
                    success, backup_filename = api_client.create_backup()
                    if not success:
                        console.print("  [yellow]  ⚠ Backup creation failed[/yellow]")
                        backup_filename = None
            finally:
                sftp_client.disconnect()

        # Create RSC export if configured
        if backup_config.get("export_config", True):
            # Connect via SSH/SFTP to check and export RSC files
            sftp_client = SFTPClientManager(
                host=ip,
                username=sftp_username or username,
                password=sftp_password or password,
                port=sftp_port,
                timeout=sftp_timeout,
            )

            if not sftp_client.connect():
                return (
                    False,
                    f"Failed to connect to {router.identity} via SSH/SFTP for RSC export",
                )

            try:
                # Generate the RSC names that would be created
                timestamp = time.strftime("%Y%m%d")
                try:
                    identity_resource = api_client.api.get_resource("/system/identity")
                    identity_data = identity_resource.get()
                    system_identity = (
                        identity_data.get("name", router.identity)
                        if identity_data
                        else router.identity
                    )
                except Exception:
                    system_identity = router.identity
                clean_identity = (
                    system_identity.replace(" ", "_").replace("/", "_").upper()
                )
                expected_rsc_name = f"{timestamp}_{clean_identity}"
                expected_verbose_name = f"{timestamp}_{clean_identity}_verbose"

                rsc_remote_path = f"/{expected_rsc_name}.rsc"
                verbose_remote_path = f"/{expected_verbose_name}.rsc"

                # Check which RSC files already exist
                normal_exists = sftp_client.file_exists(rsc_remote_path)
                verbose_exists = sftp_client.file_exists(verbose_remote_path)

                if normal_exists and verbose_exists:
                    console.print(
                        "  [cyan]→[/cyan] RSC exports already exist (normal + verbose)"
                    )
                    export_filenames = [expected_rsc_name, expected_verbose_name]
                elif normal_exists and not verbose_exists:
                    console.print(
                        "  [cyan]→[/cyan] Normal RSC export exists, creating verbose version via SSH..."
                    )
                    success, stdout, stderr = sftp_client.execute_command(
                        f"/export verbose file={expected_verbose_name}", timeout=30
                    )
                    if success:
                        console.print("  [green]  ✓ Exported verbose RSC via SSH[/green]")
                        export_filenames = [expected_rsc_name, expected_verbose_name]
                    else:
                        console.print(f"  [yellow]  ⚠ Verbose export failed: {stderr}[/yellow]")
                        export_filenames = [expected_rsc_name]
                    time.sleep(10)
                elif verbose_exists and not normal_exists:
                    console.print(
                        "  [cyan]→[/cyan] Verbose RSC export exists, creating normal version via SSH..."
                    )
                    success, stdout, stderr = sftp_client.execute_command(
                        f"/export file={expected_rsc_name}", timeout=30
                    )
                    if success:
                        console.print("  [green]  ✓ Exported normal RSC via SSH[/green]")
                        export_filenames = [expected_rsc_name, expected_verbose_name]
                    else:
                        console.print(f"  [yellow]  ⚠ Normal export failed: {stderr}[/yellow]")
                        export_filenames = [expected_verbose_name]
                    time.sleep(10)
                else:
                    console.print(
                        f"  [yellow]→[/yellow] Exporting configuration (normal + verbose) via SSH from {router.identity}..."
                    )
                    success, export_filenames = api_client.export_configuration_verbose(
                        ssh_client=sftp_client
                    )
                    if not success or not export_filenames:
                        console.print("  [yellow]  ⚠ Configuration export failed[/yellow]")
                        export_filenames = []
                    else:
                        console.print(
                            f"  [green]  ✓ Exported {len(export_filenames)} RSC file(s) via SSH[/green]"
                        )
            finally:
                sftp_client.disconnect()

        api_client.disconnect()

        # Download backup files via SFTP
        console.print("  [yellow]→[/yellow] Downloading backup files via SFTP...")

        sftp_client = SFTPClientManager(
            host=ip,
            username=sftp_username or username,
            password=sftp_password or password,
            port=sftp_port,
            timeout=sftp_timeout,
        )

        if not sftp_client.connect():
            return False, f"Failed to connect to {router.identity} via SFTP"

        try:
            # Download only the newly created backup file
            if backup_filename:
                backup_files = [backup_filename]
                console.print(f"  [cyan]  Downloading backup: {backup_filename}[/cyan]")
                successful, failed = backup_manager.download_backup_files(
                    sftp_client, router, backup_files, router_backup_dir
                )

                if successful:
                    console.print("  [green]  ✓ Downloaded backup[/green]")
                if failed:
                    console.print("  [yellow]  ✗ Failed to download backup[/yellow]")
            else:
                console.print("  [yellow]  ⊘ No backup file to download[/yellow]")

            # Download RSC files
            if export_filenames:
                for export_filename in export_filenames:
                    # Check if RSC file exists on router before downloading
                    rsc_remote_path = f"/{export_filename}.rsc"
                    if sftp_client.file_exists(rsc_remote_path):
                        rsc_files = [export_filename]
                        console.print(
                            f"  [cyan]  Downloading RSC export: {export_filename}[/cyan]"
                        )
                        successful, failed = backup_manager.download_rsc_files(
                            sftp_client, router, rsc_files, router_backup_dir
                        )

                        if successful:
                            console.print("  [green]  ✓ Downloaded RSC export[/green]")
                        if failed:
                            console.print(
                                "  [yellow]  ✗ Failed to download RSC export[/yellow]"
                            )
                    else:
                        console.print(
                            f"  [yellow]  ⊘ RSC export file not found on router: {export_filename}[/yellow]"
                        )
            else:
                console.print("  [yellow]  ⊘ No RSC file to download[/yellow]")

            # Clean up old backups if configured
            if backup_config.get("cleanup_old", True):
                keep_count = backup_config.get("keep_count", 5)
                deleted = backup_manager.cleanup_old_backups(router.identity, keep_count)
                if deleted > 0:
                    console.print(f"  [blue]  Cleaned up {deleted} old backup(s)[/blue]")

            # Get backup statistics
            stats = backup_manager.get_backup_statistics(router.identity)
            if stats.get("total_files", 0) > 0:
                console.print(
                    f"  [green]✓[/green] {router.identity}: "
                    f"{stats['total_files']} file(s) ({stats['total_size_mb']} MB)"
                )
            else:
                console.print(
                    f"  [yellow]⚠[/yellow] {router.identity}: No backup files found"
                )

            return True, f"Backup completed for {router.identity}"

        finally:
            sftp_client.disconnect()

    except Exception as e:
        logger.error(f"Error backing up {router.identity}: {e}")
        return False, f"Error backing up {router.identity}: {e}"


def backup_all_routers(
    routers: List[Router], config: Dict, router_configs: List[Dict]
) -> None:
    """
    Create and download backups from all routers.

    Parameters:
        routers (List[Router]): List of router objects.
        config (Dict): Main configuration dictionary.
        router_configs (List[Dict]): Router-specific configurations.
    """
    backup_config = config.get("backup", {})
    sftp_config = config.get("sftp", {})
    default_creds = config.get("default_credentials", {})

    if not backup_config.get("enabled", True):
        console.print("[yellow]Backup is disabled in configuration[/yellow]")
        return

    console.print(
        f"\n[bold cyan]Starting backup process for {len(routers)} router(s)...[/bold cyan]\n"
    )

    sftp_enabled = sftp_config.get("enabled", True)
    sftp_port = sftp_config.get("port", 22)
    sftp_timeout = sftp_config.get("timeout", 30)

    backup_results = []

    for router in routers:
        # Find router config for this router
        router_config = None
        for rc in router_configs:
            if rc.get("ip") == router.ip_address:
                router_config = rc
                break

        if not router_config:
            console.print(
                f"[yellow]⚠[/yellow] No configuration found for {router.identity}"
            )
            continue

        # Get credentials
        username = router_config.get("username", default_creds.get("username"))
        password = router_config.get("password", default_creds.get("password"))
        port = router_config.get("port", default_creds.get("port", 8728))
        timeout = router_config.get("timeout", default_creds.get("timeout", 10))

        sftp_username = sftp_config.get("username")
        sftp_password = sftp_config.get("password")

        console.print(
            f"[bold cyan]Backing up: {router.identity} ({router.ip_address})[/bold cyan]"
        )

        success, message = backup_router_data(
            router,
            router.ip_address,
            username,
            password,
            port,
            timeout,
            sftp_username,
            sftp_password,
            sftp_port,
            sftp_timeout,
            backup_config,
        )

        backup_results.append((router.identity, success, message))

    # Display backup results summary
    if backup_results:
        console.print(
            "\n[bold cyan]═══════════════════════════════════════════════════════════════════════[/bold cyan]"
        )
        console.print(
            "[bold cyan]                     BACKUP SUMMARY                                  [/bold cyan]"
        )
        console.print(
            "[bold cyan]═══════════════════════════════════════════════════════════════════════[/bold cyan]\n"
        )

        results_table = Table(show_header=True, header_style="bold magenta")
        results_table.add_column("Router", style="cyan")
        results_table.add_column("Status", justify="center")
        results_table.add_column("Message", style="white")

        for router_name, success, message in backup_results:
            status = "[green]✓ SUCCESS[/green]" if success else "[red]✗ FAILED[/red]"
            results_table.add_row(router_name, status, message)

        console.print(results_table)
        console.print()
