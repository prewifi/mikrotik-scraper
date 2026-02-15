"""
OSPF Network Map Generator.

Reads the OSPF JSON export and generates an interactive HTML network map
using pyvis and networkx. Routers are nodes, OSPF neighbor adjacencies
are edges, colored by OSPF area.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx
from pyvis.network import Network

logger = logging.getLogger(__name__)

# Color palette for OSPF areas (up to 20 distinct colors)
AREA_COLORS = [
    "#4FC3F7",  # Light Blue
    "#81C784",  # Green
    "#FFB74D",  # Orange
    "#E57373",  # Red
    "#BA68C8",  # Purple
    "#4DB6AC",  # Teal
    "#FFD54F",  # Amber
    "#F06292",  # Pink
    "#AED581",  # Light Green
    "#7986CB",  # Indigo
    "#FF8A65",  # Deep Orange
    "#A1887F",  # Brown
    "#90A4AE",  # Blue Grey
    "#DCE775",  # Lime
    "#4DD0E1",  # Cyan
    "#9575CD",  # Deep Purple
    "#FFF176",  # Yellow
    "#F48FB1",  # Light Pink
    "#80CBC4",  # Light Teal
    "#CE93D8",  # Light Purple
]


def _get_area_color(area_name: str, area_color_map: Dict[str, str]) -> str:
    """Get a consistent color for an OSPF area."""
    if area_name not in area_color_map:
        idx = len(area_color_map) % len(AREA_COLORS)
        area_color_map[area_name] = AREA_COLORS[idx]
    return area_color_map[area_name]


def _build_router_id_map(ospf_data: dict) -> Dict[str, dict]:
    """
    Build a mapping from OSPF router-id to router info.

    Returns:
        Dict[str, dict]: mapping of router_id -> {identity, host, areas, ...}
    """
    rid_map: Dict[str, dict] = {}

    for router in ospf_data.get("routers", []):
        if not router.get("connection_successful") or not router.get("ospf"):
            continue

        ospf = router["ospf"]
        instances = ospf.get("instances", [])

        # Use router_id from first instance
        router_id = None
        for inst in instances:
            if inst.get("router_id"):
                router_id = inst["router_id"]
                break

        if not router_id:
            router_id = router["host"]

        # Collect areas (excluding backbone for display)
        areas = set()
        for area in ospf.get("areas", []):
            area_name = area.get("name", "")
            if area_name and area_name != "backbone":
                areas.add(area_name)

        # Count active neighbors
        neighbor_count = len(ospf.get("neighbors", []))

        # Count active interfaces
        iface_count = len([
            i for i in ospf.get("interfaces", []) if not i.get("disabled")
        ])

        rid_map[router_id] = {
            "identity": router["identity"],
            "host": router["host"],
            "router_id": router_id,
            "areas": areas,
            "neighbor_count": neighbor_count,
            "interface_count": iface_count,
            "instances": instances,
        }

    return rid_map


def _get_router_id(router: dict) -> str:
    """Extract router_id from a router entry."""
    ospf = router.get("ospf")
    if not ospf:
        return router["host"]
    for inst in ospf.get("instances", []):
        if inst.get("router_id"):
            return inst["router_id"]
    return router["host"]


def generate_ospf_map(json_path: str, output_path: str) -> str:
    """
    Generate an interactive HTML network map from an OSPF JSON export.

    Uses a two-pass approach:
      Pass 1: Add all nodes (known routers + external neighbors)
      Pass 2: Add all edges from neighbor adjacencies

    Parameters:
        json_path (str): Path to the ospf_export.json file.
        output_path (str): Path for the output HTML file.

    Returns:
        str: Path to the generated HTML file.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        ospf_data = json.load(f)

    rid_map = _build_router_id_map(ospf_data)
    area_color_map: Dict[str, str] = {}

    # Create pyvis network
    net = Network(
        height="100vh",
        width="100%",
        bgcolor="#1a1a2e",
        font_color="#e0e0e0",
        directed=False,
        select_menu=True,
        filter_menu=True,
    )

    # Physics layout for readability
    net.set_options("""
    {
        "physics": {
            "barnesHut": {
                "gravitationalConstant": -8000,
                "centralGravity": 0.3,
                "springLength": 200,
                "springConstant": 0.04,
                "damping": 0.09,
                "avoidOverlap": 0.5
            },
            "stabilization": {
                "enabled": true,
                "iterations": 250,
                "updateInterval": 25
            }
        },
        "nodes": {
            "borderWidth": 2,
            "shadow": true,
            "font": {
                "size": 14,
                "face": "Inter, Roboto, sans-serif"
            }
        },
        "edges": {
            "smooth": {
                "type": "continuous"
            },
            "shadow": true,
            "font": {
                "size": 10,
                "align": "middle",
                "strokeWidth": 3,
                "strokeColor": "#1a1a2e"
            }
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 200,
            "navigationButtons": true,
            "keyboard": true
        }
    }
    """)

    # ================================================================
    #  PASS 1: Add ALL nodes first (pyvis requires nodes before edges)
    # ================================================================
    added_nodes: Set[str] = set()

    # 1a. Add known routers from our inventory
    for router in ospf_data.get("routers", []):
        if not router.get("connection_successful") or not router.get("ospf"):
            # Failed-connection nodes
            node_id = router["host"]
            if node_id not in added_nodes:
                net.add_node(
                    node_id,
                    label=router["identity"],
                    color="#616161",
                    shape="box",
                    title=f"<b>{router['identity']}</b><br>IP: {router['host']}<br>⚠️ Connection failed",
                    size=15,
                )
                added_nodes.add(node_id)
            continue

        ospf = router["ospf"]
        router_id = _get_router_id(router)

        if router_id in added_nodes:
            continue

        # Determine node color from primary area (non-backbone)
        areas = set()
        for area in ospf.get("areas", []):
            area_name = area.get("name", "")
            if area_name and area_name != "backbone":
                areas.add(area_name)

        if areas:
            primary_area = sorted(areas)[0]
            node_color = _get_area_color(primary_area, area_color_map)
        else:
            primary_area = "backbone"
            node_color = "#90A4AE"

        # Node size based on neighbor count
        neighbors = ospf.get("neighbors", [])
        node_size = 20 + len(neighbors) * 5
        node_size = min(node_size, 50)

        # Build tooltip
        area_list = ", ".join(sorted(areas)) if areas else "backbone only"
        networks = ospf.get("networks", [])
        active_nets = [n["network"] for n in networks if not n.get("disabled")]
        net_str = "<br>".join(active_nets[:8]) if active_nets else "none"

        tooltip = (
            f"<b>{router['identity']}</b><br>"
            f"<b>Host:</b> {router['host']}<br>"
            f"<b>Router ID:</b> {router_id}<br>"
            f"<b>Areas:</b> {area_list}<br>"
            f"<b>Neighbors:</b> {len(neighbors)}<br>"
            f"<b>OSPF Interfaces:</b> {len(ospf.get('interfaces', []))}<br>"
            f"<b>Active Networks:</b><br>{net_str}"
        )

        # Hub routers (≥3 neighbors) get diamond shape
        shape = "diamond" if len(neighbors) >= 3 else "dot"

        net.add_node(
            router_id,
            label=router["identity"],
            color=node_color,
            shape=shape,
            title=tooltip,
            size=node_size,
            group=primary_area,
        )
        added_nodes.add(router_id)

    # 1b. Discover and add external neighbor nodes (not in our inventory)
    for router in ospf_data.get("routers", []):
        if not router.get("connection_successful") or not router.get("ospf"):
            continue
        for neigh in router["ospf"].get("neighbors", []):
            neigh_rid = neigh.get("router_id", "")
            if neigh_rid and neigh_rid not in added_nodes:
                net.add_node(
                    neigh_rid,
                    label=neigh_rid,
                    color="#424242",
                    shape="triangle",
                    title=(
                        f"<b>External Router</b><br>"
                        f"Router ID: {neigh_rid}<br>"
                        f"Address: {neigh.get('address', '-')}"
                    ),
                    size=15,
                )
                added_nodes.add(neigh_rid)

    # ==================================
    #  PASS 2: Add ALL edges
    # ==================================
    added_edges: Set[Tuple[str, str]] = set()

    for router in ospf_data.get("routers", []):
        if not router.get("connection_successful") or not router.get("ospf"):
            continue

        ospf = router["ospf"]
        router_id = _get_router_id(router)

        for neigh in ospf.get("neighbors", []):
            neigh_rid = neigh.get("router_id", "")
            if not neigh_rid:
                continue

            # Deduplicate bidirectional edges (A↔B == B↔A)
            edge_key = tuple(sorted([router_id, neigh_rid]))
            if edge_key in added_edges:
                continue
            added_edges.add(edge_key)

            # Look up interface info for color and cost
            iface_name = neigh.get("interface", "")
            edge_area = None
            edge_cost = None
            for iface in ospf.get("interfaces", []):
                if iface.get("interface") == iface_name:
                    edge_area = iface.get("area")
                    edge_cost = iface.get("cost")
                    break

            edge_color = (
                _get_area_color(edge_area, area_color_map)
                if edge_area
                else "#555555"
            )

            edge_title = (
                f"<b>Link:</b> {router['identity']} ↔ "
                f"{rid_map.get(neigh_rid, {}).get('identity', neigh_rid)}<br>"
                f"<b>Interface:</b> {iface_name or '-'}<br>"
                f"<b>State:</b> {neigh.get('state', '-')}<br>"
                f"<b>Cost:</b> {edge_cost or '-'}<br>"
                f"<b>Adjacency:</b> {neigh.get('adjacency', '-')}"
            )

            edge_width = 2 if neigh.get("state") == "Full" else 1

            net.add_edge(
                router_id,
                neigh_rid,
                color=edge_color,
                title=edge_title,
                width=edge_width,
                label=f"c:{edge_cost}" if edge_cost else None,
            )

    # Build legend and save
    legend_html = _build_legend_html(area_color_map)
    net.save_graph(output_path)
    _inject_custom_html(output_path, legend_html, ospf_data)

    logger.info(f"OSPF network map saved to: {output_path}")
    return output_path


