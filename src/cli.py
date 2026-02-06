"""
CLI argument parsing for Mikrotik Network Inventory System.

This module handles command-line argument definition and parsing.
"""

import argparse
from typing import NamedTuple


class CLIArgs(NamedTuple):
    """Container for parsed CLI arguments."""

    config: str
    output_dir: str | None
    json_only: bool
    yaml_only: bool
    backup: bool
    backup_only: bool
    configure_services: bool
    configure_services_only: bool
    configure_users: bool
    configure_users_only: bool
    configure_syslog: bool
    configure_syslog_only: bool
    configure_snmp: bool
    configure_snmp_only: bool


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser.

    Returns:
        argparse.ArgumentParser: Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Mikrotik Network Inventory System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Configuration options
    parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        help="Override output directory from config",
    )

    # Output format options
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Save only JSON format",
    )
    parser.add_argument(
        "--yaml-only",
        action="store_true",
        help="Save only YAML format",
    )

    # Backup options
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create and download backups after inventory",
    )
    parser.add_argument(
        "--backup-only",
        action="store_true",
        help="Only perform backup operations (skip inventory)",
    )

    # IP services configuration options
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

    # User management options
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

    # Syslog configuration options
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

    # SNMP configuration options
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

    return parser


def parse_args(args: list[str] | None = None) -> CLIArgs:
    """
    Parse command line arguments.

    Parameters:
        args (list[str] | None): Arguments to parse. If None, uses sys.argv.

    Returns:
        CLIArgs: Named tuple containing parsed arguments.
    """
    parser = create_parser()
    parsed = parser.parse_args(args)

    return CLIArgs(
        config=parsed.config,
        output_dir=parsed.output_dir,
        json_only=parsed.json_only,
        yaml_only=parsed.yaml_only,
        backup=parsed.backup,
        backup_only=parsed.backup_only,
        configure_services=parsed.configure_services,
        configure_services_only=parsed.configure_services_only,
        configure_users=parsed.configure_users,
        configure_users_only=parsed.configure_users_only,
        configure_syslog=parsed.configure_syslog,
        configure_syslog_only=parsed.configure_syslog_only,
        configure_snmp=parsed.configure_snmp,
        configure_snmp_only=parsed.configure_snmp_only,
    )
