import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from llm import invoke_yantra_ai
from netlist_to_skidl import run_erc_on_netlist

router = APIRouter()

# --- Models ---
class SchematicRequest(BaseModel):
    query: str
    designData: Optional[Dict[str, Any]] = None

class ERCIssueDTO(BaseModel):
    severity: str
    message: str
    component_id: Optional[str] = None
    net_name: Optional[str] = None

class PowerBudgetDTO(BaseModel):
    total_mA: int
    margin_pct: int
    runtime_hrs: float
    warnings: List[str]

class ConfidenceDTO(BaseModel):
    subsystems: Dict[str, int]
    overall: int

class AssumptionDTO(BaseModel):
    category: str
    description: str
    impact: str

class DecisionDTO(BaseModel):
    step: str
    component_id: Optional[str]
    reason: str

class NetMember(BaseModel):
    componentId: str
    pinName: str

class IntermediateNet(BaseModel):
    name: str
    railType: Optional[str] = None
    netClass: Optional[str] = None
    members: List[NetMember]

class IntermediateSchematic(BaseModel):
    components: List[Dict[str, Any]]
    nets: List[IntermediateNet]

class SchematicResponse(BaseModel):
    netlist: Dict[str, Any]
    elements: List[Dict[str, Any]]
    erc_issues: List[ERCIssueDTO]
    pre_erc_issues: List[ERCIssueDTO]
    power_budget: PowerBudgetDTO
    confidence: ConfidenceDTO
    assumptions: List[str]
    structured_assumptions: List[AssumptionDTO] = []
    decision_trace: List[DecisionDTO] = []
    generation_hash: str
    fallback_used: bool

# --- Helper Functions ---
def _get_kb_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "knowledgebase"))

def load_parts_db():
    try:
        with open(os.path.join(_get_kb_dir(), "parts-db.json"), "r") as f:
            return json.load(f)
    except Exception:
        return []

def load_templates():
    try:
        with open(os.path.join(_get_kb_dir(), "subsystem-templates.json"), "r") as f:
            return json.load(f)
    except Exception:
        return []

def extract_json(text: str) -> dict:
    import re
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return {}

# --- Pipeline Steps ---

def step1_extract_spec(design_data, query):
    """Step 1: Use designData if available, else fallback."""
    if design_data and design_data.get("subsystems"):
        return {"subsystems": design_data["subsystems"], "bom": design_data.get("bom", [])}
    # Naive fallback parsing
    return {"subsystems": [], "bom": [], "query": query}

def step2_match_template(spec, templates):
    """Step 2: Match to template."""
    query_str = json.dumps(spec).lower()
    for t in templates:
        for kw in t.get("keywords", []):
            if kw in query_str:
                return t
    return templates[0] if templates else None

