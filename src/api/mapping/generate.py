import os
import sys
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import re
import time
import networkx as nx
from .pipeline import MappingPipeline

router = APIRouter()

class RawComponent(BaseModel):
    id: str
    name: str
    category: str
    description: str = ""
    connects_to: List[str] = []
    quantity: int = 1
    partNumber: Optional[str] = None
    evidence_text: Optional[str] = None  # Added to support new pipeline

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

# ─── Fuzzy match ─────────────────────────────────────────────────────────────
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


# ─── Protocol Resolution Engine ───────────────────────────────────────────────
# Maps category-pair combinations to specific engineering protocols.
# Generic "signal" is ONLY used as a last-resort unknown fallback.

# Keywords in component name → preferred protocol
_NAME_PROTOCOL_MAP = [
    # CAN / CAN-FD
    (["can", "canbus", "can-fd", "canfd"],             "CAN"),
    # EtherCAT
    (["ethercat"],                                      "EtherCAT"),
    # Modbus
    (["modbus", "modbus-rtu", "modbus-tcp"],            "Modbus"),
    # RS485
    (["rs485", "rs-485"],                               "RS485"),
    # RS232
    (["rs232", "rs-232"],                               "RS232"),
    # Ethernet / TCP-IP
    (["ethernet", "tcp", "rj45", "switch", "router"],  "Ethernet"),
    # UART
    (["uart", "serial"],                                "UART"),
    # USB
    (["usb"],                                           "USB"),
    # SPI
    (["spi"],                                           "SPI"),
    # I2C
    (["i2c"],                                           "I2C"),
    # PWM
    (["pwm", "servo"],                                  "PWM"),
    # STEP/DIR (stepper motor control)
    (["stepper", "step_dir", "step/dir"],               "STEP_DIR"),
    # Encoder
    (["encoder", "resolver", "hall"],                   "ENCODER"),
]

# Category-pair matrix → protocol
_CATEGORY_PROTOCOL_MAP = {
    # Power domain
    ("power", "controller"):   "POWER",
    ("power", "driver"):       "POWER",
    ("power", "actuator"):     "POWER",
    ("power", "sensor"):       "POWER",
    ("power", "electronic"):   "POWER",
    ("power", "safety"):       "POWER",
    # Control commands: controller → driver
    ("controller", "driver"):   "CAN",       # Industrial default: CAN bus
    ("driver", "controller"):   "CAN",
    ("controller", "sensor"):   "I2C",       # Sensor feedback: I2C or UART
    ("sensor", "controller"):   "I2C",
    # Motion: driver → actuator
    ("driver", "actuator"):     "PWM",       # Driver → Motor default: PWM
    ("actuator", "driver"):     "ENCODER",   # Motor → Driver feedback: Encoder
    # Mechanical: actuator → mechanical
    ("actuator", "mechanical"): "mechanical",
    ("mechanical", "actuator"): "mechanical",
    # Safety
    ("controller", "safety"):   "safety",
    ("safety", "controller"):   "safety",
    ("safety", "driver"):       "safety",
    ("driver", "safety"):       "safety",
    # Electronic / generic module
    ("controller", "electronic"): "UART",
    ("electronic", "controller"): "UART",
    ("electronic", "electronic"): "SPI",
}


def resolve_protocol(src: RawComponent, dst: RawComponent) -> str:
    """
    Deterministically resolve the engineering protocol for a connection.
    Priority:
      1. Category-pair matrix (structurally deterministic — what layer is this?)
      2. Name-based keyword match (component-specific — does the name tell us the protocol?)
      3. 'UNKNOWN_SIGNAL_PROTOCOL' placeholder (never bare "signal")
    """
    # Priority 1: category-pair matrix (most structurally reliable)
    pair = (src.category.lower(), dst.category.lower())
    reverse_pair = (dst.category.lower(), src.category.lower())
    if pair in _CATEGORY_PROTOCOL_MAP:
        return _CATEGORY_PROTOCOL_MAP[pair]
    if reverse_pair in _CATEGORY_PROTOCOL_MAP:
        return _CATEGORY_PROTOCOL_MAP[reverse_pair]

    # Priority 2: name + description keyword scan (for protocol-specific components)
    combined_names = (src.name + " " + dst.name + " " + src.description + " " + dst.description).lower()
    for keywords, protocol in _NAME_PROTOCOL_MAP:
        if any(kw in combined_names for kw in keywords):
            return protocol

    # Priority 3: safe placeholder (explicit, never bare "signal")
    return "UNKNOWN_SIGNAL_PROTOCOL"


