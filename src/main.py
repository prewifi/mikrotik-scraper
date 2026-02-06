"""
Mikrotik Network Inventory System.

Main orchestrator for collecting, analyzing, and saving network inventory data
from Mikrotik routers via RouterOS API.
"""

import logging
import sys
import time

import yaml
from rich.console import Console
from rich.logging import RichHandler

from analyzer import NetworkAnalyzer
from backup_manager import BackupManager
from backup_orchestrator import backup_all_routers
from cli import parse_args
from collectors import collect_all_routers
from config_orchestrator import (
    configure_ip_services_all_routers,
    configure_snmp_all_routers,
    configure_syslog_all_routers,
    configure_users_and_groups,
)
from display import display_banner, display_summary, generate_execution_report
from inventory import InventoryManager
from mikrotik_client import MikrotikClient
from models import NetworkInventory, Router
from sftp_client import SFTPClientManager

console = Console()
logger = logging.getLogger(__name__)


def setup_logging(config: dict) -> None:
    """
    Setup logging configuration.

    Parameters:
        config (dict): Logging configuration from config file.
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


def load_config(config_path: str) -> dict:
    """
    Load configuration from YAML file.

    Parameters:
        config_path (str): Path to configuration file.

    Returns:
        dict: Configuration dictionary.
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


def _run_backup_only_mode(config: dict) -> None:
    """
    Run backup-only mode - connect to routers just for backup, skip full data collection.

    Parameters:
        config (dict): Configuration dictionary.
    """
    router_configs = config.get("routers", [])
    backup_config = config.get("backup", {})
    sftp_config = config.get("sftp", {})
    default_creds = config.get("default_credentials", {})

    if not backup_config.get("enabled", True):
        console.print("[yellow]Backup is disabled in configuration[/yellow]")
        sys.exit(0)

    console.print(
        f"\n[bold cyan]Starting backup process for {len(router_configs)} router(s)...[/bold cyan]\n"
    )

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
                minimal_router = Router(
                    ip_address=host,
                    identity=identity,
                    connection_successful=True,
                )

                # Track created files for download
                created_backup_file = None
                created_rsc_file = None
                created_rsc_verbose_file = None

                # Perform backup
                if backup_config.get("create_backup", True):
                    success, backup_name = backup_manager.create_backup(
                        client.api, minimal_router
                    )
                    if success:
                        created_backup_file = f"{backup_name}.backup"
                        logger.info(f"Backup created: {created_backup_file}")

                # Export configuration via SSH (API doesn't support export)
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
                        success_v, stdout_v, stderr_v = export_sftp.execute_command(
                            export_cmd_verbose
                        )

                        if success_v:
                            created_rsc_verbose_file = f"{export_name_verbose}.rsc"
                            logger.info(
                                f"Verbose export created via SSH: {created_rsc_verbose_file}"
                            )
                        else:
                            logger.error(f"Verbose export failed: {stderr_v}")

                        export_sftp.disconnect()

                        # Wait for files to be written
                        time.sleep(5)
                    else:
                        logger.error(
                            f"Could not connect via SSH to export config on {host}"
                        )

                # Download only the newly created files via SFTP
                if sftp_enabled and (
                    created_backup_file or created_rsc_file or created_rsc_verbose_file
                ):
                    sftp_client = SFTPClientManager(
                        host, sftp_username, sftp_password, sftp_port, sftp_timeout
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
                failed_routers.append(
                    {"ip": host, "identity": host, "error": "Failed to connect"}
                )
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


def _run_normal_mode(args, config: dict) -> None:
    """
    Run normal mode - collect inventory, optionally configure and backup.

    Parameters:
        args: Parsed CLI arguments.
        config (dict): Configuration dictionary.
    """
    router_configs = config.get("routers", [])

    # Collect inventory
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
    should_configure = args.configure_services or (
        ip_services_config.get("enabled", False)
        and ip_services_config.get("apply_on_connect", False)
    )

    if should_configure:
        configure_ip_services_all_routers(config, router_configs)

    # Configure Users if requested or enabled
    user_mgmt_config = config.get("user_management", {})
    should_configure_users = (
        args.configure_users or user_mgmt_config.get("enabled", False)
    )

    if should_configure_users:
        configure_users_and_groups(config)

    # Perform backup if requested
    if args.backup:
        backup_all_routers(routers, config, router_configs)


def main() -> None:
    """Main entry point for the application."""
    args = parse_args()

    # Load configuration
    config = load_config(args.config)

    # Setup logging
    setup_logging(config)

    try:
        # Display banner
        display_banner()

        router_configs = config.get("routers", [])

        if args.configure_services_only:
            # Configure IP services only mode
            console.print("[bold cyan]IP Services configuration only mode...[/bold cyan]")
            configure_ip_services_all_routers(config, router_configs)

        elif args.configure_users_only:
            # Configure users only mode
            console.print("[bold cyan]User/Group configuration only mode...[/bold cyan]")
            configure_users_and_groups(config)

        elif args.configure_syslog_only:
            # Configure syslog only mode
            console.print("[bold cyan]Syslog configuration only mode...[/bold cyan]")
            configure_syslog_all_routers(config)

        elif args.configure_snmp_only:
            # Configure SNMP only mode
            console.print("[bold cyan]SNMP configuration only mode...[/bold cyan]")
            configure_snmp_all_routers(config)

        elif args.backup_only:
            # Backup only mode
            console.print("[bold cyan]Backup-only mode...[/bold cyan]")
            _run_backup_only_mode(config)

        else:
            # Normal mode - collect inventory
            _run_normal_mode(args, config)

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