def step3_resolve_components(spec, template, parts_db):
    """Step 3: Resolve parts and assign designators."""
    resolved = []
    assumptions = []
    structured_assumptions = []
    decision_trace = []
    designator_counters = {}
    
    def add_comp(part_id, subsystem):
        part = next((p for p in parts_db if p["id"] == part_id), None)
        if not part: return None
        
        prefix = "U"
        if part["category"] == "motor": prefix = "M"
        elif part["category"] == "sensor": prefix = "S"
        elif part["category"] == "power": prefix = "PS"
        elif "driver" in part["category"]: prefix = "U_DRV"
        elif part["category"] == "microcontroller": prefix = "U_MCU"
        
        designator_counters[prefix] = designator_counters.get(prefix, 0) + 1
        des = f"{prefix}{designator_counters[prefix]}"
        
        comp_id_full = f"{part_id}_{des}"
        comp = {
            "id": comp_id_full,
            "partId": part_id,
            "designator": des,
            "label": part["name"],
            "subsystem": subsystem,
            "pins": part.get("pins", [])
        }
        resolved.append(comp)
        
        decision_trace.append({
            "step": "Resolve Component",
            "component_id": comp_id_full,
            "reason": f"Selected {part['name']} for subsystem {subsystem}"
        })
        
        # 3b: Auto-inject support components
        for supp in part.get("support_components", []):
            if supp.get("mandatory"):
                supp_des = f"C_{des}_{supp['placement']}"
                resolved.append({
                    "id": supp_des,
                    "partId": supp["type"],
                    "designator": supp_des,
                    "label": f"{supp['value']} {supp['type']}",
                    "subsystem": subsystem,
                    "pins": [{"name": "1", "net": supp['placement'].split('-')[0]}, {"name": "2", "net": supp['placement'].split('-')[1]}],
                    "is_support": True
                })
                assumptions.append(f"Injected mandatory {supp['value']} {supp['type']} for {des} ({supp['placement']})")
                structured_assumptions.append({
                    "category": "Support Component",
                    "description": f"Injected mandatory {supp['value']} {supp['type']} for {des} ({supp['placement']})",
                    "impact": "Required for electrical stability"
                })
                decision_trace.append({
                    "step": "Inject Support",
                    "component_id": supp_des,
                    "reason": f"Mandatory support for {des} on {supp['placement']}"
                })
                
        # Phase 6: Connector Auto-Injection
        # If component is external (motor or sensor), inject a connector
        if part["category"] in ["motor", "sensor"]:
            num_pins = len(part.get("pins", []))
            conn_des = f"J_{des}"
            conn_pins = [{"name": str(i+1), "type": p["type"], "original_pin": p["name"]} 
                         for i, p in enumerate(part.get("pins", []))]
            resolved.append({
                "id": conn_des,
                "partId": f"Conn_01x{num_pins:02d}",
                "designator": conn_des,
                "label": f"Connector for {des}",
                "subsystem": "Interface",
                "pins": conn_pins,
                "is_support": True,
                "is_connector": True,
                "target_comp_id": comp_id_full
            })
            assumptions.append(f"Injected connector {conn_des} (1x{num_pins}) for external component {des}")
            structured_assumptions.append({
                "category": "Interface",
                "description": f"Injected connector {conn_des} (1x{num_pins}) for external component {des}",
                "impact": "Allows physical connection to off-board component"
            })
            decision_trace.append({
                "step": "Inject Connector",
                "component_id": conn_des,
                "reason": f"Auto-injected for external {part['category']} {des}"
            })
            
        return comp

    if template:
        assumptions.append(f"Matched template: {template['name']}")
        structured_assumptions.append({
            "category": "Architecture",
            "description": f"Matched template: {template['name']}",
            "impact": "Determined base components and architecture"
        })
        decision_trace.append({
            "step": "Match Template",
            "component_id": None,
            "reason": f"Query matched keywords for {template['name']}"
        })
        add_comp(template.get("power", "buck_converter"), "Power")
        add_comp(template.get("mcu", "arduino_uno"), "Control")
        for act in template.get("actuators", []):
            for _ in range(act.get("count_default", 1)):
                add_comp(act.get("default_part"), "Actuation")
        for sen in template.get("sensors", []):
            for _ in range(sen.get("count_default", 1)):
                add_comp(sen.get("default_part"), "Sensing")

    return resolved, assumptions, structured_assumptions, decision_trace

