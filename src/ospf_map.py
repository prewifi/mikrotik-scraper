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

        router_id = None
        for inst in instances:
            if inst.get("router_id"):
                router_id = inst["router_id"]
                break

        if not router_id:
            router_id = router["host"]

        areas = set()
        for area in ospf.get("areas", []):
            area_name = area.get("name", "")
            if area_name and area_name != "backbone":
                areas.add(area_name)

        neighbor_count = len(ospf.get("neighbors", []))
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


def _build_link_address_map(ospf_data: dict) -> Dict[str, List[str]]:
    """
    Build a map of router_id -> list of link IP addresses.

    Scans the neighbor entries of every router: when router A lists router B
    as a neighbor with address X, X is the IP of B's link interface toward A.
    This is more accurate than using router['host'] (management IP), which
    often equals the router_id.

    Returns:
        Dict[str, List[str]]: router_id -> sorted list of unique link IPs
    """
    link_addrs: Dict[str, list] = {}

    for router in ospf_data.get("routers", []):
        if not router.get("connection_successful") or not router.get("ospf"):
            continue
        for neigh in router["ospf"].get("neighbors", []):
            neigh_rid = neigh.get("router_id", "")
            addr = neigh.get("address", "")
            if neigh_rid and addr:
                link_addrs.setdefault(neigh_rid, [])
                if addr not in link_addrs[neigh_rid]:
                    link_addrs[neigh_rid].append(addr)

    # Sort each list for consistent display
    return {rid: sorted(addrs) for rid, addrs in link_addrs.items()}



def _build_link_pair_map(ospf_data: dict) -> Dict[Tuple[str, str], str]:
    """
    Build (local_rid, neighbor_rid) -> neighbor_address mapping.

    When router A lists router B as neighbor with address X,
    X is B's link IP as seen from A's side.
    So (A_rid, B_rid) -> X  means "B's IP toward A is X".
    """
    pair: Dict[Tuple[str, str], str] = {}
    for router in ospf_data.get("routers", []):
        if not router.get("connection_successful") or not router.get("ospf"):
            continue
        ospf = router["ospf"]
        local_rid = None
        for inst in ospf.get("instances", []):
            if inst.get("router_id"):
                local_rid = inst["router_id"]
                break
        if not local_rid:
            local_rid = router["host"]
        for neigh in ospf.get("neighbors", []):
            neigh_rid = neigh.get("router_id", "")
            addr = neigh.get("address", "")
            if neigh_rid and addr:
                pair[(local_rid, neigh_rid)] = addr
    return pair

def generate_ospf_map(json_path: str, output_path: str) -> str:
    """
    Generate an interactive HTML network map from an OSPF JSON export.

    Uses a two-pass approach:
      Pass 1: Add all nodes (known routers + external neighbors)
      Pass 2: Add all edges from neighbor adjacencies
    """
    with open(json_path, "r", encoding="utf-8") as f:
        ospf_data = json.load(f)

    rid_map = _build_router_id_map(ospf_data)
    link_addr_map = _build_link_address_map(ospf_data)
    link_pair_map = _build_link_pair_map(ospf_data)
    area_color_map: Dict[str, str] = {}

    # Create pyvis network — NO select_menu/filter_menu (they break the layout)
    net = Network(
        height="100vh",
        width="100%",
        bgcolor="#1a1a2e",
        font_color="#e0e0e0",
        directed=False,
        select_menu=False,
        filter_menu=False,
    )

    # Configure physics and interaction via Barnes-Hut algorithm
    net.barnes_hut(
        gravity=-8000,
        central_gravity=0.3,
        spring_length=200,
        spring_strength=0.04,
        damping=0.09,
        overlap=0.5,
    )

    # ================================================================
    #  PASS 1: Add ALL nodes first (pyvis requires nodes before edges)
    # ================================================================
    added_nodes: Set[str] = set()

    # 1a. Add known routers from our inventory
    for router in ospf_data.get("routers", []):
        if not router.get("connection_successful") or not router.get("ospf"):
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

        shape = "diamond" if len(neighbors) >= 3 else "dot"

        node_label = (
            f"{router['identity']}\n"
            f"{router_id}"
        )

        net.add_node(
            router_id,
            label=node_label,
            color=node_color,
            shape=shape,
            title=tooltip,
            size=node_size,
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

            # IPs at each end of the link:
            #   neigh.address = neighbor's IP as seen from this router
            #   link_pair_map[(neigh_rid, router_id)] = this router's IP as seen from neighbor
            local_ip = link_pair_map.get((neigh_rid, router_id), "")
            remote_ip = neigh.get("address", "")
            if local_ip and remote_ip:
                edge_label = f"{local_ip}\n{remote_ip}"
            elif remote_ip:
                edge_label = remote_ip
            else:
                edge_label = None

            net.add_edge(
                router_id,
                neigh_rid,
                color=edge_color,
                title=edge_title,
                label=edge_label,
                width=edge_width,
                font={"size": 9, "color": "#b0b0b0", "align": "middle"},
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

    # Title bar overlay
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

    # Full-viewport canvas with no margins
    html = html.replace(
        "<body>",
        '<body style="margin:0;padding:0;overflow:hidden;">'
    )

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
