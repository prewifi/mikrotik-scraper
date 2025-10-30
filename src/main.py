"""
Mikrotik Network Inventory System.

Main orchestrator for collecting, analyzing, and saving network inventory data
from Mikrotik routers via RouterOS API.
"""

import argparse
import logging
import sys
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
from models import Router
from sftp_client import SFTPClientManager

console = Console()


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
            backup_dir=backup_config.get("directory", "inventory/backups"),
            use_sftp=backup_config.get("use_sftp", True),
        )

        router_backup_dir = backup_manager.get_router_backup_dir(router.identity)

        # Connect to router via API for creating backups
        api_client = MikrotikClient(ip, username, password, port, timeout)
        if not api_client.connect():
            return False, f"Failed to connect to {router.identity} via API"

        # Create new backup if configured
        if backup_config.get("create_backup", True):
            console.print(f"  [yellow]→[/yellow] Creating backup on {router.identity}...")
            success, backup_filename = api_client.create_backup()
            if not success:
                console.print(f"  [yellow]  ⚠ Backup creation failed[/yellow]")

        # Create RSC export if configured
        if backup_config.get("export_config", True):
            console.print(f"  [yellow]→[/yellow] Exporting configuration from {router.identity}...")
            success, export_filename = api_client.export_configuration()
            if not success:
                console.print(f"  [yellow]  ⚠ Configuration export failed[/yellow]")

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
            # Get available backup files
            backup_files = backup_manager.get_backup_files(sftp_client) or []
            rsc_files = backup_manager.get_rsc_files(sftp_client) or []

            # Download backup files
            if backup_files:
                console.print(
                    f"  [cyan]  Found {len(backup_files)} backup file(s)[/cyan]"
                )
                successful, failed = backup_manager.download_backup_files(
                    sftp_client, router, backup_files, router_backup_dir
                )

                if successful:
                    console.print(
                        f"  [green]  ✓ Downloaded {len(successful)} backup(s)[/green]"
                    )
                if failed:
                    console.print(
                        f"  [yellow]  ✗ Failed to download {len(failed)} backup(s)[/yellow]"
                    )

            # Download RSC files
            if rsc_files:
                console.print(
                    f"  [cyan]  Found {len(rsc_files)} RSC file(s)[/cyan]"
                )
                successful, failed = backup_manager.download_rsc_files(
                    sftp_client, router, rsc_files, router_backup_dir
                )

                if successful:
                    console.print(
                        f"  [green]  ✓ Downloaded {len(successful)} RSC file(s)[/green]"
                    )
                if failed:
                    console.print(
                        f"  [yellow]  ✗ Failed to download {len(failed)} RSC file(s)[/yellow]"
                    )

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

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Setup logging
    setup_logging(config)
    logger = logging.getLogger(__name__)

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

        if args.backup_only:
            # Backup only mode - collect data first, then backup
            console.print("[bold cyan]Backup-only mode: collecting router data first...[/bold cyan]")
            routers = collect_all_routers(config)

            if not routers:
                console.print("[red]No routers were successfully queried. Exiting.[/red]")
                sys.exit(1)

            # Perform backup
            router_configs = config.get("routers", [])
            backup_all_routers(routers, config, router_configs)

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

            # Perform backup if requested
            if args.backup:
                router_configs = config.get("routers", [])
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