def step4_propagate_power_rails(resolved, parts_db_index, mcu_logic_voltage=None):
    """
    Step 4: Real rail propagation from resolved power components.
    Returns: (rails, new_assumptions)
    """
    rails = {}
    new_assumptions = []
    
    for comp in resolved:
        if comp.get("is_support"): continue
        pdb = parts_db_index.get(comp.get("partId", ""))
        if not pdb or pdb.get("category") != "power": continue
        for out_rail in pdb.get("output_rails", []):
            v = out_rail.get("voltage")
            assumed = out_rail.get("assumed", False)
            if assumed:
                if mcu_logic_voltage is not None:
                    v = mcu_logic_voltage
                    new_assumptions.append(
                        f"Rail {out_rail['rail']} voltage derived from MCU logic voltage ({v}V)")
                else:
                    new_assumptions.append(
                        f"Rail {out_rail['rail']} output voltage assumed {v}V "
                        f"(adjustable part — override if different)")
            rails[out_rail["rail"]] = {
                "voltage":         v,
                "max_current_mA":  out_rail.get("max_current_mA"),
                "source_comp_id":  comp["id"],
                "connected_components": [],
                "assumed":         assumed
            }
            
    if "GND" not in rails:
        rails["GND"] = {"voltage": 0, "max_current_mA": None,
                        "source_comp_id": None, "connected_components": []}
                        
    for comp in resolved:
        for pin in comp.get("pins", []):
            rail = pin.get("rail")
            if rail and rail in rails:
                rails[rail]["connected_components"].append(comp["id"])
                
    return rails, new_assumptions

def step5_allocate_mcu_pins(resolved, parts_db):
    """
    Step 5 (Phase 4b): Protocol Engine & MCU pin allocation.
    Reserves protocol groups (I2C, SPI, UART, CAN) instead of random pins.
    """
    allocations = {}
    mcus = [c for c in resolved if "MCU" in c["designator"]]
    if not mcus: return allocations
    mcu = mcus[0]
    
    INTERFACE_RULES = {
        "i2c": ["SDA", "SCL"],
        "spi": ["MOSI", "MISO", "SCK", "CS"],
        "uart": ["TX", "RX"],
        "can": ["CAN_TX", "CAN_RX"]
    }
    
    # Collect MCU pins
    available_pins = []
    protocol_pins = {} # { "SDA": ["I2C_0_SDA", "SDA"], ... }
    
    for p in mcu.get("pins", []):
        ptype = p["type"]
        pname = p["name"]
        if ptype in ["digital_io", "digital_in", "digital_out", "analog_in"]:
            available_pins.append(pname)
            # Match against protocol rules (naive match for now)
            for proto, expected_pins in INTERFACE_RULES.items():
                for ep in expected_pins:
                    if ep in pname:
                        protocol_pins.setdefault(ep, []).append(pname)
                        
    pin_idx = 0
    
    for comp in resolved:
        if comp["id"] == mcu["id"] or comp.get("is_support"): continue
        comp_alloc = {}
        
        # Determine if this component uses a protocol
        comp_pins = [p["name"] for p in comp.get("pins", [])]
        used_protocols = []
        for proto, expected_pins in INTERFACE_RULES.items():
            if any(ep in comp_pins for ep in expected_pins):
                used_protocols.append((proto, expected_pins))
                
        for pin in comp.get("pins", []):
            pname = pin["name"]
            ptype = pin["type"]
            
            allocated = False
            # Check protocol matches
            for proto, expected_pins in used_protocols:
                if pname in expected_pins:
                    # Try to find a matching MCU protocol pin
                    candidates = protocol_pins.get(pname, [])
                    for cand in candidates:
                        if cand in available_pins:
                            comp_alloc[pname] = cand
                            available_pins.remove(cand)
                            allocated = True
                            break
                    
            # Fallback to general GPIO
            if not allocated and ("digital" in ptype or "analog" in ptype):
                if available_pins:
                    comp_alloc[pname] = available_pins[0]
                    available_pins.pop(0)
                    
        if comp_alloc:
            allocations[comp["id"]] = comp_alloc
            
    return allocations

