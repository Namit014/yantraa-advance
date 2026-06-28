"""
Yantraa Assembly Engine — Graph-based CAD Assembly Solver

Takes an assembly graph (parent→child relationships with connection ports)
and mount point metadata, then computes world-space transforms for each
component so they snap together properly.

PRODUCTION NOTE:
  - assembly_metadata.json and assembly_templates.json are stored in
    knowledgebase/Robots_MetaData/ and committed to git.
  - CAD STEP files are served via the /api/cad/<filename> endpoint (which
    reads from local knowledgebase/** on the backend) or from S3 if
    S3_BUCKET_URL is configured in .env.
  - This file must NOT fail when JSON files are missing — it degrades
    gracefully so the design pipeline still produces component/connection
    data even without mount-point metadata.
"""

import os
import json
import math
from typing import Dict, List, Optional, Tuple
from collections import deque

# ── Path resolution ───────────────────────────────────────────────────────────

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_KB_DIR = os.path.abspath(os.path.join(_SRC_DIR, "..", "knowledgebase", "Robots_MetaData"))

_meta_path = os.path.join(_KB_DIR, "assembly_metadata.json")
_templates_path = os.path.join(_KB_DIR, "assembly_templates.json")

# S3 base URL (optional) — used to build CAD URLs in production
S3_BUCKET_URL = os.getenv("S3_BUCKET_URL", "").rstrip("/")


def _cad_url(filename: str, category: str = "") -> str:
    """
    Return the URL to serve a CAD file.
    Priority:
    1. Check if file exists locally in knowledgebase/
    2. If S3_BUCKET_URL is set, use cad_registry.get_s3_url() for the exact S3 path
    3. Fall back to /cad/<filename> endpoint
    """
    local_kb = os.path.abspath(os.path.join(_SRC_DIR, "..", "knowledgebase"))
    import glob as _glob
    matches = _glob.glob(os.path.join(local_kb, "**", filename), recursive=True)
    if matches:
        print(f"[AssemblyEngine] CAD file found locally: {matches[0]}")
        return f"/cad/{filename}"

    if S3_BUCKET_URL:
        try:
            from cad_registry import get_s3_url
            return get_s3_url(filename, S3_BUCKET_URL)
        except ImportError:
            url = f"{S3_BUCKET_URL}/knowledgebase/{filename}"
            print(f"[AssemblyEngine] cad_registry not found, using: {url}")
            return url

    print(f"[AssemblyEngine] WARNING: CAD file {filename!r} not found locally and no S3_BUCKET_URL configured.")
    return f"/cad/{filename}"


# ── Metadata / Template loaders ───────────────────────────────────────────────

