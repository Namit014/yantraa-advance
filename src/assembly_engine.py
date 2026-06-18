"""
Yantraa Assembly Engine — Graph-based CAD Assembly Solver

Takes an assembly graph (parent→child relationships with connection ports)
and mount point metadata, then computes world-space transforms for each
component so they snap together properly.
"""

import os
import json
import math
from typing import Dict, List, Optional, Tuple
from collections import deque

# Path to assembly metadata
_meta_path = os.path.join(
    os.path.dirname(__file__), "..", "knowledgebase", "Robots_MetaData", "assembly_metadata.json"
)

# Path to assembly templates
_templates_path = os.path.join(
    os.path.dirname(__file__), "..", "knowledgebase", "Robots_MetaData", "assembly_templates.json"
)


def _load_metadata() -> dict:
    """Load mount point metadata for all known components."""
    try:
        with open(_meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("components", {})
    except Exception as e:
        print(f"[AssemblyEngine] Failed to load metadata: {e}")
        return {}


def _load_templates() -> dict:
    """Load pre-built assembly templates."""
    try:
        with open(_templates_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[AssemblyEngine] Failed to load templates: {e}")
        return {}


def match_template(query: str) -> Optional[dict]:
    """
    Check if the user's query matches a pre-built assembly template.
    Returns the template dict if found, None otherwise.
    """
    templates = _load_templates()
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
    
    return None


def template_to_design_data(template: dict) -> dict:
    """
    Convert a template's graph into the standard design API response format
    (subsystems, connections, bom, assembly_graph).
    """
    import glob
    graph_nodes = template.get("graph", [])
    cad_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "knowledgebase", "CAD_Models"))
    
    # Group by role/category for subsystems
    subsystems_map = {}
    bom = []
    connections = []
    assembly_graph = []
    missing = []
    
    for node in graph_nodes:
        part = node.get("part", "")
        role = node.get("role", "component")
        node_id = node.get("id", part)
        parent = node.get("parent")
        
        # Determine subsystem category
        category = "Structure"
        part_l = part.lower()
        if "actuator" in part_l or "motor" in part_l or "propeller" in part_l or "a-2475" in part_l or "a-2020" in part_l or "a-2200" in part_l or "a-2438" in part_l:
            category = "Actuators"
        elif "gripper" in part_l or "a-2055" in part_l or "a-2143" in part_l or "a-2292" in part_l:
            category = "End_Effectors"
        elif "driver" in part_l or "battery" in part_l or "controller" in part_l or "a-2433" in part_l or "a-2525" in part_l or "a-2432" in part_l:
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
        
        # Check if the CAD file exists locally
        has_cad = False
        for ext in [".step", ".STEP", ".stp", ".STP"]:
            test_path = os.path.join(cad_base_dir, f"{part}{ext}")
            if os.path.exists(test_path):
                has_cad = True
                break
        
        if not has_cad:
            # Check recursively in subdirectories
            matches = glob.glob(os.path.join(cad_base_dir, "**", f"{part}.*"), recursive=True)
            if matches:
                has_cad = True
        
        if not has_cad:
            # Avoid duplicate missing items
            if not any(m["name"] == part for m in missing):
                missing.append({"name": part})
        
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
    
    return {
        "subsystems": list(subsystems_map.values()),
        "connections": connections,
        "bom": bom,
        "missing": missing,
        "validation": [],
        "assembly_graph": assembly_graph,
        "_template_graph": graph_nodes
    }


def solve_assembly(
    graph_nodes: List[dict],
    assembly_graph: List[dict],
    metadata: Optional[dict] = None
) -> List[dict]:
    """
    Walk the assembly graph and compute world-space transforms for each part.
    
    Args:
        graph_nodes: List of dicts with at least {"id": str, "part": str}
        assembly_graph: List of dicts with {"parent": str, "child": str, "parent_port": str, "child_port": str}
        metadata: Optional pre-loaded metadata dict. Loaded from file if None.
    
    Returns:
        List of dicts: [{"id": str, "part": str, "cad_url": str, "position": [x,y,z], "rotation": [rx,ry,rz]}]
    """
    if metadata is None:
        metadata = _load_metadata()
    
    if not graph_nodes:
        return []
    
    # Build adjacency: parent_id -> [(child_id, parent_port, child_port)]
    children_of = {}
    parent_of = {}
    for edge in assembly_graph:
        pid = edge["parent"]
        cid = edge["child"]
        pp = edge.get("parent_port", "output_flange")
        cp = edge.get("child_port", "input_flange")
        children_of.setdefault(pid, []).append((cid, pp, cp))
        parent_of[cid] = pid
    
    # Build node lookup
    node_map = {}
    for n in graph_nodes:
        node_map[n["id"]] = n
    
    # Find root(s) — nodes with no parent
    roots = [n["id"] for n in graph_nodes if n["id"] not in parent_of]
    if not roots:
        roots = [graph_nodes[0]["id"]]
    
    # BFS from root, computing transforms
    transforms = {}
    
    for root_id in roots:
        transforms[root_id] = {"position": [0, 0, 0], "rotation": [0, 0, 0]}
        
        queue = deque([root_id])
        while queue:
            current_id = queue.popleft()
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
    
    # Build result
    results = []
    for node in graph_nodes:
        nid = node["id"]
        part = node.get("part", "")
        meta = metadata.get(part, {})
        step_file = meta.get("step_file", f"{part}.STEP")
        
        t = transforms.get(nid, {"position": [0, 0, 0], "rotation": [0, 0, 0]})
        
        results.append({
            "id": nid,
            "part": part,
            "cad_url": f"/cad/{step_file}",
            "position": t["position"],
            "rotation": t["rotation"]
        })
    
    print(f"[AssemblyEngine] Solved {len(results)} transforms")
    return results


