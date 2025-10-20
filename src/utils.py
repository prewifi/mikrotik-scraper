"""
Utility functions for the Mikrotik inventory system.
"""

import ipaddress
from typing import Optional


def is_valid_ip(ip_string: str) -> bool:
    """
    Check if a string is a valid IP address.

    Parameters:
        ip_string (str): String to validate.

    Returns:
        bool: True if valid IP address, False otherwise.
    """
    try:
        ipaddress.ip_address(ip_string)
        return True
    except ValueError:
        return False


def parse_cidr(cidr: str) -> tuple[str, int] | None:
    """
    Parse a CIDR notation string.

    Parameters:
        cidr (str): CIDR notation (e.g., "192.168.1.1/24").

    Returns:
        tuple[str, int] | None: Tuple of (IP, prefix_length) or None if invalid.
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        return (str(network.network_address), network.prefixlen)
    except ValueError:
        return None


def get_network_from_ip(ip_with_cidr: str) -> Optional[str]:
    """
    Extract network address from IP with CIDR notation.

    Parameters:
        ip_with_cidr (str): IP address with CIDR (e.g., "192.168.1.10/24").

    Returns:
        Optional[str]: Network address (e.g., "192.168.1.0/24") or None.
    """
    try:
        network = ipaddress.ip_network(ip_with_cidr, strict=False)
        return str(network)
    except ValueError:
        return None


def format_uptime(uptime_string: str) -> str:
    """
    Format RouterOS uptime string to human-readable format.

    Parameters:
        uptime_string (str): RouterOS uptime (e.g., "1w2d3h4m5s").

    Returns:
        str: Formatted uptime string.
    """
    # RouterOS format is already human-readable, but we could enhance it
    # For now, just return as-is
    return uptime_string


def sanitize_interface_name(name: str) -> str:
    """
    Sanitize interface name for use in filenames or identifiers.

    Parameters:
        name (str): Interface name.

    Returns:
        str: Sanitized name.
    """
    return name.replace("/", "-").replace(" ", "_")


def bytes_to_human(bytes_value: int) -> str:
    """
    Convert bytes to human-readable format.

    Parameters:
        bytes_value (int): Number of bytes.

    Returns:
        str: Human-readable string (e.g., "1.5 GB").
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"
