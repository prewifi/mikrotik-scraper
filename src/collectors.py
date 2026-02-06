"""
Router data collection for Mikrotik Network Inventory System.

This module handles collecting data from routers, both sequentially and in parallel.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)

from mikrotik_client import MikrotikClient
from models import Router

console = Console()
logger = logging.getLogger(__name__)


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


def _collect_parallel(
    router_configs: List[Dict],
    default_creds: Dict,
    collection_options: Dict,
    max_workers: int,
) -> List[Router]:
    """
    Collect data from routers in parallel.

    Parameters:
        router_configs (List[Dict]): List of router configurations.
        default_creds (Dict): Default credentials.
        collection_options (Dict): Collection options.
        max_workers (int): Maximum number of parallel workers.

    Returns:
        List[Router]: List of successfully collected routers.
    """
    routers = []

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

    return routers


def _collect_sequential(
    router_configs: List[Dict],
    default_creds: Dict,
    collection_options: Dict,
) -> List[Router]:
    """
    Collect data from routers sequentially.

    Parameters:
        router_configs (List[Dict]): List of router configurations.
        default_creds (Dict): Default credentials.
        collection_options (Dict): Collection options.

    Returns:
        List[Router]: List of successfully collected routers.
    """
    routers = []

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

    return routers


def collect_all_routers(config: Dict) -> List[Router]:
    """
    Collect data from all routers in configuration.

    Parameters:
        config (Dict): Configuration dictionary.

    Returns:
        List[Router]: List of router objects with collected data.
    """
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
        routers = _collect_parallel(
            router_configs, default_creds, collection_options, max_workers
        )
    else:
        routers = _collect_sequential(
            router_configs, default_creds, collection_options
        )

    console.print(
        f"\n[bold green]Successfully collected data from {len(routers)}/{len(router_configs)} routers[/bold green]\n"
    )

    return routers
