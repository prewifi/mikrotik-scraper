"""
Mikrotik Network Inventory System.

Main orchestrator for collecting, analyzing, and saving network inventory data
from Mikrotik routers via RouterOS API.
"""

import argparse
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import yaml
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table

from analyzer import NetworkAnalyzer
from backup_manager import BackupManager
from inventory import InventoryManager
from mikrotik_client import MikrotikClient
from models import Router, IPServiceConfig, UserConfig, UserGroupConfig, SyslogConfig, LoggingTopicConfig, SNMPConfig, SNMPCommunityConfig
from sftp_client import SFTPClientManager

console = Console()
logger = logging.getLogger(__name__)



def setup_logging(config: Dict) -> None:
    """
    Setup logging configuration.

    Parameters:
        config (Dict): Logging configuration from config file.
    """
    log_config = config.get("logging", {})
    level = getattr(logging, log_config.get("level", "INFO").upper())
    log_file = log_config.get("file")
    use_console = log_config.get("console", True)

    handlers = []

    # File handler (if log file is specified)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        handlers.append(file_handler)

    # Console handler with Rich
    if use_console:
        console_handler = RichHandler(console=console, rich_tracebacks=True)
        handlers.append(console_handler)

    logging.basicConfig(
        level=level,
        handlers=handlers,
        format="%(message)s",
    )