def _load_metadata() -> dict:
    """Load mount point metadata. Returns empty dict on any failure."""
    if not os.path.exists(_meta_path):
        print(f"[AssemblyEngine] assembly_metadata.json not found at: {_meta_path}")
        return {}
    try:
        with open(_meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = data.get("components", {})
        print(f"[AssemblyEngine] Loaded metadata for {len(result)} components.")
        return result
    except Exception as e:
        print(f"[AssemblyEngine] Failed to load metadata: {e}")
        return {}


def _load_templates() -> dict:
    """Load pre-built assembly templates. Returns empty dict on any failure."""
    if not os.path.exists(_templates_path):
        print(f"[AssemblyEngine] assembly_templates.json not found at: {_templates_path}")
        return {}
    try:
        with open(_templates_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        print(f"[AssemblyEngine] Loaded {len(result)} assembly templates.")
        return result
    except Exception as e:
        print(f"[AssemblyEngine] Failed to load templates: {e}")
        return {}


# ── Template matching ─────────────────────────────────────────────────────────

def match_template(query: str) -> Optional[dict]:
    """
    Check if the user's query matches a pre-built assembly template.
    Returns the template dict if found, None otherwise.
    """
    templates = _load_templates()
    if not templates:
        print("[AssemblyEngine] No templates available — skipping template match.")
        return None

    query_lower = query.lower()
    best_match = None
    best_score = 0

    for template_id, template in templates.items():
        keywords = template.get("keywords", [])
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > best_score:
            best_score = score
            best_match = template

    if best_match and best_score > 0:
        print(f"[AssemblyEngine] Matched template: {best_match.get('description', 'unknown')} (score={best_score})")
        return best_match

    print("[AssemblyEngine] No template matched the query.")
    return None


# ── Template → Design data conversion ────────────────────────────────────────

def template_to_design_data(template: dict) -> dict:
    """
    Convert a template's graph into the standard design API response format.
    No longer checks for local CAD file existence — all parts are assumed
    available via the CAD serving endpoint or S3. Only truly generic/unknown
    parts end up in `missing`.
    """
    graph_nodes = template.get("graph", [])
    metadata = _load_metadata()

    subsystems_map: dict = {}
    bom: list = []
    connections: list = []
    assembly_graph: list = []
    missing: list = []

    for node in graph_nodes:
        part = node.get("part", "")
        role = node.get("role", "component")
        node_id = node.get("id", part)
        parent = node.get("parent")

        # Determine subsystem category
        category = "Structure"
        part_l = part.lower()
        if any(k in part_l for k in ["actuator", "motor", "propeller", "a-2475", "a-2020", "a-2200", "a-2438"]):
            category = "Actuators"
        elif any(k in part_l for k in ["gripper", "a-2055", "a-2143", "a-2292"]):
            category = "End_Effectors"
        elif any(k in part_l for k in ["driver", "battery", "controller", "a-2433", "a-2525", "a-2432"]):
            category = "Electronics"

        if category not in subsystems_map:
            subsystems_map[category] = {"name": category, "components": []}

        subsystems_map[category]["components"].append({
            "id": node_id,
            "name": part,
            "role": role,
            "voltage": "48V" if category == "Actuators" else "N/A",
            "interface": "RJ45" if category in ("Actuators", "Electronics") else "Mechanical"
        })

        bom.append({"id": node_id, "name": part, "qty": 1})

        # Only mark as missing if not in metadata AND not a known HEBI/standard part.
        # We no longer check the local filesystem — the backend serves CAD via /api/cad/
        in_metadata = part in metadata
        looks_known = (
            part.startswith("A-") or
            part.startswith("quadcopter") or
            part.startswith("brushless") or
            part in ("propeller", "flight_controller", "lipo_battery")
        )
        if not in_metadata and not looks_known:
            if not any(m["name"] == part for m in missing):
                missing.append({"name": part})
                print(f"[AssemblyEngine] Part '{part}' has no metadata — marking as missing/custom.")

        if parent:
            connections.append({
                "from": parent,
                "to": node_id,
                "relation": "drives" if category == "Actuators" else "mounted_on",
                "protocol": "Mechanical"
            })
            assembly_graph.append({
                "parent": parent,
                "child": node_id,
                "parent_port": node.get("port", "output_flange"),
                "child_port": "input_flange"
            })

    print(f"[AssemblyEngine] template_to_design_data: {len(bom)} BOM items, {len(connections)} connections, {len(missing)} missing.")
    return {
        "subsystems": list(subsystems_map.values()),
        "connections": connections,
        "bom": bom,
        "missing": missing,
        "validation": [],
        "assembly_graph": assembly_graph,
        "_template_graph": graph_nodes
    }


# ── Assembly solver ───────────────────────────────────────────────────────────

def solve_assembly(
    graph_nodes: List[dict],
    assembly_graph: List[dict],
    metadata: Optional[dict] = None
) -> List[dict]:
    """
    Walk the assembly graph and compute world-space transforms for each part.

    Args:
        graph_nodes: List of dicts with at least {"id": str, "part": str}
        assembly_graph: List of dicts with {"parent": str, "child": str,
                        "parent_port": str, "child_port": str}
        metadata: Optional pre-loaded metadata dict. Loaded from file if None.

    Returns:
        List of dicts:
        [{"id": str, "part": str, "cad_url": str,
          "position": [x,y,z], "rotation": [rx,ry,rz]}]
    """
    if metadata is None:
        metadata = _load_metadata()

    if not graph_nodes:
        return []

    # Build adjacency: parent_id → [(child_id, parent_port, child_port)]
    children_of: dict = {}
    parent_of: dict = {}
    for edge in assembly_graph:
        pid = edge["parent"]
        cid = edge["child"]
        pp = edge.get("parent_port", "output_flange")
        cp = edge.get("child_port", "input_flange")
        children_of.setdefault(pid, []).append((cid, pp, cp))
        parent_of[cid] = pid

    # Build node lookup
    node_map = {n["id"]: n for n in graph_nodes}

    # Find root(s) — nodes with no parent
    roots = [n["id"] for n in graph_nodes if n["id"] not in parent_of]
    if not roots:
        roots = [graph_nodes[0]["id"]]

    # BFS from root, computing transforms
    transforms: dict = {}
    for root_id in roots:
        transforms[root_id] = {"position": [0, 0, 0], "rotation": [0, 0, 0]}
        queue = [root_id]
        while queue:
            current_id = queue.pop(0)
            current_node = node_map.get(current_id)
            if not current_node:
                continue

            current_transform = transforms[current_id]
            current_part = current_node.get("part", "")
            current_meta = metadata.get(current_part, {})

            for child_id, parent_port, child_port in children_of.get(current_id, []):
                child_node = node_map.get(child_id)
                if not child_node:
                    continue

                child_part = child_node.get("part", "")
                child_meta = metadata.get(child_part, {})

                child_transform = _compute_child_transform(
                    current_transform,
                    current_meta,
                    parent_port,
                    child_meta,
                    child_port
                )

                transforms[child_id] = child_transform
                queue.append(child_id)

    # Build result with CAD URLs.
    # Assign deterministic grid positions to orphan nodes (those not reached by BFS)
    # so they never collapse to the same [0,0,0] point — which triggers false overlap warnings.
    ORPHAN_SPACING_MM = 150  # horizontal spacing between unplaced components
    orphan_index = 0

    results = []
    for node in graph_nodes:
        nid = node["id"]
        part = node.get("part", "")
        meta = metadata.get(part, {})
        step_file = meta.get("step_file", f"{part}.STEP")
        category = meta.get("category", "")

        if nid in transforms:
            t = transforms[nid]
        else:
            # Orphan: not reachable via assembly_graph (no parent-child edges defined).
            # Place it on a spaced grid row so distance != 0 between orphans.
            t = {
                "position": [orphan_index * ORPHAN_SPACING_MM, 0, 0],
                "rotation": [0, 0, 0]
            }
            orphan_index += 1

        results.append({
            "id": nid,
            "part": part,
            "cad_url": _cad_url(step_file, category),
            "position": t["position"],
            "rotation": t["rotation"],
            "is_placed": nid in transforms  # flag: True = real transform, False = auto-spaced
        })

    print(f"[AssemblyEngine] Solved {len(results)} transforms ({orphan_index} orphan nodes auto-spaced).")
    return results


# ── Child transform computation ───────────────────────────────────────────────

def _compute_child_transform(
    parent_transform: dict,
    parent_meta: dict,
    parent_port: str,
    child_meta: dict,
    child_port: str
) -> dict:
    parent_pos = parent_transform["position"]
    parent_rot = parent_transform["rotation"]

    parent_mounts = parent_meta.get("mount_points", {})
    parent_port_data = parent_mounts.get(parent_port, {})

    child_mounts = child_meta.get("mount_points", {})
    child_port_data = child_mounts.get(child_port, {})

    port_local = parent_port_data.get("position", [0, 0, 0])
    port_rot_offset = parent_port_data.get("rotation_offset", [0, 0, 0])

    rotated_port = _rotate_point(port_local, parent_rot)

    child_input_local = child_port_data.get("position", [0, 0, 0])

    child_rot = [
        parent_rot[0] + port_rot_offset[0],
        parent_rot[1] + port_rot_offset[1],
        parent_rot[2] + port_rot_offset[2]
    ]

    rotated_child_input = _rotate_point(child_input_local, child_rot)

    child_pos = [
        parent_pos[0] + rotated_port[0] - rotated_child_input[0],
        parent_pos[1] + rotated_port[1] - rotated_child_input[1],
        parent_pos[2] + rotated_port[2] - rotated_child_input[2]
    ]

    return {
        "position": [round(p, 2) for p in child_pos],
        "rotation": [round(r, 4) for r in child_rot]
    }


def _rotate_point(point: List[float], euler_angles: List[float]) -> List[float]:
    x, y, z = point
    rx, ry, rz = euler_angles

    cos_rx, sin_rx = math.cos(rx), math.sin(rx)
    y1 = y * cos_rx - z * sin_rx
    z1 = y * sin_rx + z * cos_rx
    x1 = x

    cos_ry, sin_ry = math.cos(ry), math.sin(ry)
    x2 = x1 * cos_ry + z1 * sin_ry
    z2 = -x1 * sin_ry + z1 * cos_ry
    y2 = y1

    cos_rz, sin_rz = math.cos(rz), math.sin(rz)
    x3 = x2 * cos_rz - y2 * sin_rz
    y3 = x2 * sin_rz + y2 * cos_rz
    z3 = z2

    return [x3, y3, z3]


# ── Assembly validation ───────────────────────────────────────────────────────

def validate_assembly(transforms: List[dict], metadata: Optional[dict] = None) -> List[dict]:
    """Basic validation of the assembled robot. Returns warnings/errors."""
    if metadata is None:
        metadata = _load_metadata()

    issues = []

    for i, t1 in enumerate(transforms):
        for j, t2 in enumerate(transforms):
            if i >= j:
                continue

            p1 = t1["position"]
            p2 = t2["position"]

            # Skip collision check if either component is at the origin [0,0,0].
            # Origin means the component is unplaced (no mount-point data available),
            # not that it physically overlaps — this was producing false 0.0mm warnings.
            if p1 == [0, 0, 0] or p2 == [0, 0, 0]:
                continue

            # Also skip auto-spaced orphan nodes (flagged during solve_assembly).
            if not t1.get("is_placed", True) or not t2.get("is_placed", True):
                continue

            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))
            if dist < 5 and t1["part"] != t2["part"]:
                issues.append({
                    "type": "warning",
                    "message": f"Parts {t1['part']} and {t2['part']} may be overlapping (distance: {dist:.1f}mm)"
                })

    for t in transforms:
        if t["part"] not in metadata:
            issues.append({
                "type": "warning",
                "message": f"No mount point data for {t['part']} — position may be approximate"
            })

    actuator_count = sum(1 for t in transforms if metadata.get(t["part"], {}).get("category") == "Actuators")
    battery_count = sum(1 for t in transforms if "battery" in t["part"].lower() or "a-2525" in t["part"].lower())

    if actuator_count > 0 and battery_count == 0:
        issues.append({
            "type": "warning",
            "message": f"Robot has {actuator_count} actuators but no battery — add A-2525-01 Wattman Battery"
        })

    return issues
