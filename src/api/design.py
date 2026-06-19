import os
import sys
import json
import re
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Ensure src/ is on sys.path
_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from retriever import Retriever
from llm import invoke_yantra_ai
from assembly_engine import match_template, template_to_design_data, solve_assembly, validate_assembly

router = APIRouter()

class DesignRequest(BaseModel):
    query: str

class DesignResponse(BaseModel):
    subsystems: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]
    bom: List[Dict[str, Any]]
    missing: List[Dict[str, Any]]
    validation: List[Dict[str, Any]]
    cad_available: bool = False
    cad_url: Optional[str] = None
    cad_urls: List[str] = []
    chat_reply: Optional[str] = None
    assembly_transforms: List[Dict[str, Any]] = []
    assembly_mode: str = "side_by_side"

def _strip_markdown_json(text: str) -> str:
    """Remove ```json``` fences and find the JSON object/array."""
    cleaned = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        return cleaned[start : end + 1]
    arr_start = cleaned.find("[")
    arr_end = cleaned.rfind("]")
    if arr_start != -1 and arr_end != -1:
        return cleaned[arr_start : arr_end + 1]
    return cleaned.strip()

def _consolidate_bom(bom: List[Any]) -> List[Dict[str, Any]]:
    bom_map = {}
    for item in bom:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "").strip()
        if not name:
            continue
        qty = item.get("qty", 1)
        try:
            qty = int(qty)
        except Exception:
            qty = 1
        if name in bom_map:
            bom_map[name]["qty"] += qty
        else:
            bom_map[name] = {
                "id": item.get("id", name),
                "name": name,
                "qty": qty
            }
    return list(bom_map.values())


def _safe_llm_call(prompt: str, system_prompt: str, response_format: str = "json_object", model: str = "openrouter/owl-alpha") -> str:
    try:
        res = invoke_yantra_ai(
            prompt=prompt,
            system_prompt=system_prompt,
            response_format=response_format,
            model=model
        )
        if res.startswith("OpenRouter API Error") or res.startswith("Error calling AI"):
            print(f"[api/design] Warning: owl-alpha call failed. Falling back to default model...")
            res = invoke_yantra_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                response_format=response_format
            )
        return res
    except Exception as e:
        print(f"[api/design] LLM invocation failed: {e}. Retrying with plain text response...")
        return invoke_yantra_ai(
            prompt=prompt,
            system_prompt=system_prompt,
            response_format="text"
        )

