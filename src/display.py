"""
Display and reporting utilities for Mikrotik Network Inventory System.

This module handles console output, summary display, and report generation.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from rich.console import Console
from rich.table import Table

from models import NetworkInventory

console = Console()
logger = logging.getLogger(__name__)


def display_banner() -> None:
    """Display the application banner."""
    console.print(
        "\n[bold blue]╔═══════════════════════════════════════════════════════════════════╗[/bold blue]"
    )
    console.print(
        "[bold blue]║      MIKROTIK NETWORK INVENTORY SYSTEM                        ║[/bold blue]"
    )
    console.print(
        "[bold blue]╚═══════════════════════════════════════════════════════════════════╝[/bold blue]\n"
    )


def display_summary(inventory: NetworkInventory) -> None:
    """
    Display a summary of the collected inventory.

    Parameters:
        inventory (NetworkInventory): NetworkInventory object.
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


def display_operation_summary(
    title: str,
    successful: int,
    failed: int,
) -> None:
    """
    Display a summary for an operation.

    Parameters:
        title (str): Title of the summary section.
        successful (int): Number of successful operations.
        failed (int): Number of failed operations.
    """
    console.print(
        "\n[bold cyan]═══════════════════════════════════════════════════════════════════════[/bold cyan]"
    )
    console.print(f"[bold cyan]              {title.upper():^50}[/bold cyan]")
    console.print(
        "[bold cyan]═══════════════════════════════════════════════════════════════════════[/bold cyan]\n"
    )

    console.print(f"[green]Successful: {successful}[/green]")
    console.print(f"[red]Failed: {failed}[/red]")
    console.print(f"[cyan]Total: {successful + failed}[/cyan]\n")


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
        f.write("SUMMARY\n")
        f.write("-" * 30 + "\n")
        f.write(f"Total Routers:   {total}\n")
        f.write(f"Successful:      {len(successful_routers)}\n")
        f.write(f"Failed:          {len(failed_routers)}\n")
        f.write("\n")

        # Successful routers
        f.write(f"SUCCESSFUL ROUTERS ({len(successful_routers)})\n")
        f.write("-" * 30 + "\n")
        if successful_routers:
            for router in successful_routers:
                identity = router.get("identity", "Unknown")
                ip = router.get("ip", "Unknown")
                f.write(f"  ✓ {identity} ({ip})\n")
        else:
            f.write("  (none)\n")
        f.write("\n")

        # Failed routers
        f.write(f"FAILED ROUTERS ({len(failed_routers)})\n")
        f.write("-" * 30 + "\n")
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
        f.write("END OF REPORT\n")

    logger.info(f"Execution report saved to: {report_path}")
    console.print(f"[cyan]Report saved to: {report_path}[/cyan]")

    return str(report_path)


def display_backup_results(
    backup_results: List[tuple],
) -> None:
    """
    Display backup operation results in a table.

    Parameters:
        backup_results (List[tuple]): List of (router_name, success, message) tuples.
    """
    if not backup_results:
        return

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