@router.post("/api/mapping/build-graph", response_model=BuildGraphResponse)
async def build_graph(request: BuildGraphRequest):
    components = request.components
    connections: List[ConnectionOut] = []
    seen = set()
    warnings = []
    
    # New Pipeline hook (Optional/Phased rollout)
    if components and any(c.evidence_text for c in components):
        raw_evidence = "\n".join(c.evidence_text for c in components if c.evidence_text)
        pipeline = MappingPipeline(raw_evidence)
        pipeline_results = pipeline.run()
        if pipeline_results.get("repairs"):
            warnings.extend(pipeline_results["repairs"])

    
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

    # ─── Primary pass — use RAG connects_to with protocol resolution ──────────
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

            # ── Protocol-aware label resolution ──────────────────────────────
            protocol = resolve_protocol(src_node, dst_node)

            if protocol == "POWER":
                add_conn(src_id, dst_id, "POWER")
                add_conn(src_id, dst_id, "GND")
                G.add_edge(src_id, dst_id, label="POWER")
            elif protocol == "mechanical":
                add_conn(src_id, dst_id, "mechanical")
                G.add_edge(src_id, dst_id, label="mechanical")
            elif protocol == "safety":
                add_conn(src_id, dst_id, "safety")
                G.add_edge(src_id, dst_id, label="safety")
            else:
                add_conn(src_id, dst_id, protocol)
                G.add_edge(src_id, dst_id, label=protocol)

    # ─── Secondary fallback — unconnected nodes ───────────────────────────────
    by_category = {}
    for c in components:
        by_category.setdefault(c.category, []).append(c)
        
    controllers = by_category.get("controller", [])
    actuators = by_category.get("actuator", [])
    sensors = by_category.get("sensor", [])
    mechanical = by_category.get("mechanical", [])
    power = by_category.get("power", [])
    electronic = by_category.get("electronic", [])
    drivers = by_category.get("driver", [])
    
    connected_ids = set()
    for c in connections:
        connected_ids.add(c.fromId)
        connected_ids.add(c.toId)

    # Controller → Driver: CAN (industrial default)
    for d in drivers:
        if d.id not in connected_ids:
            for c in controllers:
                proto = resolve_protocol(c, d)
                add_conn(c.id, d.id, proto)
                G.add_edge(c.id, d.id, label=proto)

    # Driver → Actuator: PWM
    for a in actuators:
        if a.id not in connected_ids:
            for d in drivers:
                proto = resolve_protocol(d, a)
                add_conn(d.id, a.id, proto)
                G.add_edge(d.id, a.id, label=proto)
            if not drivers:
                for c in controllers:
                    proto = resolve_protocol(c, a)
                    add_conn(c.id, a.id, proto)
                    G.add_edge(c.id, a.id, label=proto)
                 
    # Sensor → Controller: I2C / ENCODER
    for s in sensors:
        if s.id not in connected_ids:
            for c in controllers:
                proto = resolve_protocol(s, c)
                add_conn(s.id, c.id, proto)
                G.add_edge(s.id, c.id, label=proto)
                
    # Mechanical → nearest actuator: mechanical linkage
    for i, m in enumerate(mechanical):
        if m.id not in connected_ids and actuators:
            target = actuators[i % len(actuators)]
            add_conn(m.id, target.id, "mechanical")
            G.add_edge(m.id, target.id, label="mechanical")
            
    # Power → Controllers / Drivers / Actuators: POWER
    for p in power:
        if p.id not in connected_ids:
            for c in controllers:
                add_conn(p.id, c.id, "POWER")
                add_conn(p.id, c.id, "GND")
                G.add_edge(p.id, c.id, label="POWER")
            for d in drivers:
                add_conn(p.id, d.id, "POWER")
                add_conn(p.id, d.id, "GND")
                G.add_edge(p.id, d.id, label="POWER")
            for a in actuators:
                add_conn(p.id, a.id, "POWER")
                add_conn(p.id, a.id, "GND")
                G.add_edge(p.id, a.id, label="POWER")
                
    # Electronic modules → Controller: resolved per component
    for c in controllers:
        if c.id not in connected_ids:
            for e in electronic:
                proto = resolve_protocol(c, e)
                add_conn(c.id, e.id, proto)
                G.add_edge(c.id, e.id, label=proto)
                
    # Update connected_ids after secondary pass
    connected_ids.clear()
    for c in connections:
        connected_ids.add(c.fromId)
        connected_ids.add(c.toId)

    # ─── Post-processing: GND wires & Triple-Driver deduplication ────────────
    current_conns = list(connections)
    for c in current_conns:
        if c.label == "POWER":
            has_gnd = any(
                ex.fromId == c.fromId and ex.toId == c.toId and ex.label == "GND"
                for ex in connections
            )
            if not has_gnd:
                add_conn(c.fromId, c.toId, "GND")
                G.add_edge(c.fromId, c.toId, label="GND")
                
    # Resolve Triple-Driver Ambiguity
    for act in actuators:
        drives = [c for c in connections if c.toId == act.id and c.label == "PWM"]
        if len(drives) > 1:
            drivers_matched = [comp_map[d.fromId] for d in drives if d.fromId in comp_map]
            def score(n):
                l = n.name.lower()
                if "shield" in l or "driver" in l or "hat" in l: return 3
                if "arduino" in l or "raspberry" in l or "mega" in l or "esp" in l: return 2
                return 1
            drivers_matched.sort(key=score, reverse=True)
            if drivers_matched:
                best_driver = drivers_matched[0]
                for weaker in drivers_matched[1:]:
                    # Remove weaker drive
                    connections[:] = [
                        c for c in connections
                        if not (c.fromId == weaker.id and c.toId == act.id and c.label == "PWM")
                    ]
                    if G.has_edge(weaker.id, act.id):
                        G.remove_edge(weaker.id, act.id)
                    # Daisy chain via CAN (inter-driver communication)
                    existing = any(
                        (c.fromId == weaker.id and c.toId == best_driver.id) or
                        (c.toId == weaker.id and c.fromId == best_driver.id)
                        for c in connections
                    )
                    if not existing:
                        add_conn(weaker.id, best_driver.id, "CAN")
                        G.add_edge(weaker.id, best_driver.id, label="CAN")

    # ─── NetworkX Validations ─────────────────────────────────────────────────
    isolated = list(nx.isolates(G))
    if isolated:
        warnings.append(f"Found {len(isolated)} isolated components with no connections.")
        
    # Find simple cycles in power delivery
    try:
        power_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('label') == 'POWER']
        power_G = nx.DiGraph(power_edges)
        cycles = list(nx.simple_cycles(power_G))
        if cycles:
            warnings.append(f"Detected {len(cycles)} cycle(s) in power delivery! This could represent a short circuit or infinite loop.")
    except Exception as e:
        warnings.append(f"Cycle detection failed: {e}")

    # Warn about any remaining UNKNOWN_SIGNAL_PROTOCOL edges
    unknown_count = sum(1 for c in connections if c.label == "UNKNOWN_SIGNAL_PROTOCOL")
    if unknown_count > 0:
        warnings.append(
            f"{unknown_count} connection(s) could not be mapped to a specific protocol. "
            f"Labeled as UNKNOWN_SIGNAL_PROTOCOL. Add protocol keywords to component names/descriptions to resolve."
        )

    return BuildGraphResponse(
        connections=connections,
        isolated_nodes=isolated,
        warnings=warnings
    )