def step6_validate_pin_compatibility(resolved, rails, parts_db_index, allocations):
    """
    Step 6: Real Pre-ERC structural validation.
    Runs before SKiDL. Returns List[dict] with severity/message/component_id/net_name.
    """
    issues = []
    
    # Check 1: Voltage domain mismatches
    mcu_logic_v = None
    for comp in resolved:
        pdb = parts_db_index.get(comp.get("partId", ""))
        if pdb and pdb.get("category") == "microcontroller":
            mcu_logic_v = pdb.get("logic_voltage")
            break
            
    if mcu_logic_v is not None:
        for comp in resolved:
            if comp.get("is_support"): continue
            pdb = parts_db_index.get(comp.get("partId", ""))
            if not pdb: continue
            for pin in pdb.get("pins", []):
                pin_logic_v = pin.get("logic_V")
                if pin_logic_v and pin_logic_v != mcu_logic_v:
                    if pin.get("type") in ["digital_in", "digital_out", "digital_io"]:
                        issues.append({
                            "severity": "warning",
                            "message": (f"{comp['designator']} pin {pin['name']} expects "
                                       f"{pin_logic_v}V logic but MCU operates at {mcu_logic_v}V "
                                       f"— level shifter may be required"),
                            "component_id": comp["id"]
                        })
                        break

    # Check 2: Power rail with no source
    for comp in resolved:
        if comp.get("is_support"): continue
        pdb = parts_db_index.get(comp.get("partId", ""))
        if not pdb: continue
        for pin in pdb.get("pins", []):
            if pin.get("type") == "power":
                rail = pin.get("rail")
                if rail and rail not in rails:
                    issues.append({
                        "severity": "error",
                        "message": (f"{comp['designator']} requires rail '{rail}' "
                                   f"but no power source for this rail was resolved"),
                        "component_id": comp["id"]
                    })

    # Check 3: electrical_constraints from parts-db
    for comp in resolved:
        pdb = parts_db_index.get(comp.get("partId", ""))
        if not pdb: continue
        for constraint in pdb.get("electrical_constraints", []):
            if constraint["rule"] == "must_connect":
                pin_name = constraint["pin"]
                target_rail = constraint.get("target_rail")
                alloc = allocations.get(comp["id"], {})
                if pin_name not in alloc and target_rail not in rails:
                    issues.append({
                        "severity": constraint.get("severity", "error"),
                        "message": constraint.get("message",
                            f"{comp['designator']} pin {pin_name} constraint not satisfied"),
                        "component_id": comp["id"]
                    })

    # Check 4: Floating required inputs
    for comp in resolved:
        if comp.get("is_support"): continue
        pdb = parts_db_index.get(comp.get("partId", ""))
        if not pdb: continue
        alloc = allocations.get(comp["id"], {})
        for pin in pdb.get("pins", []):
            if pin.get("type") == "digital_in" and pin["name"] not in alloc:
                if pin["name"] not in ("MS1", "MS2", "MS3", "M0", "M1", "M2", "AD0"):
                    issues.append({
                        "severity": "warning",
                        "message": (f"{comp['designator']} pin {pin['name']} is a required input "
                                   f"with no driver assigned"),
                        "component_id": comp["id"]
                    })

    return issues

def classify_net(net_name: str) -> str:
    """Phase 5: Classify nets for layout/routing tools."""
    name = net_name.upper()
    if "GND" in name: return "ground"
    if any(p in name for p in ["+5V", "+3V3", "VDD", "VCC", "VIN", "VMOT"]): return "power"
    if any(p in name for p in ["M+", "M-", "OUTA", "OUTB", "MOTOR"]): return "motor"
    if any(p in name for p in ["SDA", "SCL"]): return "i2c"
    if any(p in name for p in ["MOSI", "MISO", "SCK", "CS"]): return "spi"
    if any(p in name for p in ["TX", "RX"]): return "uart"
    if any(p in name for p in ["CAN_H", "CAN_L", "CAN_TX", "CAN_RX"]): return "can"
    if "USB" in name or "D+" in name or "D-" in name: return "usb"
    return "signal"

