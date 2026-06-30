import os
import sys
import time
import networkx as nx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import re

# Add src to path to import component_mapper
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from component_mapper import canonicalize, classify, compute_confidence, detect_duplicates, infer_relationship_type, RELATION_TYPES

router = APIRouter()

class RawComponent(BaseModel):
    id: str
    name: str
    category: str
    description: str = ""
    connects_to: List[str] = []
    quantity: int = 1
    partNumber: Optional[str] = None
    aliases: List[str] = []
    assembly_parent: Optional[str] = None
    assembly_depth: int = 0
    relation_types: Dict[str, str] = {}
    confidence: Optional[float] = None
    subcategory: Optional[str] = None
    canonical_id: Optional[str] = None

class ConnectionOut(BaseModel):
    id: str
    fromId: str
    toId: str
    label: str
    relation_type: str
    confidence: float
    evidence_sources: List[str]
    isUserEdited: bool = False

class BuildGraphRequest(BaseModel):
    components: List[RawComponent]

class BuildGraphResponse(BaseModel):
    connections: List[ConnectionOut]
    components: List[RawComponent]
    assembly_tree: Dict[str, Any]
    canonical_map: Dict[str, str]
    isolated_nodes: List[str]
    low_confidence_edges: List[str]
    warnings: List[str]

# Fuzzy match Python implementation
def fuzzy_match(a: str, b: str) -> bool:
    def normalize(s: str) -> str:
        return re.sub(r'[^a-z0-9]', '', s.lower())
    
    na = normalize(a)
    nb = normalize(b)
    if na in nb or nb in na:
        return True
    
    words_a = [w for w in re.split(r'[^a-z0-9]+', a.lower()) if len(w) > 1]
    words_b = [w for w in re.split(r'[^a-z0-9]+', b.lower()) if len(w) > 1]
    intersection = [w for w in words_a if w in words_b]
    
    if len(words_a) > 0 and len(intersection) / len(words_a) >= 0.6:
        return True
    if len(words_b) > 0 and len(intersection) / len(words_b) >= 0.6:
        return True
        
    return False