@router.post("/api/design", response_model=DesignResponse)
async def generate_robot_design(request: Request, design_request: DesignRequest):
    query = design_request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    # ─── PHASE 0 & 1: Router Agent (Intent + Search Terms) ────────────────────
    print("[api/design] Phase 1: Running Router Agent...")
    router_system = """You are Yantraa, a friendly robotics design AI.
Analyze the user's input. Determine if it is a request to design a robot, select components, check connections, or perform technical robotics planning.
If it is conversational or unrelated to designing a specific robot system:
- Set "is_design_query" to false
- Write a friendly reply in "response"
- Leave "search_terms" empty.

If it is a request to design or build a robot:
- Set "is_design_query" to true
- Leave "response" empty
- Identify hardware components needed and provide them as a list of strings in "search_terms" (e.g. ["Arduino Uno", "L298N Motor Driver", "LiPo Battery"])

Output ONLY valid JSON.
OUTPUT FORMAT:
{
  "is_design_query": true,
  "response": "",
  "search_terms": ["term1", "term2"]
}"""

    router_prompt = f"User Input: {query}"
    
    is_design_query = True
    conversational_reply = ""
    components_to_search = []
    
    try:
        raw_router = _safe_llm_call(router_prompt, router_system, response_format="json_object")
        cleaned_router = _strip_markdown_json(raw_router)
        router_data = json.loads(cleaned_router)
        
        is_design_query = router_data.get("is_design_query", True)
        conversational_reply = router_data.get("response", "")
        components_to_search = router_data.get("search_terms", [])
        if not isinstance(components_to_search, list):
            components_to_search = [query]
        if not components_to_search and is_design_query:
            components_to_search = [query]
    except Exception as e:
        print(f"[api/design] Phase 1 Router parsing failed: {e}")
        is_design_query = True
        components_to_search = [query]

    if not is_design_query:
        print(f"[api/design] Intent is conversational. Reply: '{conversational_reply}'")
        return DesignResponse(
            subsystems=[],
            connections=[],
            bom=[],
            missing=[],
            validation=[],
            cad_available=False,
            cad_url=None,
            chat_reply=conversational_reply
        )
        
    print(f"[api/design] Search terms extracted: {components_to_search}")

    # ─── PHASE 1.5: Check Assembly Templates ──────────────────────────────────
    template = match_template(query)
    if template:
        print(f"[api/design] Template matched! Skipping LLM synthesis.")
        template_data = template_to_design_data(template)
        
        # Solve assembly transforms
        graph_nodes = template_data.get("_template_graph", [])
        assembly_graph = template_data.get("assembly_graph", [])
        assembly_transforms = solve_assembly(graph_nodes, assembly_graph)
        
        # Validate
        assembly_validation = validate_assembly(assembly_transforms)
        
        # Build CAD URLs from assembly transforms
        cad_urls = [t["cad_url"] for t in assembly_transforms]
        
        return DesignResponse(
            subsystems=template_data.get("subsystems", []),
            connections=template_data.get("connections", []),
            bom=_consolidate_bom(template_data.get("bom", [])),
            missing=template_data.get("missing", []),
            validation=template_data.get("validation", []) + assembly_validation,
            cad_available=len(cad_urls) > 0,
            cad_url=cad_urls[0] if cad_urls else None,
            cad_urls=cad_urls,
            assembly_transforms=assembly_transforms,
            assembly_mode="assembled"
        )

    # ─── PHASE 2: Qdrant RAG Search ─────────────────────────────────────────────
    print("[api/design] Phase 2: Querying Qdrant Database...")
    retrieved_texts = []
    retriever_instance = request.app.state.retriever
    
    # Search for each term (limit to top 8 to prevent huge contexts)
    for search_term in components_to_search[:8]:
        try:
            points = retriever_instance.search(search_term, top_k=2)
            for pt in points:
                if pt.payload and "text" in pt.payload:
                    retrieved_texts.append(f"## {search_term}\n{pt.payload['text']}")
        except Exception as e:
            print(f"[api/design] RAG search failed for '{search_term}': {e}")
            
    rag_results = "\n\n".join(retrieved_texts) if retrieved_texts else "(No component specifications retrieved from RAG. Use general specifications.)"

    # Load component graph if available
    component_graph_text = ""
    cg_path = os.path.join(_src_dir, "..", "knowledgebase", "Robots_MetaData", "component_graph.json")
    hebi_path = os.path.join(_src_dir, "..", "knowledgebase", "Robots_MetaData", "hebi_components.json")
    try:
        if os.path.exists(cg_path):
            with open(cg_path, "r", encoding="utf-8") as f:
                cg_data = json.load(f)
                component_graph_text += "KNOWN COMPONENT GRAPH (from LeRobotDepot):\n" + json.dumps(cg_data) + "\n\n"
        if os.path.exists(hebi_path):
            with open(hebi_path, "r", encoding="utf-8") as f:
                hebi_data = json.load(f)
                minimized_hebi = [{"name": c.get("name"), "category": c.get("category")} for c in hebi_data.get("components", [])]
                component_graph_text += "AVAILABLE HEBI CAD COMPONENTS:\n" + json.dumps(minimized_hebi) + "\n\n"
    except Exception as e:
        print(f"[api/design] Could not load component graphs: {e}")

    # ─── PHASE 3: Synthesis Agent (Mapping + Connection + Validation) ────────
    print("[api/design] Phase 3: Running Synthesis Agent...")
    synthesis_system = """You are Yantraa, a master robotics design AI. Your job is to design a complete robot assembly.
    
If the robot is a standard industrial arm, quadruped, humanoid, or mobile base, you MUST use HEBI component names from the AVAILABLE list below.
However, if the user asks for a system that cannot be built with HEBI components (e.g. a flying robot, drone, flight controller, propeller, plane, hexacopter, underwater ROV, etc.), you should generate standard generic custom components matching: `quadcopter_frame`, `brushless_motor`, `propeller`, `flight_controller`, `lipo_battery`.

ROBOT ASSEMBLY TEMPLATES (use these as guides):

1. ARTICULATED ARM (painting, welding, pick-and-place, cobot):
   - Actuators: A-2475-08 (base), A-2475-05 (joints x2-4)
   - Mounts: A-2221-01_Heavy_Right_Angle_Bracket_Inside (base mount), A-2220-01_Light_Right_Angle_Bracket (joint brackets), A-2218-01_Output_Tube_Adapter (link connectors)
   - End Effector: A-2055-01_Gripper_Assembly (gripping) or A-2143-02 (parallel gripper) or A-2292-01 (custom tool)
   - Electronics: A-2433-01_Motor_Driver_RJ45 (1 per actuator), A-2525-01 (battery)

2. DELTA ROBOT (fast pick-and-place, 3D printing):
   - Actuators: A-2475-05 x3 (parallel arms)
   - Mounts: A-2096-02_Six_Tube_Adapter (central hub), A-2220-01_Light_Right_Angle_Bracket x3
   - End Effector: A-2055-01_Gripper_Assembly
   - Electronics: A-2433-01_Motor_Driver_RJ45 x3

3. MOBILE ROBOT (wheeled, AGV):
   - Actuators: A-2438-02 (track/wheel drive x2-4)
   - Mounts: A-2227-01_Wheel_Adapter x4, A-2228-01_T-Slot_Right_Angle_Adapter (frame)
   - Electronics: A-2432-01 (IO board), A-2525-01 (battery)

4. QUADRUPED / DOG ROBOT:
   - Actuators: A-2475-05 x12 (3 per leg)
   - Mounts: A-2221-01_Heavy_Right_Angle_Bracket_Inside x8
   - Electronics: A-2433-01_Motor_Driver_RJ45 x4, A-2525-01

5. HUMANOID:
   - Actuators: A-2269-01_R-Series_Double_Shoulder x2, A-2475-08 x4, A-2475-05 x6
   - Mounts: A-2221-01_Heavy_Right_Angle_Bracket_Inside, A-2096-02_Six_Tube_Adapter
   - End Effector: A-2055-01_Gripper_Assembly x2

6. DRONE / FLYING ROBOT:
   - Chassis: quadcopter_frame
   - Actuators: brushless_motor (qty 4), propeller (qty 4)
   - Electronics: flight_controller, lipo_battery
   - Port mappings (parent_port on frame/motor -> child_port 'input_flange' on child):
     * quadcopter_frame -> brushless_motor (motor_fr, motor_fl, motor_br, motor_bl) at ports (motor_mount_fr, motor_mount_fl, motor_mount_br, motor_mount_bl)
     * brushless_motor -> propeller at port (shaft)
     * quadcopter_frame -> flight_controller at port (top_face)
     * quadcopter_frame -> lipo_battery at port (bottom_face)

RULES:
- For HEBI robots, use ONLY component names from the AVAILABLE list below.
- For flying robots/drones, use custom component names (`quadcopter_frame`, `brushless_motor`, `propeller`, `flight_controller`, `lipo_battery`) and define the assembly_graph.
- Any custom component you generate (e.g. quadcopter_frame, brushless_motor, lipo_battery) MUST be included in the 'missing' array, e.g. `{"name": "quadcopter_frame"}` so the UI lets the user click to generate its CAD model.
- If you use custom components or define an assembly, you MUST include 'assembly_graph' in your JSON output detailing the parent-child relationships and connection ports.
- Output ONLY valid JSON. No extra conversational text.
- Keep output SHORT: max 12 components, 10 connections.

OUTPUT FORMAT:
{
  "subsystems": [
    {
      "name": "subsystem name",
      "components": [
        {"id": "unique_id", "name": "component name", "role": "what it does", "voltage": "48V", "interface": "RJ45"}
      ]
    }
  ],
  "connections": [
    {"from": "id", "to": "id", "relation": "controlled_by", "protocol": "RJ45"}
  ],
  "bom": [
    {"id": "id", "name": "exact name", "qty": 1}
  ],
  "missing": [
    {"name": "component name"}
  ],
  "validation": [],
  "assembly_graph": [
    {"parent": "parent_id", "child": "child_id", "parent_port": "port_name", "child_port": "port_name"}
  ]
}"""

    # Build a compact component list to minimize token usage
    compact_components = []
    try:
        if os.path.exists(hebi_path):
            with open(hebi_path, "r", encoding="utf-8") as f:
                hebi_data = json.load(f)
                for comp in hebi_data.get("components", []):
                    compact_components.append(f"- {comp.get('name')} ({comp.get('category')})")
    except Exception:
        pass
    
    available_list = "\n".join(compact_components) if compact_components else "(No components loaded)"

    synthesis_prompt = f"""AVAILABLE HEBI COMPONENTS:
{available_list}

RETRIEVED SPECS:
{rag_results[:2000]}

USER REQUEST: {query}

Generate the robot assembly JSON now."""

    synthesis_data = {}
    try:
        raw_synthesis = _safe_llm_call(synthesis_prompt, synthesis_system, response_format="json_object")
        cleaned_synthesis = _strip_markdown_json(raw_synthesis)
        synthesis_data = json.loads(cleaned_synthesis)
    except Exception as e:
        print(f"[api/design] Phase 3 Synthesis parsing failed: {e}")
        with open("debug_synthesis.txt", "w", encoding="utf-8") as debug_file:
            debug_file.write(raw_synthesis)
        print(f"[api/design] RAW LLM OUTPUT WAS:\n{raw_synthesis[:1000]}...\n---")
        synthesis_data = {
            "subsystems": [{"name": "Pre-assembled System", "components": [{"id": "sys_1", "name": "Monolithic Robot System", "role": "Full assembly", "voltage": "N/A", "interface": "Standard"}]}],
            "connections": [],
            "bom": [{"id": "sys_1", "name": "Full Robot Assembly", "qty": 1}],
            "missing": [],
            "validation": [{"type": "warning", "message": "Standard BOM generated due to complex custom assembly. Reference CAD model for full physical details."}]
        }

    # ─── PHASE 4: Assemble Final Response & CAD Checks ───────────────────────
    print("[api/design] Phase 4: Finalizing assembly...")
    subsystems = synthesis_data.get("subsystems", [])
    connections = synthesis_data.get("connections", [])
    bom = synthesis_data.get("bom", [])
    missing = synthesis_data.get("missing", [])
    validation = synthesis_data.get("validation", [])

    # Normalize connections to have 'from' and 'to' fields
    normalized_connections = []
    if isinstance(connections, list):
        for conn in connections:
            if not isinstance(conn, dict):
                continue
            c_from = conn.get("from") or conn.get("id_from") or conn.get("from_id")
            c_to = conn.get("to") or conn.get("id_to") or conn.get("to_id")
            if c_from and c_to:
                normalized_connections.append({
                    "from": str(c_from),
                    "to": str(c_to),
                    "relation": conn.get("relation", "connected_to"),
                    "protocol": conn.get("protocol", "DC")
                })

    # Check CAD availability based on query
    cad_available = False
    cad_url = None
    
    known_cads = {
        "autonomous mobile": "autonomous_mobile_robot.stp",
        "agv": "AVGs_robot_cad.step",
        "cartesian": "cartesian_robot_cad.stp",
        "cobot": "Articulated_robot_cad.STEP",
        "delta": "DeltaRobot2.STEP",
        "painting": "Painting_Robot.step",
        "paint": "Painting_Robot.step",
        "spray": "Painting_Robot.step",
        "scara": "scara_robot_cad.stp",
        "welding": "welding_robot.stp",
        "weld": "welding_robot.stp",
        "articulated": "Articulated_robot_cad.STEP",
        "6 axis": "Articulated_robot_cad.STEP",
        "6-axis": "Articulated_robot_cad.STEP",
        "6 dof": "Articulated_robot_cad.STEP",
        "6-dof": "Articulated_robot_cad.STEP",
        "robotic arm": "Articulated_robot_cad.STEP",
        "robot arm": "Articulated_robot_cad.STEP",
        "pick and place": "Articulated_robot_cad.STEP",
        "pick-and-place": "Articulated_robot_cad.STEP",
        "pick things": "Articulated_robot_cad.STEP",
        "grab": "Articulated_robot_cad.STEP",
        "assembly line": "Articulated_robot_cad.STEP",
        "manipulation": "Articulated_robot_cad.STEP",
        "inspection": "inspection_robot_cad.STEP",
        "humanoid": "Robot_humanoid.step",
        "machine tending": "machine_tending_robot.stp",
        "in-pipe": "InPipeInspectionRobot.STEP",
        "in pipe": "InPipeInspectionRobot.STEP",
        "pipeline": "InPipeInspectionRobot.STEP",
        "corrosion": "InPipeInspectionRobot.STEP",
        "dog": "Full_System_A-2403-02.step",
        "robotic dog": "Full_System_A-2403-02.step",
        "quadruped": "Full_System_A-2403-02.step",
        "four leg": "Full_System_A-2403-02.step",
        "4 leg": "Full_System_A-2403-02.step",
    }
    
    # Dynamically add HEBI CADs
    try:
        if os.path.exists(hebi_path):
            with open(hebi_path, "r", encoding="utf-8") as f:
                hebi_data = json.load(f)
                for comp in hebi_data.get("components", []):
                    name = comp.get("name", "")
                    filename = comp.get("filename", "")
                    if name and filename:
                        # Add full name e.g. "a-2020-05"
                        known_cads[name.lower()] = filename
                        known_cads[name.lower().replace("-", " ")] = filename
    except Exception as e:
        print(f"[api/design] Error loading HEBI cads: {e}")
    
    # Extract all text from BOM and subsystems to match against
    matched_cads = set()
    
    # Check each BOM item
    if isinstance(bom, list):
        for b in bom:
            if not isinstance(b, dict):
                continue
            name = b.get("name", "").lower()
            desc = b.get("description", "").lower()
            search_text = f"{name} {desc}"
            
            for key, filename in known_cads.items():
                if key in search_text:
                    matched_cads.add(filename)
                
    # Also check subsystems as LLMs sometimes put components there but forget them in BOM
    if isinstance(subsystems, list):
        for sub in subsystems:
            if not isinstance(sub, dict):
                continue
            for comp in sub.get("components", []):
                if not isinstance(comp, dict):
                    continue
                name = comp.get("name", "").lower()
                role = comp.get("role", "").lower()
                search_text = f"{name} {role}"
                
                for key, filename in known_cads.items():
                    if key in search_text:
                        matched_cads.add(filename)
                
    # Fallback to monolithic robots if modular assembly yielded nothing
    if len(matched_cads) == 0:
        query_lower = query.lower()
        for key, filename in known_cads.items():
            if key in query_lower:
                matched_cads.add(filename)
            
    # Fallback to checking retrieved search points for robot names
    if not matched_cads:
        try:
            points = retriever_instance.search(query, top_k=5)
            for pt in points:
                payload = pt.payload or {}
                robot_val = payload.get("robot") or payload.get("robot_name") or payload.get("category")
                if robot_val and isinstance(robot_val, str):
                    r_lower = robot_val.lower()
                    for key, filename in known_cads.items():
                        if key.replace(" ", "_") in r_lower or key in r_lower:
                            matched_cads.add(filename)
        except Exception:
            pass

    cad_available = len(matched_cads) > 0
    # Use direct static URL since Next.js hosts the CAD files in public/cad/
    cad_urls = [f"/cad/{f}" for f in matched_cads]
    cad_url = cad_urls[0] if cad_urls else None
    
    # ─── PHASE 5: Assembly Engine (Compute Transforms) ────────────────────────
    assembly_transforms = []
    assembly_mode = "side_by_side"
    
    # Try to build assembly graph from LLM synthesis data
    llm_assembly_graph = synthesis_data.get("assembly_graph", [])
    if llm_assembly_graph:
        # LLM provided assembly graph — use it
        graph_nodes = []
        if isinstance(subsystems, list):
            for sub in subsystems:
                if not isinstance(sub, dict):
                    continue
                for comp in sub.get("components", []):
                    if not isinstance(comp, dict):
                        continue
                    graph_nodes.append({"id": comp["id"], "part": comp["name"]})
        
        assembly_transforms = solve_assembly(graph_nodes, llm_assembly_graph)
        if assembly_transforms:
            assembly_mode = "assembled"
            # Override cad_urls with assembly-computed URLs
            cad_urls = [t["cad_url"] for t in assembly_transforms]
            cad_available = True
            cad_url = cad_urls[0] if cad_urls else None
    
    print(f"[api/design] Pipeline complete. Subsystems={len(subsystems)}, Connections={len(normalized_connections)}, Validation Errors={len(validation)}")
    print(f"[api/design] Assembly mode: {assembly_mode}, CADs: {len(cad_urls)}")

    return DesignResponse(
        subsystems=subsystems,
        connections=normalized_connections,
        bom=_consolidate_bom(bom),
        missing=missing,
        validation=validation,
        cad_available=cad_available,
        cad_url=cad_url,
        cad_urls=cad_urls,
        assembly_transforms=assembly_transforms,
        assembly_mode=assembly_mode
    )