def step7_generate_netlist_llm(resolved, allocations, parts_db_subset, query, use_llm=True):
    """Step 7: Single LLM call for constrained netlist generation."""
    nets = []
    
    # We will build a naive netlist deterministically if fallback is forced, 
    # otherwise invoke the LLM
    if not use_llm:
        # Fallback: Just wire power and ground for demonstration
        pwr_members = []
        gnd_members = []
        for c in resolved:
            for p in c.get("pins", []):
                if p["type"] == "power": pwr_members.append({"componentId": c["id"], "pinName": p["name"]})
                if p["type"] == "ground": gnd_members.append({"componentId": c["id"], "pinName": p["name"]})
        
        if pwr_members: nets.append({"name": "+5V", "railType": "power", "members": pwr_members})
        if gnd_members: nets.append({"name": "GND", "railType": "ground", "members": gnd_members})
        
        # Wire allocated MCU pins
        for comp_id, allocs in allocations.items():
            for comp_pin, mcu_pin in allocs.items():
                mcu_id = [c["id"] for c in resolved if "MCU" in c["designator"]][0]
                nets.append({
                    "name": f"NET_{comp_id}_{comp_pin}",
                    "railType": "signal",
                    "members": [
                        {"componentId": comp_id, "pinName": comp_pin},
                        {"componentId": mcu_id, "pinName": mcu_pin}
                    ]
                })
        
        for net in nets:
            net["netClass"] = classify_net(net.get("name", ""))
            
        return {"components": resolved, "nets": nets}, True
        
    system_prompt = """You are Yantraa's Schematic Netlist Engine.
Given a list of exact components, their parts-db pins, and pre-allocated MCU pins, output the final LogicalNetlist.
OUTPUT FORMAT JSON:
{
  "nets": [
    { "name": "GND", "railType": "ground", "members": [{"componentId": "U_MCU1", "pinName": "GND"}] }
  ]
}
CRITICAL RULES:
1. ONLY use componentIds from the provided list.
2. ONLY use pinNames explicitly listed in the provided components.
3. Obey the pre-allocated MCU pins exactly.
"""
    
    prompt_data = {
        "query": query,
        "components": [{ "id": c["id"], "part": c["partId"], "pins": [p["name"] for p in c.get("pins",[])] } for c in resolved],
        "mcu_pin_allocations": allocations
    }
    
    try:
        res = invoke_yantra_ai(json.dumps(prompt_data), system_prompt, "json_object")
        netlist_data = extract_json(res)
        final_nets = netlist_data.get("nets", nets)
    except Exception as e:
        print(f"LLM Netlist error: {e}")
        # fallback
        return step7_generate_netlist_llm(resolved, allocations, parts_db_subset, query, use_llm=False)

    for net in final_nets:
        net["netClass"] = classify_net(net.get("name", ""))

    return {"components": resolved, "nets": final_nets}, False

def step8_run_erc(netlist):
    """Step 8: Run ERC via SKiDL adapter."""
    issues = run_erc_on_netlist(netlist)
    return [ERCIssueDTO(**i) for i in issues]