@router.post("/api/mapping/build-graph", response_model=BuildGraphResponse)
async def build_graph(request: BuildGraphRequest):
    raw_components = [c.dict() for c in request.components]
    
    # 1. Canonicalize and Deduplicate
    merged_components = detect_duplicates(raw_components)
    canonical_map = {}
    
    for mc in merged_components:
        canon = canonicalize(mc["name"], mc.get("aliases", []))
        mc["canonical_id"] = canon.canonical_id
        if not mc.get("subcategory"):
            mc["category"] = canon.category
            mc["subcategory"] = canon.subcategory
        canonical_map[mc["name"]] = canon.canonical_id
        for alias in mc.get("aliases", []):
            canonical_map[alias] = canon.canonical_id

    # Restore objects (for internal logic)
    components = [RawComponent(**mc) for mc in merged_components]
    
    connections: List[ConnectionOut] = []
    seen = set()
    warnings = []
    low_confidence_edges = []
    
    conn_counter = 0
    def add_conn(from_id: str, to_id: str, label: str, relation_type: str, confidence: float, sources: List[str]):
        nonlocal conn_counter
        if not from_id or not to_id or from_id == to_id:
            return
        key1 = f"{from_id}->{to_id}->{label}"
        key2 = f"{to_id}->{from_id}->{label}"
        if key1 in seen or key2 in seen:
            return
        seen.add(key1)
        
        conn_id = f"conn-nx-{conn_counter}-{int(time.time() * 1000)}"
        conn_counter += 1
        
        connections.append(ConnectionOut(
            id=conn_id,
            fromId=from_id,
            toId=to_id,
            label=label,
            relation_type=relation_type,
            confidence=confidence,
            evidence_sources=sources,
            isUserEdited=False
        ))
        if confidence < 0.90:
            low_confidence_edges.append(conn_id)
        
    comp_map = {c.id: c for c in components}
    
    G = nx.DiGraph()
    for c in components:
        G.add_node(c.id, category=c.category, label=c.name)

    # Calculate Confidence function
    def get_confidence(src: RawComponent, dst: RawComponent, rel_type: str, source_type: str) -> float:
        geo = 0.7 if src.partNumber else 0.4
        bom = 1.0 if source_type == "connects_to" else 0.5
        draw = 0.5
        meta = 1.0 if src.assembly_parent else (0.6 if src.description else 0.3)
        llm = 1.0 if rel_type in src.relation_types.values() else 0.6
        return compute_confidence(geo, bom, draw, meta, llm)

    # Primary pass - use RAG connects_to
    for rc in components:
        for target_name in rc.connects_to:
            to_node = next((n for n in components if fuzzy_match(n.name, target_name)), None)
            if not to_node:
                continue
                
            src_id = rc.id
            dst_id = to_node.id
            
            # Enforce directionality overrides
            if rc.category == 'actuator' and to_node.category == 'controller':
                src_id, dst_id = dst_id, src_id
            elif to_node.category == 'power':
                src_id, dst_id = dst_id, src_id
                
            src_node = comp_map[src_id]
            dst_node = comp_map[dst_id]
            
            # 1. Try explicitly provided relation from LLM
            rel_type = src_node.relation_types.get(dst_node.name)
            if not rel_type:
                rel_type = src_node.relation_types.get(target_name)
                
            # 2. Fallback to inference
            if not rel_type:
                rel_type = infer_relationship_type(src_node.category, dst_node.category, src_node.name, dst_node.name)
                
            conf = get_confidence(src_node, dst_node, rel_type, "connects_to")
            
            # Derive label for backward compat
            label = "connection"
            if "mechanical" in src_node.category or "mechanical" in dst_node.category: label = "linkage"
            if rel_type in ["drives", "transmits_torque_to"]: label = "drive"
            if rel_type in ["electrically_connected", "pneumatically_connected"]: label = "power"
            if rel_type in ["controls", "senses"]: label = "data"
            
            if label == "power":
                add_conn(src_id, dst_id, "power", rel_type, conf, ["connects_to", "llm"])
                add_conn(src_id, dst_id, "ground", "electrically_connected", conf, ["inferred"])
                G.add_edge(src_id, dst_id, label="power")
                G.add_edge(src_id, dst_id, label="ground")
            else:
                add_conn(src_id, dst_id, label, rel_type, conf, ["connects_to"])
                G.add_edge(src_id, dst_id, label=label)

    # Secondary fallback for unconnected nodes
    by_category = {}
    for c in components:
        by_category.setdefault(c.category, []).append(c)
        
    controllers = by_category.get("controller", [])
    actuators = by_category.get("actuator", [])
    sensors = by_category.get("sensor", [])
    mechanical = by_category.get("mechanical", [])
    power = by_category.get("power", [])
    electronic = by_category.get("electronic", [])
    
    connected_ids = set()
    for c in connections:
        connected_ids.add(c.fromId)
        connected_ids.add(c.toId)
        
    def add_inferred(src: RawComponent, dst: RawComponent, label: str, rel_type: str):
        conf = get_confidence(src, dst, rel_type, "inferred")
        add_conn(src.id, dst.id, label, rel_type, conf, ["inferred"])
        G.add_edge(src.id, dst.id, label=label)

    for a in actuators:
        if a.id not in connected_ids:
            for c in controllers:
                add_inferred(c, a, "drive", "controls")
                
    for s in sensors:
        if s.id not in connected_ids:
            for c in controllers:
                add_inferred(s, c, "data", "senses")
                
    for i, m in enumerate(mechanical):
        if m.id not in connected_ids and actuators:
            target = actuators[i % len(actuators)]
            add_inferred(m, target, "linkage", "mounted_to")
            
    for p in power:
        if p.id not in connected_ids:
            for c in controllers:
                add_inferred(p, c, "power", "electrically_connected")
            for a in actuators:
                add_inferred(p, a, "power", "electrically_connected")
                
    for c in controllers:
        if c.id not in connected_ids:
            for e in electronic:
                add_inferred(c, e, "signal", "electrically_connected")

    # NetworkX Validations
    isolated = list(nx.isolates(G))
    if isolated:
        warnings.append(f"Found {len(isolated)} isolated components with no connections.")
        
    try:
        power_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('label') == 'power']
        power_G = nx.DiGraph(power_edges)
        cycles = list(nx.simple_cycles(power_G))
        if cycles:
            warnings.append(f"Detected {len(cycles)} cycle(s) in power delivery! This could represent a short circuit or infinite loop.")
    except Exception as e:
        warnings.append(f"Cycle detection failed: {e}")

    # Build Assembly Tree
    assembly_tree = {"Robot": {"children": {}}}
    for c in components:
        if c.assembly_parent:
            # Simple 1-level for now
            if c.assembly_parent not in assembly_tree["Robot"]["children"]:
                assembly_tree["Robot"]["children"][c.assembly_parent] = {"children": {}}
            assembly_tree["Robot"]["children"][c.assembly_parent]["children"][c.name] = {"id": c.id}
        else:
            assembly_tree["Robot"]["children"][c.name] = {"id": c.id}

    # Filter out extremely low confidence edges
    final_connections = [c for c in connections if c.confidence >= 0.80]
    
    if len(final_connections) < len(connections):
        warnings.append(f"Filtered {len(connections) - len(final_connections)} edges below 0.80 confidence threshold.")

    return BuildGraphResponse(
        connections=final_connections,
        components=components,
        assembly_tree=assembly_tree,
        canonical_map=canonical_map,
        isolated_nodes=isolated,
        low_confidence_edges=low_confidence_edges,
        warnings=warnings
    )

