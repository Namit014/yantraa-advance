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

class SchematicResponse(BaseModel):
    netlist: Dict[str, Any]
    elements: List[Dict[str, Any]]
    erc_issues: List[ERCIssueDTO]
    pre_erc_issues: List[ERCIssueDTO]
    power_budget: PowerBudgetDTO
    confidence: ConfidenceDTO
    assumptions: List[str]
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
        
        comp = {
            "id": f"{part_id}_{des}",
            "partId": part_id,
            "designator": des,
            "label": part["name"],
            "subsystem": subsystem,
            "pins": part.get("pins", [])
        }
        resolved.append(comp)
        
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
        return comp

    if template:
        assumptions.append(f"Matched template: {template['name']}")
        add_comp(template.get("power", "buck_converter"), "Power")
        add_comp(template.get("mcu", "arduino_uno"), "Control")
        for act in template.get("actuators", []):
            for _ in range(act.get("count_default", 1)):
                add_comp(act.get("default_part"), "Actuation")
        for sen in template.get("sensors", []):
            for _ in range(sen.get("count_default", 1)):
                add_comp(sen.get("default_part"), "Sensing")

    return resolved, assumptions

def step4_propagate_power_rails(resolved):
    """Step 4: Propagate rails (Mock)."""
    rails = {}
    for comp in resolved:
        if comp.get("is_support"): continue
        for pin in comp.get("pins", []):
            if pin["type"] == "power":
                rails[pin.get("rail", "+5V")] = {"voltage": 5.0}
    return rails

def step5_allocate_mcu_pins(resolved, parts_db):
    """Step 5: Deterministic MCU pin allocation."""
    allocations = {}
    mcus = [c for c in resolved if "MCU" in c["designator"]]
    if not mcus: return allocations
    mcu = mcus[0]
    
    available_pins = [p["name"] for p in mcu.get("pins", []) if p["type"] in ["digital_io", "digital_in", "digital_out", "analog_in"]]
    pin_idx = 0
    
    for comp in resolved:
        if comp["id"] == mcu["id"] or comp.get("is_support"): continue
        comp_alloc = {}
        for pin in comp.get("pins", []):
            if "digital" in pin["type"] or "analog" in pin["type"]:
                if pin_idx < len(available_pins):
                    comp_alloc[pin["name"]] = available_pins[pin_idx]
                    pin_idx += 1
        if comp_alloc:
            allocations[comp["id"]] = comp_alloc
            
    return allocations

def step6_validate_pin_compatibility(resolved, rails):
    """Step 6: Pre-ERC validation."""
    return [] # Mock pass

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
        return {"components": resolved, "nets": netlist_data.get("nets", nets)}, False
    except Exception as e:
        print(f"LLM Netlist error: {e}")
        # fallback
        return step7_generate_netlist_llm(resolved, allocations, parts_db_subset, query, use_llm=False)

def step8_run_erc(netlist):
    """Step 8: Run ERC via SKiDL adapter."""
    issues = run_erc_on_netlist(netlist)
    return [ERCIssueDTO(**i) for i in issues]

def step9_analyze_power(resolved, parts_db):
    """Step 9: Power budget analysis."""
    total_mA = sum(next((p.get("current_draw_mA", 0) for p in parts_db if p["id"] == c["partId"]), 0) for c in resolved if not c.get("is_support"))
    return PowerBudgetDTO(
        total_mA=total_mA,
        margin_pct=max(0, 100 - int((total_mA / 3000) * 100)), # mock 3A supply
        runtime_hrs=round(2000 / max(1, total_mA), 1), # mock 2000mAh battery
        warnings=[] if total_mA < 2500 else ["Approaching 3A supply limit"]
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

def step11_score_confidence(resolved, netlist, erc_issues):
    """Step 11: Confidence scoring."""
    score = 100 - (len(erc_issues) * 5)
    return ConfidenceDTO(
        subsystems={"Power": 95, "Control": 90, "Actuation": 85},
        overall=max(0, min(100, score))
    )

# --- Endpoint ---

@router.post("/api/schematic/generate", response_model=SchematicResponse)
async def generate_schematic(request: Request, payload: SchematicRequest):
    try:
        parts_db = load_parts_db()
        templates = load_templates()
        
        # 1. Extract Spec
        spec = step1_extract_spec(payload.designData, payload.query)
        
        # 2. Match Template
        template = step2_match_template(spec, templates)
        
        # 3. Resolve Components
        resolved, assumptions = step3_resolve_components(spec, template, parts_db)
        
        # 4. Propagate Rails
        rails = step4_propagate_power_rails(resolved)
        
        # 5. Allocate MCU Pins
        allocations = step5_allocate_mcu_pins(resolved, parts_db)
        
        # 6. Pre-ERC Validation
        pre_erc_issues = step6_validate_pin_compatibility(resolved, rails)
        
        # 7. Generate Netlist
        netlist, fallback_used = step7_generate_netlist_llm(resolved, allocations, parts_db, payload.query)
        
        # 8. Run ERC
        erc_issues = step8_run_erc(netlist)
        
        # 9. Power Analysis
        power_budget = step9_analyze_power(resolved, parts_db)
        
        # 10. Layout & Compile
        elements = step10_layout_and_compile(netlist)
        
        # 11. Confidence Scoring
        confidence = step11_score_confidence(resolved, netlist, erc_issues)
        
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