def _build_legend_html(area_color_map: Dict[str, str]) -> str:
    """Build an HTML legend for the OSPF areas."""
    items = []
    for area_name, color in sorted(area_color_map.items()):
        items.append(
            f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0;">'
            f'<span style="display:inline-block;width:14px;height:14px;'
            f'border-radius:50%;background:{color};border:1px solid #fff;"></span>'
            f'<span>{area_name}</span></div>'
        )

    items.append(
        '<div style="display:flex;align-items:center;gap:8px;margin:4px 0;">'
        '<span style="display:inline-block;width:14px;height:14px;'
        'border-radius:50%;background:#90A4AE;border:1px solid #fff;"></span>'
        '<span>Backbone only</span></div>'
    )
    items.append(
        '<div style="display:flex;align-items:center;gap:8px;margin:4px 0;">'
        '<span style="display:inline-block;width:14px;height:14px;'
        'border-radius:50%;background:#424242;border:1px solid #fff;"></span>'
        '<span>External (no data)</span></div>'
    )
    items.append(
        '<div style="display:flex;align-items:center;gap:8px;margin:4px 0;">'
        '<span style="display:inline-block;width:14px;height:14px;'
        'border-radius:50%;background:#616161;border:1px solid #fff;"></span>'
        '<span>Connection failed</span></div>'
    )

    legend = (
        '<div id="ospf-legend" style="position:fixed;top:10px;right:10px;'
        'background:rgba(26,26,46,0.92);border:1px solid #333;border-radius:12px;'
        'padding:16px 20px;z-index:9999;color:#e0e0e0;font-family:Inter,Roboto,sans-serif;'
        'font-size:13px;backdrop-filter:blur(10px);box-shadow:0 4px 24px rgba(0,0,0,0.4);'
        'max-height:80vh;overflow-y:auto;">'
        '<div style="font-weight:700;font-size:15px;margin-bottom:10px;'
        'border-bottom:1px solid #444;padding-bottom:8px;">🗺️ OSPF Areas</div>'
        + "".join(items)
        + '<div style="margin-top:12px;border-top:1px solid #444;padding-top:8px;'
        'font-size:11px;color:#888;">◆ Hub (≥3 neighbors) &nbsp; ● Node &nbsp; ▲ External</div>'
        '</div>'
    )
    return legend


def _inject_custom_html(html_path: str, legend_html: str, ospf_data: dict) -> None:
    """Inject custom legend and styling into the generated HTML."""
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    total_routers = ospf_data.get("total_routers", 0)
    generated = ospf_data.get("generated", "")

    # Add title bar
    title_bar = (
        '<div style="position:fixed;top:10px;left:10px;'
        'background:rgba(26,26,46,0.92);border:1px solid #333;border-radius:12px;'
        'padding:12px 20px;z-index:9999;color:#e0e0e0;font-family:Inter,Roboto,sans-serif;'
        'backdrop-filter:blur(10px);box-shadow:0 4px 24px rgba(0,0,0,0.4);">'
        f'<div style="font-weight:700;font-size:18px;">📡 OSPF Network Map</div>'
        f'<div style="font-size:12px;color:#888;margin-top:4px;">'
        f'{total_routers} routers • Generated {generated}</div>'
        '</div>'
    )

    # Inject before </body>
    injection = legend_html + title_bar
    html = html.replace("</body>", injection + "\n</body>")

    # Override body margin
    html = html.replace(
        "<body>",
        '<body style="margin:0;padding:0;overflow:hidden;">'
    )

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