def load_config(config_path: str) -> Dict:
    """
    Load configuration from YAML file.

    Parameters:
        config_path (str): Path to configuration file.

    Returns:
        Dict: Configuration dictionary.
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        console.print(f"[red]Error: Configuration file not found: {config_path}[/red]")
        console.print(
            "\n[yellow]Please create a config.yaml file based on config.yaml.example[/yellow]"
        )
        sys.exit(1)
    except yaml.YAMLError as e:
        console.print(f"[red]Error parsing configuration file: {e}[/red]")
        sys.exit(1)


def generate_execution_report(
    operation_name: str,
    successful_routers: List[Dict],
    failed_routers: List[Dict],
    output_dir: str = "results",
) -> str:
    """
    Generate an execution report file with successful and failed routers.

    Parameters:
        operation_name (str): Name of the operation (e.g., 'backup', 'syslog', 'users').
        successful_routers (List[Dict]): List of dicts with 'ip' and 'identity' for successful routers.
        failed_routers (List[Dict]): List of dicts with 'ip', 'identity', and 'error' for failed routers.
        output_dir (str): Directory to save the report (default: 'results').

    Returns:
        str: Path to the generated report file.
    """
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"{operation_name}_report_{timestamp}.txt"
    
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    report_path = output_path / report_filename
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"{'='*60}\n")
        f.write(f"EXECUTION REPORT: {operation_name.upper()}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*60}\n\n")
        
        # Summary
        total = len(successful_routers) + len(failed_routers)
        f.write(f"SUMMARY\n")
        f.write(f"-" * 30 + "\n")
        f.write(f"Total Routers:   {total}\n")
        f.write(f"Successful:      {len(successful_routers)}\n")
        f.write(f"Failed:          {len(failed_routers)}\n")
        f.write(f"\n")
        
        # Successful routers
        f.write(f"SUCCESSFUL ROUTERS ({len(successful_routers)})\n")
        f.write(f"-" * 30 + "\n")
        if successful_routers:
            for router in successful_routers:
                identity = router.get("identity", "Unknown")
                ip = router.get("ip", "Unknown")
                f.write(f"  ✓ {identity} ({ip})\n")
        else:
            f.write("  (none)\n")
        f.write(f"\n")
        
        # Failed routers
        f.write(f"FAILED ROUTERS ({len(failed_routers)})\n")
        f.write(f"-" * 30 + "\n")
        if failed_routers:
            for router in failed_routers:
                identity = router.get("identity", "Unknown")
                ip = router.get("ip", "Unknown")
                error = router.get("error", "Unknown error")
                f.write(f"  ✗ {identity} ({ip})\n")
                f.write(f"    Error: {error}\n")
        else:
            f.write("  (none)\n")
        
        f.write(f"\n{'='*60}\n")
        f.write(f"END OF REPORT\n")
    
    logger.info(f"Execution report saved to: {report_path}")
    console.print(f"[cyan]Report saved to: {report_path}[/cyan]")
    
    return str(report_path)



def collect_router_data(
    ip: str,
    username: str,
    password: str,
    port: int,
    timeout: int,
    collection_options: Optional[Dict] = None,
) -> Tuple[Router | None, str | None]:
    """
    Collect data from a single router.

    Parameters:
        ip (str): Router IP address.
        username (str): RouterOS username.
        password (str): RouterOS password.
        port (int): API port.
        timeout (int): Connection timeout.
        collection_options (Optional[Dict]): Options for data collection.

    Returns:
        Tuple[Router | None, str | None]: Router object and error message if any.
    """
    client = MikrotikClient(ip, username, password, port, timeout)
    router, error = client.collect_all_data(collection_options)

    if error:
        return None, error

    return router, None


def collect_all_routers(config: Dict) -> List[Router]:
    """
    Collect data from all routers in configuration.

    Parameters:
        config (Dict): Configuration dictionary.

    Returns:
        List[Router]: List of router objects with collected data.
    """
    routers = []
    default_creds = config.get("default_credentials", {})
    router_configs = config.get("routers", [])
    collection_config = config.get("collection", {})

    parallel = collection_config.get("parallel", False)
    max_workers = collection_config.get("max_workers", 5)

    # Get collection options
    collection_options = collection_config.get("collect", {})

    console.print(
        f"\n[bold cyan]Starting data collection from {len(router_configs)} routers...[/bold cyan]\n"
    )

    if parallel:
        # Parallel collection
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Collecting router data...", total=len(router_configs))

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for router_config in router_configs:
                    ip = router_config.get("ip")
                    username = router_config.get("username", default_creds.get("username"))
                    password = router_config.get("password", default_creds.get("password"))
                    port = router_config.get("port", default_creds.get("port", 8728))
                    timeout = router_config.get("timeout", default_creds.get("timeout", 10))

                    future = executor.submit(
                        collect_router_data,
                        ip,
                        username,
                        password,
                        port,
                        timeout,
                        collection_options,
                    )
                    futures[future] = ip

                for future in as_completed(futures):
                    ip = futures[future]
                    try:
                        router, error = future.result()
                        if router:
                            routers.append(router)
                            console.print(f"[green]✓[/green] {router.identity} ({ip})")
                        else:
                            console.print(f"[red]✗[/red] {ip}: {error}")
                    except Exception as e:
                        console.print(f"[red]✗[/red] {ip}: Unexpected error: {e}")

                    progress.update(task, advance=1)
    else:
        # Sequential collection
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("Collecting router data...", total=len(router_configs))

            for router_config in router_configs:
                ip = router_config.get("ip")
                username = router_config.get("username", default_creds.get("username"))
                password = router_config.get("password", default_creds.get("password"))
                port = router_config.get("port", default_creds.get("port", 8728))
                timeout = router_config.get("timeout", default_creds.get("timeout", 10))

                progress.update(task, description=f"Collecting from {ip}...")

                router, error = collect_router_data(
                    ip, username, password, port, timeout, collection_options
                )

                if router:
                    routers.append(router)
                    console.print(f"[green]✓[/green] {router.identity} ({ip})")
                else:
                    console.print(f"[red]✗[/red] {ip}: {error}")

                progress.update(task, advance=1)

    console.print(
        f"\n[bold green]Successfully collected data from {len(routers)}/{len(router_configs)} routers[/bold green]\n"
    )
    return routers


def display_summary(inventory) -> None:
    """
    Display a summary of the collected inventory.

    Parameters:
        inventory: NetworkInventory object.
    """
    console.print(
        "\n[bold cyan]═══════════════════════════════════════════════════════════════════════[/bold cyan]"
    )
    console.print(
        "[bold cyan]                    INVENTORY SUMMARY                                  [/bold cyan]"
    )
    console.print(
        "[bold cyan]═══════════════════════════════════════════════════════════════════════[/bold cyan]\n"
    )

    # Statistics table
    stats_table = Table(show_header=True, header_style="bold magenta")
    stats_table.add_column("Metric", style="cyan", width=40)
    stats_table.add_column("Value", justify="right", style="yellow")

    for key, value in inventory.stats.items():
        stats_table.add_row(key.replace("_", " ").title(), str(value))

    console.print(stats_table)

    # Routers table
    if inventory.routers:
        console.print("\n[bold magenta]Routers:[/bold magenta]\n")
        router_table = Table(show_header=True, header_style="bold magenta")
        router_table.add_column("Status", width=6)
        router_table.add_column("Identity", style="cyan")
        router_table.add_column("IP Address", style="yellow")
        router_table.add_column("Version", style="green")
        router_table.add_column("Interfaces", justify="right")
        router_table.add_column("Neighbors", justify="right")

        for router in inventory.routers:
            status = "✓" if router.connection_successful else "✗"
            version = router.system_resource.version if router.system_resource else "N/A"
            router_table.add_row(
                status,
                router.identity,
                router.ip_address,
                version,
                str(len(router.interfaces)),
                str(len(router.neighbors)),
            )

        console.print(router_table)

    # Anomalies summary
    if inventory.anomalies:
        console.print("\n[bold red]Anomalies Detected:[/bold red]\n")
        critical = sum(1 for a in inventory.anomalies if a.severity == "critical")
        warning = sum(1 for a in inventory.anomalies if a.severity == "warning")
        info = sum(1 for a in inventory.anomalies if a.severity == "info")

        console.print(f"  [red]Critical: {critical}[/red]")
        console.print(f"  [yellow]Warning: {warning}[/yellow]")
        console.print(f"  [blue]Info: {info}[/blue]")


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
    logger = logging.getLogger(__name__)

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
        export_filename = None
        
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
                    system_identity = identity_data.get("name", router.identity) if identity_data else router.identity
                except Exception:
                    system_identity = router.identity
                clean_identity = system_identity.replace(" ", "_").replace("/", "_").upper()
                expected_backup_name = f"{timestamp}_{clean_identity}"
                backup_remote_path = f"/{expected_backup_name}.backup"

                # Check if backup already exists
                if sftp_client.file_exists(backup_remote_path):
                    console.print(f"  [cyan]→[/cyan] Backup already exists: {expected_backup_name}.backup")
                    backup_filename = expected_backup_name
                else:
                    # Backup doesn't exist, create it
                    console.print(f"  [yellow]→[/yellow] Creating backup on {router.identity}...")
                    success, backup_filename = api_client.create_backup()
                    if not success:
                        console.print(f"  [yellow]  ⚠ Backup creation failed[/yellow]")
                        backup_filename = None
            finally:
                sftp_client.disconnect()

        # Create RSC export if configured
        export_filenames = []
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
                return False, f"Failed to connect to {router.identity} via SSH/SFTP for RSC export"

            try:
                # Generate the RSC names that would be created
                timestamp = time.strftime("%Y%m%d")
                try:
                    identity_resource = api_client.api.get_resource("/system/identity")
                    identity_data = identity_resource.get()
                    system_identity = identity_data.get("name", router.identity) if identity_data else router.identity
                except Exception:
                    system_identity = router.identity
                clean_identity = system_identity.replace(" ", "_").replace("/", "_").upper()
                expected_rsc_name = f"{timestamp}_{clean_identity}"
                expected_verbose_name = f"{timestamp}_{clean_identity}_verbose"
                
                rsc_remote_path = f"/{expected_rsc_name}.rsc"
                verbose_remote_path = f"/{expected_verbose_name}.rsc"

                # Check which RSC files already exist
                normal_exists = sftp_client.file_exists(rsc_remote_path)
                verbose_exists = sftp_client.file_exists(verbose_remote_path)

                if normal_exists and verbose_exists:
                    console.print(f"  [cyan]→[/cyan] RSC exports already exist (normal + verbose)")
                    export_filenames = [expected_rsc_name, expected_verbose_name]
                elif normal_exists and not verbose_exists:
                    console.print(f"  [cyan]→[/cyan] Normal RSC export exists, creating verbose version via SSH...")

                    success, stdout, stderr = sftp_client.execute_command(f"/export verbose file={expected_verbose_name}", timeout=30)
                    if success:
                        console.print(f"  [green]  ✓ Exported verbose RSC via SSH[/green]")
                        export_filenames = [expected_rsc_name, expected_verbose_name]
                    else:
                        console.print(f"  [yellow]  ⚠ Verbose export failed: {stderr}[/yellow]")
                        export_filenames = [expected_rsc_name]
                    time.sleep(10)  # Wait for file to be written
                elif verbose_exists and not normal_exists:
                    console.print(f"  [cyan]→[/cyan] Verbose RSC export exists, creating normal version via SSH...")
                    success, stdout, stderr = sftp_client.execute_command(f"/export file={expected_rsc_name}", timeout=30)
                    if success:
                        console.print(f"  [green]  ✓ Exported normal RSC via SSH[/green]")
                        export_filenames = [expected_rsc_name, expected_verbose_name]
                    else:
                        console.print(f"  [yellow]  ⚠ Normal export failed: {stderr}[/yellow]")
                        export_filenames = [expected_verbose_name]
                    time.sleep(10)  # Wait for file to be written
                else:
                    console.print(f"  [yellow]→[/yellow] Exporting configuration (normal + verbose) via SSH from {router.identity}...")
                    success, export_filenames = api_client.export_configuration_verbose(ssh_client=sftp_client)
                    if not success or not export_filenames:
                        console.print(f"  [yellow]  ⚠ Configuration export failed[/yellow]")
                        export_filenames = []
                    else:
                        console.print(f"  [green]  ✓ Exported {len(export_filenames)} RSC file(s) via SSH[/green]")
            finally:
                sftp_client.disconnect()

        api_client.disconnect()

        # Download backup files via SFTP
        console.print(f"  [yellow]→[/yellow] Downloading backup files via SFTP...")

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
                console.print(
                    f"  [cyan]  Downloading backup: {backup_filename}[/cyan]"
                )
                successful, failed = backup_manager.download_backup_files(
                    sftp_client, router, backup_files, router_backup_dir
                )

                if successful:
                    console.print(
                        f"  [green]  ✓ Downloaded backup[/green]"
                    )
                if failed:
                    console.print(
                        f"  [yellow]  ✗ Failed to download backup[/yellow]"
                    )
            else:
                console.print(f"  [yellow]  ⊘ No backup file to download[/yellow]")

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
                            console.print(
                                f"  [green]  ✓ Downloaded RSC export[/green]"
                            )
                        if failed:
                            console.print(
                                f"  [yellow]  ✗ Failed to download RSC export[/yellow]"
                            )
                    else:
                        console.print(f"  [yellow]  ⊘ RSC export file not found on router: {export_filename}[/yellow]")
            else:
                console.print(f"  [yellow]  ⊘ No RSC file to download[/yellow]")

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
            console.print(f"[yellow]⚠[/yellow] No configuration found for {router.identity}")
            continue

        # Get credentials
        username = router_config.get("username", default_creds.get("username"))
        password = router_config.get("password", default_creds.get("password"))
        port = router_config.get("port", default_creds.get("port", 8728))
        timeout = router_config.get("timeout", default_creds.get("timeout", 10))

        sftp_username = sftp_config.get("username")
        sftp_password = sftp_config.get("password")

        console.print(f"[bold cyan]Backing up: {router.identity} ({router.ip_address})[/bold cyan]")

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


def configure_ip_services_all_routers(
    config: Dict, router_configs: List[Dict]
) -> Tuple[int, int]:
    """
    Configure IP services on all routers.

    Parameters:
        config (Dict): Main configuration dictionary.
        router_configs (List[Dict]): Router-specific configurations.

    Returns:
        Tuple[int, int]: (successful_count, failed_count).
    """
    ip_services_config = config.get("ip_services", {})
    
    if not ip_services_config.get("enabled", False):
        console.print("[yellow]IP services configuration is disabled[/yellow]")
        return 0, 0

    services_to_configure = ip_services_config.get("services", {})
    if not services_to_configure:
        console.print("[yellow]No IP services configured in config file[/yellow]")
        return 0, 0

    rollback_timeout = ip_services_config.get("rollback_timeout", 300)
    create_rollback = ip_services_config.get("rollback_on_failure", True)
    
    default_creds = config.get("default_credentials", {})
    
    console.print(
        f"\n[bold cyan]Configuring IP services on {len(router_configs)} router(s)...[/bold cyan]\n"
    )
    console.print(
        f"[cyan]Services to configure: {', '.join(services_to_configure.keys())}[/cyan]\n"
    )
    
    if create_rollback:
        console.print(
            f"[yellow]⚠ Rollback protection enabled (timeout: {rollback_timeout}s)[/yellow]\n"
        )

    successful = 0
    failed = 0

    for router_config in router_configs:
        ip = router_config.get("ip")
        username = router_config.get("username", default_creds.get("username"))
        password = router_config.get("password", default_creds.get("password"))
        port = router_config.get("port", default_creds.get("port", 8728))
        timeout = router_config.get("timeout", default_creds.get("timeout", 10))

        console.print(f"[bold cyan]Configuring: {ip}[/bold cyan]")

        # Connect to router
        client = MikrotikClient(ip, username, password, port, timeout)
        
        if not client.connect():
            console.print(f"  [red]✗ Failed to connect[/red]\n")
            failed += 1
            continue

        try:
            # Get router identity for better logging
            identity = client.get_system_identity()
            console.print(f"  Router: {identity}")

            # Build service configuration list
            service_configs = []
            for service_name, service_config in services_to_configure.items():
                addresses = service_config.get("addresses", "")
                if addresses:
                    service_configs.append(
                        IPServiceConfig(
                            service_name=service_name,
                            addresses=addresses
                        )
                    )

            if not service_configs:
                console.print(f"  [yellow]⚠ No valid service configurations[/yellow]\n")
                client.disconnect()
                continue

            # Apply configuration with rollback
            success, scheduler_name, error = client.set_ip_service_addresses(
                service_configs=service_configs,
                create_rollback=create_rollback,
                rollback_timeout=rollback_timeout,
            )

            if success:
                console.print(f"  [green]✓ Configuration applied successfully[/green]")
                successful += 1
            else:
                console.print(f"  [red]✗ Configuration failed: {error}[/red]")
                if scheduler_name:
                    console.print(
                        f"  [yellow]  → Rollback scheduler active: {scheduler_name}[/yellow]"
                    )
                failed += 1

        except Exception as e:
            console.print(f"  [red]✗ Error: {e}[/red]")
            failed += 1
        finally:
            client.disconnect()
            console.print()

    # Summary
    console.print(
        "\n[bold cyan]═══════════════════════════════════════════════════════════════════════[/bold cyan]"
    )
    console.print(
        "[bold cyan]              IP SERVICES CONFIGURATION SUMMARY                       [/bold cyan]"
    )
    console.print(
        "[bold cyan]═══════════════════════════════════════════════════════════════════════[/bold cyan]\n"
    )
    
    console.print(f"[green]Successful: {successful}[/green]")
    console.print(f"[red]Failed: {failed}[/red]")
    console.print(f"[cyan]Total: {successful + failed}[/cyan]\n")

    return successful, failed


def configure_users_and_groups(config: Dict) -> Tuple[int, int]:
    """
    Configure users and groups on all routers.

    Parameters:
        config (Dict): Configuration dictionary.

    Returns:
        Tuple[int, int]: Number of successful and failed configurations.
    """
    user_mgmt_config = config.get("user_management", {})
    if not user_mgmt_config.get("enabled", False):
        logger.info("User management configuration disabled")
        return 0, 0

    console.print("\n[bold cyan]Starting User and Group Configuration...[/bold cyan]")

    successful = 0
    failed = 0

    routers_config = config.get("routers", [])
    total_routers = len(routers_config)

    # Prepare configs
    groups_config = []
    for g in user_mgmt_config.get("groups", []):
        groups_config.append(UserGroupConfig(**g))

    users_config = []
    for u in user_mgmt_config.get("users", []):
        users_config.append(UserConfig(**u))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Configuring users and groups...", total=total_routers
        )

        for router_conf in routers_config:
            host = router_conf.get("ip") or router_conf.get("host")
            username = router_conf.get("username", config.get("default_credentials", {}).get("username"))
            password = router_conf.get("password", config.get("default_credentials", {}).get("password"))
            port = router_conf.get("port", 8728)

            progress.update(task, description=f"[cyan]Configuring {host}...")

            client = MikrotikClient(host, username, password, port)

            try:
                if client.connect():
                    logger.info(f"Connected to {host} for user management")

                    # Configure Groups
                    for group_conf in groups_config:
                        client.ensure_user_group(group_conf)

                    # Configure Users
                    for user_conf in users_config:
                        client.ensure_user(user_conf)

                    successful += 1
                    client.disconnect()
                else:
                    logger.error(f"Failed to connect to {host}")
                    failed += 1
            except Exception as e:
                logger.error(f"Error configuring users on {host}: {e}")
                failed += 1

            progress.advance(task)

    console.print(f"\n[green]Successful: {successful}[/green]")
    console.print(f"[red]Failed: {failed}[/red]")

    return successful, failed


def configure_syslog_all_routers(config: Dict) -> Tuple[int, int]:
    """
    Configure syslog on all routers.

    Parameters:
        config (Dict): Configuration dictionary.

    Returns:
        Tuple[int, int]: Number of successful and failed configurations.
    """
    syslog_config = config.get("syslog", {})
    if not syslog_config.get("enabled", False):
        logger.info("Syslog configuration disabled")
        return 0, 0

    console.print("\n[bold cyan]Starting Syslog Configuration...[/bold cyan]")

    successful = 0
    failed = 0

    routers_config = config.get("routers", [])
    total_routers = len(routers_config)

    # Prepare syslog config
    try:
        syslog_settings = SyslogConfig(
            remote_server=syslog_config.get("remote_server"),
            remote_port=syslog_config.get("remote_port", 514),
            bsd_syslog=syslog_config.get("bsd_syslog", True),
            syslog_facility=syslog_config.get("syslog_facility", "local0"),
            syslog_severity=syslog_config.get("syslog_severity", "auto"),
        )
    except Exception as e:
        logger.error(f"Invalid syslog configuration: {e}")
        return 0, 1

    # Prepare topic configs
    topics_config = []
    for t in syslog_config.get("topics", []):
        topics_config.append(LoggingTopicConfig(**t))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Configuring syslog...", total=total_routers
        )

        for router_conf in routers_config:
            host = router_conf.get("ip") or router_conf.get("host")
            username = router_conf.get("username", config.get("default_credentials", {}).get("username"))
            password = router_conf.get("password", config.get("default_credentials", {}).get("password"))
            port = router_conf.get("port", 8728)

            progress.update(task, description=f"[cyan]Configuring syslog on {host}...")

            client = MikrotikClient(host, username, password, port)

            try:
                if client.connect():
                    logger.info(f"Connected to {host} for syslog configuration")

                    # Configure syslog action (src_address is the router's IP)
                    client.configure_syslog(syslog_settings, src_address=host)

                    # Configure logging topics
                    if topics_config:
                        client.configure_logging_topics(topics_config)

                    successful += 1
                    client.disconnect()
                else:
                    logger.error(f"Failed to connect to {host}")
                    failed += 1
            except Exception as e:
                logger.error(f"Error configuring syslog on {host}: {e}")
                failed += 1

            progress.advance(task)

    console.print(f"\n[green]Successful: {successful}[/green]")
    console.print(f"[red]Failed: {failed}[/red]")

    return successful, failed


def configure_snmp_all_routers(config: Dict) -> Tuple[int, int]:
    """
    Configure SNMP on all routers defined in config.

    Parameters:
        config (Dict): Configuration dictionary.

    Returns:
        Tuple[int, int]: (successful, failed) counts.
    """
    snmp_config_dict = config.get("snmp", {})
    if not snmp_config_dict:
        console.print("[yellow]No SNMP configuration found in config[/yellow]")
        return 0, 0

    # Parse communities
    communities = []
    for comm_dict in snmp_config_dict.get("communities", []):
        communities.append(SNMPCommunityConfig(**comm_dict))

    # Create SNMPConfig
    snmp_settings = SNMPConfig(
        enabled=snmp_config_dict.get("enabled", True),
        contact=snmp_config_dict.get("contact"),
        location=snmp_config_dict.get("location"),
        trap_community=snmp_config_dict.get("trap_community", "public"),
        trap_version=snmp_config_dict.get("trap_version", 2),
        communities=communities,
    )

    routers_config = config.get("routers", [])
    if not routers_config:
        console.print("[yellow]No routers defined in configuration[/yellow]")
        return 0, 0

    total_routers = len(routers_config)
    successful = 0
    failed = 0

    console.print(f"\n[bold cyan]Configuring SNMP on {total_routers} router(s)...[/bold cyan]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Configuring SNMP...", total=total_routers
        )

        for router_conf in routers_config:
            host = router_conf.get("ip") or router_conf.get("host")
            username = router_conf.get("username", config.get("default_credentials", {}).get("username"))
            password = router_conf.get("password", config.get("default_credentials", {}).get("password"))
            port = router_conf.get("port", 8728)

            progress.update(task, description=f"[cyan]Configuring SNMP on {host}...")

            client = MikrotikClient(host, username, password, port)

            try:
                if client.connect():
                    logger.info(f"Connected to {host} for SNMP configuration")

                    # Get system identity for location
                    system_identity = client.get_identity()

                    # Configure SNMP (this also configures communities)
                    client.configure_snmp(snmp_settings, system_identity=system_identity)

                    successful += 1
                    client.disconnect()
                else:
                    logger.error(f"Failed to connect to {host}")
                    failed += 1
            except Exception as e:
                logger.error(f"Error configuring SNMP on {host}: {e}")
                failed += 1

            progress.advance(task)

    console.print(f"\n[green]Successful: {successful}[/green]")
    console.print(f"[red]Failed: {failed}[/red]")

    return successful, failed


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="Mikrotik Network Inventory System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    parser.add_argument("-o", "--output-dir", help="Override output directory from config")
    parser.add_argument("--json-only", action="store_true", help="Save only JSON format")
    parser.add_argument("--yaml-only", action="store_true", help="Save only YAML format")
    parser.add_argument(
        "--backup", action="store_true", help="Create and download backups after inventory"
    )
    parser.add_argument(
        "--backup-only",
        action="store_true",
        help="Only perform backup operations (skip inventory)",
    )
    parser.add_argument(
        "--configure-services",
        action="store_true",
        help="Configure IP services on all routers (can be combined with other options)",
    )
    parser.add_argument(
        "--configure-services-only",
        action="store_true",
        help="Only configure IP services (skip inventory and backup)",
    )
    parser.add_argument(
        "--configure-users",
        action="store_true",
        help="Configure users and groups on all routers",
    )
    parser.add_argument(
        "--configure-users-only",
        action="store_true",
        help="Only configure users and groups (skip inventory and backup)",
    )
    parser.add_argument(
        "--configure-syslog",
        action="store_true",
        help="Configure syslog on all routers",
    )
    parser.add_argument(
        "--configure-syslog-only",
        action="store_true",
        help="Only configure syslog (skip inventory and backup)",
    )
    parser.add_argument(
        "--configure-snmp",
        action="store_true",
        help="Configure SNMP on all routers",
    )
    parser.add_argument(
        "--configure-snmp-only",
        action="store_true",
        help="Only configure SNMP (skip inventory and backup)",
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Setup logging
    setup_logging(config)


    try:
        # Display banner
        console.print(
            "\n[bold blue]╔═══════════════════════════════════════════════════════════════════╗[/bold blue]"
        )
        console.print(
            "[bold blue]║      MIKROTIK NETWORK INVENTORY SYSTEM                        ║[/bold blue]"
        )
        console.print(
            "[bold blue]╚═══════════════════════════════════════════════════════════════════╝[/bold blue]\n"
        )

        router_configs = config.get("routers", [])

        if args.configure_services_only:
            # Configure IP services only mode
            console.print(
                "[bold cyan]IP Services configuration only mode...[/bold cyan]"
            )
            configure_ip_services_all_routers(config, router_configs)

        elif args.configure_users_only:
            # Configure users only mode
            console.print(
                "[bold cyan]User/Group configuration only mode...[/bold cyan]"
            )
            configure_users_and_groups(config)

        elif args.configure_syslog_only:
            # Configure syslog only mode
            console.print(
                "[bold cyan]Syslog configuration only mode...[/bold cyan]"
            )
            configure_syslog_all_routers(config)

        elif args.configure_snmp_only:
            # Configure SNMP only mode
            console.print(
                "[bold cyan]SNMP configuration only mode...[/bold cyan]"
            )
            configure_snmp_all_routers(config)

        elif args.backup_only:
            # Backup only mode - connect to routers just for backup, skip full data collection
            console.print("[bold cyan]Backup-only mode...[/bold cyan]")
            
            router_configs = config.get("routers", [])
            backup_config = config.get("backup", {})
            sftp_config = config.get("sftp", {})
            default_creds = config.get("default_credentials", {})
            
            if not backup_config.get("enabled", True):
                console.print("[yellow]Backup is disabled in configuration[/yellow]")
                sys.exit(0)
            
            console.print(f"\n[bold cyan]Starting backup process for {len(router_configs)} router(s)...[/bold cyan]\n")
            
            sftp_enabled = sftp_config.get("enabled", True)
            sftp_port = sftp_config.get("port", 22)
            sftp_timeout = sftp_config.get("timeout", 30)
            
            backup_manager = BackupManager(
                backup_dir=backup_config.get("directory", "inventory"),
                use_sftp=sftp_enabled,
            )
            
            # Track results for report
            successful_routers = []
            failed_routers = []
            
            for rc in router_configs:
                host = rc.get("ip") or rc.get("host")
                username = rc.get("username", default_creds.get("username"))
                password = rc.get("password", default_creds.get("password"))
                port = rc.get("port", default_creds.get("port", 8728))
                
                sftp_username = sftp_config.get("username", username)
                sftp_password = sftp_config.get("password", password)
                
                console.print(f"[cyan]Backing up {host}...[/cyan]")
                
                # Connect to get identity only
                client = MikrotikClient(host, username, password, port)
                try:
                    if client.connect():
                        # Get identity for directory naming
                        identity = client.get_identity() or host
                        
                        # Create minimal Router object for backup_manager
                        from models import Router
                        minimal_router = Router(
                            ip_address=host,
                            identity=identity,
                            connection_successful=True,
                        )
                        
                        # Track created files for download
                        created_backup_file = None
                        created_rsc_file = None
                        
                        # Perform backup
                        if backup_config.get("create_backup", True):
                            success, backup_name = backup_manager.create_backup(
                                client.api, minimal_router
                            )
                            if success:
                                created_backup_file = f"{backup_name}.backup"
                                logger.info(f"Backup created: {created_backup_file}")
                        
                        # Export configuration via SSH (API doesn't support export)
                        created_rsc_verbose_file = None
                        if backup_config.get("export_config", True):
                            timestamp = time.strftime("%Y%m%d")
                            clean_identity = identity.replace(" ", "_").replace("/", "_").upper()
                            export_name = f"{timestamp}_{clean_identity}"
                            export_name_verbose = f"{timestamp}_{clean_identity}_verbose"
                            
                            # Use SSH to execute export commands
                            export_sftp = SFTPClientManager(
                                host, sftp_username, sftp_password, sftp_port, sftp_timeout
                            )
                            if export_sftp.connect():
                                # Normal export
                                export_cmd = f'/export file="{export_name}"'
                                success, stdout, stderr = export_sftp.execute_command(export_cmd)
                                
                                if success:
                                    created_rsc_file = f"{export_name}.rsc"
                                    logger.info(f"Export created via SSH: {created_rsc_file}")
                                else:
                                    logger.error(f"Export failed: {stderr}")
                                
                                # Verbose export
                                export_cmd_verbose = f'/export verbose file="{export_name_verbose}"'
                                success_v, stdout_v, stderr_v = export_sftp.execute_command(export_cmd_verbose)
                                
                                if success_v:
                                    created_rsc_verbose_file = f"{export_name_verbose}.rsc"
                                    logger.info(f"Verbose export created via SSH: {created_rsc_verbose_file}")
                                else:
                                    logger.error(f"Verbose export failed: {stderr_v}")
                                
                                export_sftp.disconnect()
                                
                                # Wait for files to be written
                                import time as time_module
                                time_module.sleep(5)
                            else:
                                logger.error(f"Could not connect via SSH to export config on {host}")
                        
                        # Download only the newly created files via SFTP
                        if sftp_enabled and (created_backup_file or created_rsc_file or created_rsc_verbose_file):
                            sftp_client = SFTPClientManager(
                                host, sftp_username, sftp_password,
                                sftp_port, sftp_timeout
                            )
                            if sftp_client.connect():
                                local_dir = backup_manager.get_router_backup_dir(identity)
                                
                                # Download only the specific backup file just created
                                if created_backup_file:
                                    backup_manager.download_backup_files(
                                        sftp_client, minimal_router, [created_backup_file], local_dir
                                    )
                                
                                # Download only the specific RSC files just created
                                rsc_files_to_download = []
                                if created_rsc_file:
                                    rsc_files_to_download.append(created_rsc_file)
                                if created_rsc_verbose_file:
                                    rsc_files_to_download.append(created_rsc_verbose_file)
                                
                                if rsc_files_to_download:
                                    backup_manager.download_rsc_files(
                                        sftp_client, minimal_router, rsc_files_to_download, local_dir
                                    )
                                
                                sftp_client.disconnect()
                        
                        successful_routers.append({"ip": host, "identity": identity})
                        client.disconnect()
                    else:
                        logger.error(f"Failed to connect to {host}")
                        failed_routers.append({"ip": host, "identity": host, "error": "Failed to connect"})
                except Exception as e:
                    logger.error(f"Error backing up {host}: {e}")
                    failed_routers.append({"ip": host, "identity": host, "error": str(e)})
            
            # Generate execution report
            generate_execution_report(
                operation_name="backup",
                successful_routers=successful_routers,
                failed_routers=failed_routers,
                output_dir=backup_config.get("directory", "results"),
            )
            
            console.print(f"\n[green]Successful: {len(successful_routers)}[/green]")
            console.print(f"[red]Failed: {len(failed_routers)}[/red]")

        else:
            # Normal mode - collect inventory
            routers = collect_all_routers(config)

            if not routers:
                console.print("[red]No routers were successfully queried. Exiting.[/red]")
                sys.exit(1)

            # Analyze network topology (if enabled)
            analysis_config = config.get("analysis", {})
            if analysis_config.get("enabled", True):
                console.print("[bold cyan]Analyzing network topology...[/bold cyan]")
                analyzer = NetworkAnalyzer(routers, analysis_config)
                inventory = analyzer.analyze()
            else:
                # Skip analysis, just create basic inventory
                from models import NetworkInventory

                inventory = NetworkInventory(routers=routers, links=[], anomalies=[])
                console.print("[yellow]Analysis disabled - skipping topology analysis[/yellow]")

            # Display summary
            display_summary(inventory)

            # Save inventory
            output_dir = args.output_dir or config.get("output", {}).get("directory", "output")
            inventory_manager = InventoryManager(output_dir)

            console.print(f"\n[bold cyan]Saving inventory to: {output_dir}[/bold cyan]\n")

            formats = config.get("output", {}).get("formats", ["json", "yaml", "summary"])

            if args.json_only:
                formats = ["json"]
            elif args.yaml_only:
                formats = ["yaml"]

            # Save individual files for each router
            if "json" in formats:
                console.print("[cyan]Saving JSON files per router...[/cyan]")
                for router in routers:
                    json_path = inventory_manager.save_router_json(router)
                    console.print(f"[green]✓[/green] JSON saved: {json_path}")

            if "yaml" in formats:
                console.print("[cyan]Saving YAML files per router...[/cyan]")
                for router in routers:
                    yaml_path = inventory_manager.save_router_yaml(router)
                    console.print(f"[green]✓[/green] YAML saved: {yaml_path}")

            if "summary" in formats:
                summary_path = inventory_manager.save_summary(inventory)
                console.print(f"[green]✓[/green] Summary saved: {summary_path}")

            console.print("\n[bold green]✓ Inventory collection completed successfully![/bold green]\n")

            # Configure IP services if enabled or requested
            ip_services_config = config.get("ip_services", {})
            should_configure = (
                args.configure_services  # Explicitly requested via CLI
                or (  # Or enabled in config and apply_on_connect is true
                    ip_services_config.get("enabled", False)
                    and ip_services_config.get("apply_on_connect", False)
                )
            )

            if should_configure:
                configure_ip_services_all_routers(config, router_configs)

            # Configure Users if requested or enabled
            user_mgmt_config = config.get("user_management", {})
            should_configure_users = (
                args.configure_users
                or user_mgmt_config.get("enabled", False)
            )

            if should_configure_users:
                configure_users_and_groups(config)

            # Perform backup if requested
            if args.backup:
                backup_all_routers(routers, config, router_configs)


    except KeyboardInterrupt:
        console.print("\n\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