def step9_analyze_power(resolved, parts_db_index, rails):
    """
    Step 9: Real power budget. Per-rail summation. Returns (PowerBudgetDTO, erc_additions[]).
    erc_additions are rail-overload ERC errors to be merged into the main erc_issues list.
    """
    rail_draw = {}
    total_mA = 0
    erc_additions = []
    warnings = []

    for comp in resolved:
        if comp.get("is_support"): continue
        pdb = parts_db_index.get(comp.get("partId", ""))
        if not pdb: continue
        draw = pdb.get("current_draw_mA", 0)
        total_mA += draw
        # Attribute draw to first power rail this component is connected to
        attributed = False
        for pin in pdb.get("pins", []):
            if pin.get("type") == "power" and pin.get("rail"):
                rail = pin["rail"]
                rail_draw[rail] = rail_draw.get(rail, 0) + draw
                attributed = True
                break
        if not attributed:
            rail_draw["UNKNOWN"] = rail_draw.get("UNKNOWN", 0) + draw

    # Check each rail for overload
    margin_pct = 100
    for rail_name, draw in rail_draw.items():
        rail_info = rails.get(rail_name, {})
        max_mA = rail_info.get("max_current_mA")
        if max_mA is not None:
            pct = int((draw / max_mA) * 100)
            if draw > max_mA:
                warnings.append(f"OVERLOAD: {rail_name} draws {draw}mA > {max_mA}mA supply")
                erc_additions.append({
                    "severity": "error",
                    "message": f"Rail '{rail_name}' overloaded: {draw}mA load > {max_mA}mA capacity",
                    "net_name": rail_name
                })
            elif pct > 80:
                warnings.append(f"{rail_name} at {pct}% capacity ({draw}/{max_mA}mA)")
            margin_pct = min(margin_pct, 100 - pct)

    # Runtime — look for battery_mAh in resolved parts
    battery_mAh = None
    for comp in resolved:
        pdb = parts_db_index.get(comp.get("partId", ""))
        if pdb and pdb.get("battery_mAh"):
            battery_mAh = pdb["battery_mAh"]
            break
    if battery_mAh is None:
        battery_mAh = 2000
        warnings.append("No battery found in design — runtime assumes 2000mAh")

    return (
        PowerBudgetDTO(
            total_mA=total_mA,
            margin_pct=max(0, min(100, margin_pct)),
            runtime_hrs=round(battery_mAh / max(1, total_mA), 1),
            warnings=warnings
        ),
        erc_additions
    )

def step10_layout_and_compile(netlist):
    """Step 10: Compile LogicalNetlist to SchematicElement[] view."""
    elements = []
    
    # Very crude grid layout
    x, y = 100, 100
    for idx, comp in enumerate(netlist.get("components", [])):
        if comp.get("is_support"): continue
        
        comp_el = {
            "id": f"el_{comp['id']}",
            "type": "ic_block", # using the new systematic default
            "x": x,
            "y": y,
            "color": "#1a1a1a",
            "strokeWidth": 1.5,
            "partId": comp["partId"],
            "componentId": comp["id"],
            "designator": comp["designator"],
            "pinStubs": comp.get("pins", [])
        }
        elements.append(comp_el)
        
        x += 200
        if x > 800:
            x = 100
            y += 200
            
    # For wires, we just create straight lines between the blocks for now in the compiler
    # A real auto-router is complex, we just connect centers
    for net in netlist.get("nets", []):
        members = net.get("members", [])
        if len(members) < 2: continue
        
        # Connect first member to all others
        src = members[0]
        src_el = next((e for e in elements if e.get("componentId") == src["componentId"]), None)
        if not src_el: continue
        
        for tgt in members[1:]:
            tgt_el = next((e for e in elements if e.get("componentId") == tgt["componentId"]), None)
            if not tgt_el: continue
            
            elements.append({
                "id": f"wire_{net['name']}_{tgt['componentId']}",
                "type": "wire",
                "color": "#eab308" if net.get("railType") == "power" else "#3b82f6",
                "strokeWidth": 1.5,
                "netId": net["name"],
                "points": [
                    {"x": src_el["x"] + 40, "y": src_el["y"] + 40}, # rough center
                    {"x": tgt_el["x"] + 40, "y": tgt_el["y"] + 40}
                ]
            })
            
    return elements