def _compute_child_transform(
    parent_transform: dict,
    parent_meta: dict,
    parent_port: str,
    child_meta: dict,
    child_port: str
) -> dict:
    """
    Compute the world-space transform of a child component given:
    - The parent's world transform
    - The parent's output port metadata
    - The child's input port metadata
    
    The child's input port is aligned to the parent's output port.
    """
    parent_pos = parent_transform["position"]
    parent_rot = parent_transform["rotation"]
    
    # Get parent output port position (relative to parent origin)
    parent_mounts = parent_meta.get("mount_points", {})
    parent_port_data = parent_mounts.get(parent_port, {})
    
    # Get child input port position (relative to child origin)  
    child_mounts = child_meta.get("mount_points", {})
    child_port_data = child_mounts.get(child_port, {})
    
    # Parent's port world position = parent_world_pos + rotated(port_local_pos)
    port_local = parent_port_data.get("position", [0, 0, 0])
    port_rot_offset = parent_port_data.get("rotation_offset", [0, 0, 0])
    
    # Apply parent rotation to port position
    rotated_port = _rotate_point(port_local, parent_rot)
    
    # Child's input port offset (we need to subtract this so the input aligns)
    child_input_local = child_port_data.get("position", [0, 0, 0])
    
    # Compute child world position:
    # child_world = parent_world + rotated(parent_output_pos) - rotated(child_input_pos)
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
    """
    Rotate a 3D point by Euler angles [rx, ry, rz] in radians.
    Uses XYZ rotation order.
    """
    x, y, z = point
    rx, ry, rz = euler_angles
    
    # Rotation around X
    cos_rx, sin_rx = math.cos(rx), math.sin(rx)
    y1 = y * cos_rx - z * sin_rx
    z1 = y * sin_rx + z * cos_rx
    x1 = x
    
    # Rotation around Y
    cos_ry, sin_ry = math.cos(ry), math.sin(ry)
    x2 = x1 * cos_ry + z1 * sin_ry
    z2 = -x1 * sin_ry + z1 * cos_ry
    y2 = y1
    
    # Rotation around Z
    cos_rz, sin_rz = math.cos(rz), math.sin(rz)
    x3 = x2 * cos_rz - y2 * sin_rz
    y3 = x2 * sin_rz + y2 * cos_rz
    z3 = z2
    
    return [x3, y3, z3]


def validate_assembly(transforms: List[dict], metadata: Optional[dict] = None) -> List[dict]:
    """
    Basic validation of the assembled robot.
    Returns a list of warnings/errors.
    """
    if metadata is None:
        metadata = _load_metadata()
    
    issues = []
    
    # Check for overlapping parts (simple distance check)
    for i, t1 in enumerate(transforms):
        for j, t2 in enumerate(transforms):
            if i >= j:
                continue
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(t1["position"], t2["position"])))
            if dist < 5 and t1["part"] != t2["part"]:
                issues.append({
                    "type": "warning",
                    "message": f"Parts {t1['part']} and {t2['part']} may be overlapping (distance: {dist:.1f}mm)"
                })
    
    # Check that all parts have metadata
    for t in transforms:
        if t["part"] not in metadata:
            issues.append({
                "type": "warning",
                "message": f"No mount point data for {t['part']} — position may be approximate"
            })
    
    # Check power budget (rough)
    actuator_count = sum(1 for t in transforms if metadata.get(t["part"], {}).get("category") == "Actuators")
    battery_count = sum(1 for t in transforms if "battery" in t["part"].lower() or "a-2525" in t["part"].lower())
    
    if actuator_count > 0 and battery_count == 0:
        issues.append({
            "type": "warning",
            "message": f"Robot has {actuator_count} actuators but no battery — add A-2525-01 Wattman Battery"
        })
    
    return issues
