import os
import sys
import time
import networkx as nx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import re

router = APIRouter()

class RawComponent(BaseModel):
    id: str
    name: str
    category: str
    description: str = ""
    connects_to: List[str] = []
    quantity: int = 1
    partNumber: Optional[str] = None

class ConnectionOut(BaseModel):
    id: str
    fromId: str
    toId: str
    label: str
    isUserEdited: bool = False

class BuildGraphRequest(BaseModel):
    components: List[RawComponent]

class BuildGraphResponse(BaseModel):
    connections: List[ConnectionOut]
    isolated_nodes: List[str]
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
    components = request.components
    connections: List[ConnectionOut] = []
    seen = set()
    warnings = []
    
    conn_counter = 0
    def add_conn(from_id: str, to_id: str, label: str):
        nonlocal conn_counter
        if not from_id or not to_id or from_id == to_id:
            return
        key1 = f"{from_id}->{to_id}->{label}"
        key2 = f"{to_id}->{from_id}->{label}"
        if key1 in seen or key2 in seen:
            return
        seen.add(key1)
        conn_counter += 1
        connections.append(ConnectionOut(
            id=f"conn-nx-{conn_counter}-{int(time.time() * 1000)}",
            fromId=from_id,
            toId=to_id,
            label=label,
            isUserEdited=False
        ))
        
    # Map for easy lookup
    comp_map = {c.id: c for c in components}
    
    # Init DiGraph
    G = nx.DiGraph()
    for c in components:
        G.add_node(c.id, category=c.category, label=c.name)

    # Primary pass - use RAG connects_to
    for rc in components:
        for target_name in rc.connects_to:
            # find to_node
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
            pair_key = f"{src_node.category}-{dst_node.category}"
            
            label = "connection"
            if "mechanical" in pair_key:
                label = "linkage"
            elif pair_key in ["actuator-controller", "controller-actuator"]:
                label = "drive"
            elif "sensor" in pair_key and "power" in pair_key:
                label = "power"
            elif "sensor" in pair_key:
                label = "data"
            elif "power" in pair_key:
                label = "power"
            elif "electronic" in pair_key:
                label = "signal"
                
            if label == "power":
                add_conn(src_id, dst_id, "power")
                add_conn(src_id, dst_id, "ground")
                G.add_edge(src_id, dst_id, label="power")
                G.add_edge(src_id, dst_id, label="ground")
            else:
                add_conn(src_id, dst_id, label)
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
        
    for a in actuators:
        if a.id not in connected_ids:
            for c in controllers:
                add_conn(c.id, a.id, "drive")
                G.add_edge(c.id, a.id, label="drive")
                
    for s in sensors:
        if s.id not in connected_ids:
            for c in controllers:
                add_conn(s.id, c.id, "data")
                G.add_edge(s.id, c.id, label="data")
                
    for i, m in enumerate(mechanical):
        if m.id not in connected_ids and actuators:
            target = actuators[i % len(actuators)]
            add_conn(m.id, target.id, "linkage")
            G.add_edge(m.id, target.id, label="linkage")
            
    for p in power:
        if p.id not in connected_ids:
            for c in controllers:
                add_conn(p.id, c.id, "power")
                add_conn(p.id, c.id, "ground")
                G.add_edge(p.id, c.id, label="power")
            for a in actuators:
                add_conn(p.id, a.id, "power")
                add_conn(p.id, a.id, "ground")
                G.add_edge(p.id, a.id, label="power")
                
    for c in controllers:
        if c.id not in connected_ids:
            for e in electronic:
                add_conn(c.id, e.id, "signal")
                G.add_edge(c.id, e.id, label="signal")
                
    # Update connected_ids after secondary pass
    connected_ids.clear()
    for c in connections:
        connected_ids.add(c.fromId)
        connected_ids.add(c.toId)

    # Post processing: Ground wires & Triple-Driver
    current_conns = list(connections)
    for c in current_conns:
        if c.label == "power":
            has_ground = any(existing.fromId == c.fromId and existing.toId == c.toId and existing.label == "ground" for existing in connections)
            if not has_ground:
                add_conn(c.fromId, c.toId, "ground")
                G.add_edge(c.fromId, c.toId, label="ground")
                
    # Resolve Triple-Driver Ambiguity
    for act in actuators:
        drives = [c for c in connections if c.toId == act.id and c.label == "drive"]
        if len(drives) > 1:
            drivers = [comp_map[d.fromId] for d in drives if d.fromId in comp_map]
            def score(n):
                l = n.name.lower()
                if "shield" in l or "driver" in l or "hat" in l: return 3
                if "arduino" in l or "raspberry" in l or "mega" in l or "esp" in l: return 2
                return 1
            drivers.sort(key=score, reverse=True)
            if drivers:
                best_driver = drivers[0]
                for weaker in drivers[1:]:
                    # Remove weaker drive
                    connections = [c for c in connections if not (c.fromId == weaker.id and c.toId == act.id and c.label == "drive")]
                    if G.has_edge(weaker.id, act.id):
                        G.remove_edge(weaker.id, act.id)
                        
                    # Daisy chain
                    existing = any((c.fromId == weaker.id and c.toId == best_driver.id) or (c.toId == weaker.id and c.fromId == best_driver.id) for c in connections)
                    if not existing:
                        add_conn(weaker.id, best_driver.id, "signal")
                        G.add_edge(weaker.id, best_driver.id, label="signal")

    # NetworkX Validations
    isolated = list(nx.isolates(G))
    if isolated:
        warnings.append(f"Found {len(isolated)} isolated components with no connections.")
        
    # Find simple cycles in power delivery
    try:
        power_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('label') == 'power']
        power_G = nx.DiGraph(power_edges)
        cycles = list(nx.simple_cycles(power_G))
        if cycles:
            warnings.append(f"Detected {len(cycles)} cycle(s) in power delivery! This could represent a short circuit or infinite loop.")
    except Exception as e:
        warnings.append(f"Cycle detection failed: {e}")

    return BuildGraphResponse(
        connections=connections,
        isolated_nodes=isolated,
        warnings=warnings
    )