def step11_score_confidence(resolved, erc_issues, pre_erc_issues, fallback_used, parts_db_index, assumptions):
    """
    Step 11: Real confidence scoring.
    Derives score per subsystem based on ERC/Pre-ERC issues, unknown parts, and fallback.
    """
    subsystems = {"Power": 100, "Control": 100, "Actuation": 100, "Sensing": 100, "Unknown": 100}
    
    # Base penalty for fallback
    if fallback_used:
        for k in subsystems: subsystems[k] -= 10
        assumptions.append("Fallback netlist generator used (-10% confidence overall)")

    # Group components by subsystem
    comp_to_sub = {c["id"]: c.get("subsystem", "Unknown") for c in resolved}

    # Penalize for ERC errors
    all_issues = erc_issues + pre_erc_issues
    for issue in all_issues:
        penalty = 15 if issue.get("severity") == "error" else 5
        cid = issue.get("component_id")
        sub = comp_to_sub.get(cid, "Unknown")
        subsystems[sub] = max(0, subsystems[sub] - penalty)
        
    # Penalize for unknown logic voltage / unknown parts
    for comp in resolved:
        if comp.get("is_support"): continue
        pdb = parts_db_index.get(comp.get("partId", ""))
        sub = comp.get("subsystem", "Unknown")
        if not pdb:
            subsystems[sub] = max(0, subsystems[sub] - 20)
            assumptions.append(f"Component {comp['designator']} not in parts-db (-20% to {sub})")

    # Filter out unused subsystems from scoring
    active_subs = set(comp_to_sub.values())
    subsystems = {k: v for k, v in subsystems.items() if k in active_subs}

    if not subsystems:
        return ConfidenceDTO(subsystems={}, overall=0)

    overall = sum(subsystems.values()) // len(subsystems)
    return ConfidenceDTO(
        subsystems=subsystems,
        overall=overall
    )

# --- Endpoint ---

@router.post("/api/schematic/generate", response_model=SchematicResponse)
async def generate_schematic(request: Request, payload: SchematicRequest):
    try:
        parts_db = load_parts_db()
        templates = load_templates()
        
        pdb_index = {p["id"]: p for p in parts_db}
        
        # 1. Extract Spec
        spec = step1_extract_spec(payload.designData, payload.query)
        
        # 2. Match Template
        template = step2_match_template(spec, templates)
        
        # 3. Resolve Components
        resolved, assumptions = step3_resolve_components(spec, template, parts_db)
        
        # Determine MCU logic voltage early for rails
        mcu_logic_v = None
        for comp in resolved:
            pdb = pdb_index.get(comp.get("partId", ""))
            if pdb and pdb.get("category") == "microcontroller":
                mcu_logic_v = pdb.get("logic_voltage")
                break
        
        # 4. Propagate Rails
        rails, rail_assumptions = step4_propagate_power_rails(resolved, pdb_index, mcu_logic_v)
        assumptions.extend(rail_assumptions)
        
        # 5. Allocate MCU Pins
        allocations = step5_allocate_mcu_pins(resolved, parts_db)
        
        # 6. Pre-ERC Validation
        pre_erc_issues_raw = step6_validate_pin_compatibility(resolved, rails, pdb_index, allocations)
        pre_erc_issues = [ERCIssueDTO(**i) for i in pre_erc_issues_raw]
        
        # 7. Generate Netlist
        netlist, fallback_used = step7_generate_netlist_llm(resolved, allocations, parts_db, payload.query)
        
        # 8. Run ERC
        erc_issues_raw = run_erc_on_netlist(netlist, parts_db)
        erc_issues = [ERCIssueDTO(**i) for i in erc_issues_raw]
        
        # 9. Power Analysis
        power_budget, power_ercs = step9_analyze_power(resolved, pdb_index, rails)
        for e in power_ercs:
            erc_issues.append(ERCIssueDTO(**e))
        
        # 10. Layout & Compile
        elements = step10_layout_and_compile(netlist)
        
        # 11. Confidence Scoring
        confidence = step11_score_confidence(
            resolved, 
            [e.dict() for e in erc_issues], 
            [e.dict() for e in pre_erc_issues], 
            fallback_used, 
            pdb_index, 
            assumptions
        )
        
        # Generate Hash
        hash_input = json.dumps(spec) + str(len(parts_db))
        gen_hash = hashlib.md5(hash_input.encode()).hexdigest()
        
        return SchematicResponse(
            netlist=netlist,
            elements=elements,
            erc_issues=erc_issues,
            pre_erc_issues=pre_erc_issues,
            power_budget=power_budget,
            confidence=confidence,
            assumptions=assumptions,
            generation_hash=gen_hash,
            fallback_used=fallback_used
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/parts-db")
async def get_parts_db():
    return load_parts_db()
