"""
Configuration orchestration for Mikrotik Network Inventory System.

This module handles configuration operations (IP services, users, syslog, SNMP)
across multiple routers.
"""

import logging
from typing import Dict, List, Tuple

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)

from mikrotik_client import MikrotikClient
from models import (
    IPServiceConfig,
    LoggingTopicConfig,
    SNMPCommunityConfig,
    SNMPConfig,
    SyslogConfig,
    UserConfig,
    UserGroupConfig,
)

console = Console()
logger = logging.getLogger(__name__)


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
            console.print("  [red]✗ Failed to connect[/red]\n")
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
                        IPServiceConfig(service_name=service_name, addresses=addresses)
                    )

            if not service_configs:
                console.print("  [yellow]⚠ No valid service configurations[/yellow]\n")
                client.disconnect()
                continue

            # Apply configuration with rollback
            success, scheduler_name, error = client.set_ip_service_addresses(
                service_configs=service_configs,
                create_rollback=create_rollback,
                rollback_timeout=rollback_timeout,
            )

            if success:
                console.print("  [green]✓ Configuration applied successfully[/green]")
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
            username = router_conf.get(
                "username", config.get("default_credentials", {}).get("username")
            )
            password = router_conf.get(
                "password", config.get("default_credentials", {}).get("password")
            )
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
        task = progress.add_task("[cyan]Configuring syslog...", total=total_routers)

        for router_conf in routers_config:
            host = router_conf.get("ip") or router_conf.get("host")
            username = router_conf.get(
                "username", config.get("default_credentials", {}).get("username")
            )
            password = router_conf.get(
                "password", config.get("default_credentials", {}).get("password")
            )
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

    console.print(
        f"\n[bold cyan]Configuring SNMP on {total_routers} router(s)...[/bold cyan]\n"
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Configuring SNMP...", total=total_routers)

        for router_conf in routers_config:
            host = router_conf.get("ip") or router_conf.get("host")
            username = router_conf.get(
                "username", config.get("default_credentials", {}).get("username")
            )
            password = router_conf.get(
                "password", config.get("default_credentials", {}).get("password")
            )
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
