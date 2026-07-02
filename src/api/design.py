import os
import sys
import json
import re
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Ensure src/ is on sys.path
try:
    from llm import LLM_PROVIDER
    print(f"[DEBUG] Configured LLM Provider: {LLM_PROVIDER}")
except ImportError:
    pass

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from retriever import Retriever
from llm import invoke_yantra_ai
from assembly_engine import match_template, template_to_design_data, solve_assembly, validate_assembly

# S3 base URL from environment — used to build CAD URLs when local files are absent
S3_BUCKET_URL = os.getenv("S3_BUCKET_URL", "").rstrip("/")

router = APIRouter()

class Message(BaseModel):
    role: str
    content: str

class DesignRequest(BaseModel):
    query: Optional[str] = None
    messages: Optional[List[Message]] = None

class DesignResponse(BaseModel):
    subsystems: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]
    bom: List[Dict[str, Any]]
    missing: List[Dict[str, Any]]
    validation: List[Dict[str, Any]]
    cad_available: bool = False
    cad_url: Optional[str] = None
    cad_urls: List[str] = []
    extracted_components: List[str] = []
    chat_reply: Optional[str] = None
    assembly_transforms: List[Dict[str, Any]] = []
    assembly_mode: str = "side_by_side"

def extract_json(text: str) -> dict:
    """Extract and parse JSON object from LLM response text."""
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
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}

FULL_ASSEMBLY_KEYWORDS = ["full_system", "full-system", "assembly", "complete", "system"]

def pick_primary_cad(matched_files: list[str]) -> list[str]:
    # Prefer a full assembly file if one exists
    for f in matched_files:
        if any(kw in f.lower() for kw in FULL_ASSEMBLY_KEYWORDS):
            return [f]
    # Otherwise return only the first match
    return matched_files[:1] if matched_files else []

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

def _safe_llm_call(prompt: str, system_prompt: str, response_format: str = "json_object", model: Optional[str] = None) -> str:
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
        try:
            return invoke_yantra_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                response_format="text"
            )
        except Exception as e2:
            print(f"[api/design] Final LLM invocation failed: {e2}")
            import json
            
            # Create a clean, user-friendly error message
            friendly_err = "The AI service is currently busy or rate-limited. Please wait a moment and try your request again."
            
            return json.dumps({
                "subsystems": [],
                "connections": [],
                "bom": [],
                "missing": [],
                "validation": [{"type": "error", "message": friendly_err}],
                "cad_available": False,
                "cad_urls": [],
                "chat_reply": friendly_err
            })

async def run_synthesis_pipeline(request: Request, query: str, messages_list: Optional[List[Dict[str, str]]] = None) -> DesignResponse:
    # ─── PHASE 0 & 1: Router Agent (Intent + Search Terms) ────────────────────
    print("[api/design] Phase 1: Running Router Agent...")
    from cad_registry import get_known_cads
    known_cads_dict = get_known_cads()
    known_robot_types = list(known_cads_dict.keys())
    
    history_str = ""
    if messages_list:
        history_str = "CONVERSATION HISTORY:\n"
        for m in messages_list:
            role_name = "User" if m.get("role") == "user" else "Assistant"
            history_str += f"{role_name}: {m.get('content')}\n"
        history_str += "\n"
    router_system = f"""You are Yantraa, a friendly robotics design AI.
Analyze the user's input. Determine if it is a request to design a robot, select components, check connections, or perform technical robotics planning.
If it is conversational or unrelated to designing a specific robot system:
- Set "is_design_query" to false
- Write a friendly reply in "response"
- Leave "search_terms" empty.
- Set "closest_robot_type" to null

If it is a request to design or build a robot:
- Set "is_design_query" to true
- Leave "response" empty
- Identify hardware components needed and provide them as a list of strings in "search_terms" (e.g. ["Arduino Uno", "L298N Motor Driver", "LiPo Battery"])
- Match the user's requested robot to the closest available option from this exact list: {known_robot_types}. 
  If the user's intent strongly matches one of these (e.g. "I want a machine for carrying boxes" -> "agv" or "mobile robot", "I need to weld" -> "welding"), provide that exact string in "closest_robot_type". 
  If none match, set "closest_robot_type" to null.

Output ONLY valid JSON.
OUTPUT FORMAT:
{{
  "is_design_query": true,
  "response": "",
  "search_terms": ["term1", "term2"],
  "closest_robot_type": "agv"
}}"""

    router_prompt = f"User Input: {query}"
    if history_str:
        router_prompt = f"{history_str}User Input: {query}"
    
    is_design_query = True
    conversational_reply = ""
    components_to_search = []
    closest_robot_type = None
    
    try:
        raw_router = _safe_llm_call(router_prompt, router_system, response_format="json_object")
        router_data = extract_json(raw_router)
        
        is_design_query = router_data.get("is_design_query", True)
        conversational_reply = router_data.get("response", "")
        components_to_search = router_data.get("search_terms", [])
        closest_robot_type = router_data.get("closest_robot_type")
        
        if not isinstance(components_to_search, list):
            components_to_search = [query]
        if not components_to_search and is_design_query:
            components_to_search = [query]
    except Exception as e:
        print(f"[api/design] Phase 1 Router parsing failed: {e}")
        is_design_query = True
        components_to_search = [query]
        closest_robot_type = None

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
    # DISABLED per user request: We no longer intercept with modular HEBI templates, 
    # forcing the system to always fetch the full monolithic CAD model instead.
    # template = match_template(query)
    # if template:
    #     ...


    # ─── PHASE 2: Qdrant RAG Search ─────────────────────────────────────────────
    print("[api/design] Phase 2: Querying Qdrant Database...")
    retrieved_texts = []
    retriever_instance = request.app.state.retriever
    
    # Search for each term (limit to top 8 to prevent huge contexts)
    for search_term in components_to_search[:8]:
        try:
            points = retriever_instance.search(f"{search_term} pinout datasheet connection", top_k=3)
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
    print(f"[api/design] Looking for component_graph at: {os.path.abspath(cg_path)}")
    print(f"[api/design] Looking for hebi_components at: {os.path.abspath(hebi_path)}")
    try:
        if os.path.exists(cg_path):
            with open(cg_path, "r", encoding="utf-8") as f:
                cg_data = json.load(f)
                component_graph_text += "KNOWN COMPONENT GRAPH (from LeRobotDepot):\n" + json.dumps(cg_data) + "\n\n"
            print(f"[api/design] Loaded component_graph.json ({len(cg_data)} entries).")
        else:
            print(f"[api/design] WARNING: component_graph.json NOT FOUND — LLM will use general knowledge only.")
        if os.path.exists(hebi_path):
            with open(hebi_path, "r", encoding="utf-8") as f:
                hebi_data = json.load(f)
                minimized_hebi = [{"name": c.get("name"), "category": c.get("category")} for c in hebi_data.get("components", [])]
                component_graph_text += "AVAILABLE HEBI CAD COMPONENTS:\n" + json.dumps(minimized_hebi) + "\n\n"
            print(f"[api/design] Loaded hebi_components.json ({len(minimized_hebi)} entries).")
        else:
            print(f"[api/design] WARNING: hebi_components.json NOT FOUND — LLM will not have HEBI component list.")
    except Exception as e:
        print(f"[api/design] Could not load component graphs: {e}")

    # ─── PHASE 3: Synthesis Agent (Mapping + Connection + Validation) ────────
    print("[api/design] Phase 3: Running Synthesis Agent...")
    synthesis_system = """You are Yantraa, a friendly, concise, and technically sharp master robotics design AI. Your job is to assemble a complete, industrial-grade robot according to the USER REQUEST.
You must construct the robot by selecting individual components, organizing them into subsystems, mapping electrical/logic connections, and generating a Bill of Materials (BOM) with validation checks.

CRITICAL RULES:
- If the robot is a standard industrial arm, quadruped, humanoid, or mobile base, you MUST use HEBI component names from the AVAILABLE list below.
- If the user asks for a system that cannot be built with HEBI components (e.g. a flying robot, drone), you should generate standard generic custom components (e.g., `quadcopter_frame`, `brushless_motor`).
- Any custom component you generate MUST be included in the 'missing' array, e.g. `{"name": "quadcopter_frame"}` so the UI lets the user click to generate its CAD model.
- If you use custom components or define an assembly, you MUST include 'assembly_graph' in your JSON output detailing the parent-child relationships and connection ports.
- Output ONLY valid JSON in the exact structure requested.

ROBOTICS ARCHITECTURE STANDARDS (MANDATORY):
0. **EXTREME BREVITY**: You are running on a constrained model. Keep your output EXTREMELY short. Generate a maximum of 5-8 essential components total across all subsystems. DO NOT generate extensive wiring or every single sensor/resistor. Keep it minimal to prevent JSON truncation!
1. **Power Distribution (Trunk-and-Branch Topology)**: DO NOT run a dedicated power wire from the main base PSU to every single driver across the robot (this causes EMI). Instead, use a Trunk-and-Branch topology: Route a thick "Main Power Trunk" to a "Local Distribution Hub" or "Local Busbar" near each joint, and branch off to local drivers.
2. **Grounding Strategy**: Motor grounds, logic grounds, and sensor grounds MUST be separated and tied together only at a single "Star Ground Node" or "Common Ground Bus". Avoid ground loops.
3. **Emergency Stop (Hardware Cutoff)**: E-Stops MUST physically cut motor power. Generate an "E-Stop Button" connected to a "Safety Relay" or "Contactor". The Safety Relay MUST sit between the PSU and the Motor Drivers on the 24V/48V lines. Do NOT route E-Stop solely to the MCU.
4. **Encoder Feedback**: Every actuator MUST have explicit encoder/position feedback wiring. Use differential signals (RS-422) for noise immunity. Encoders MUST route back to the Controller or local Joint Controller.
5. **Power Supply Sizing & Fusing**: Size power supplies for PEAK stall current (2-3x nominal). Every individual branch from the PSU to a Driver MUST pass through a dedicated "Fuse" or "Circuit Breaker".
6. **Communication Architecture (Daisy-Chain)**: For complex robots, do NOT wire the MCU directly to every driver with a massive harness. You MUST enforce a Fieldbus Architecture (CAN Bus or EtherCAT). CRITICAL: Wire the Fieldbus in a Daisy-Chain topology (`Main MCU` -> `Joint 1 Controller` -> `Joint 2 Controller` -> `Joint 3 Controller`) to minimize long signal wires.
7. **Power Isolation**: Strictly separate Logic and Motor power. 24V/48V feeds motor drivers directly. 24V MUST feed a dedicated "DC-DC Buck Converter" which provides isolated 5V/3.3V logic power to the MCU and sensors.
8. **Dynamic Joint Naming**: You MUST explicitly name motors/actuators with their kinematic role based on the requested robot type (e.g., "J1 Base Rotation Motor", "J2 Arm Motor").
9. **Strict Connectivity**: 
   - Separate Power vs Signal. Clearly denote the `wire_type` as exactly one of: "power", "ground", "signal", "data", "pwm", "can".
   - CRITICAL: The `from` and `to` fields in the `connections` array MUST EXACTLY MATCH the `id` of the components defined in the `subsystems` array. DO NOT use the `name` field for connections. Do not invent IDs that do not exist in the components array.
10. **Actuator & Driver Rule**: Add ALL required motor drivers between controllers and motors. Motors must NEVER be connected directly to the battery. For every actuator, clearly show driver connection, power source, and feedback sensor connection.
11. **Complete Power Architecture**: Show Battery, Main Power Switch, Fuse protection, Reverse polarity protection, Current protection, Voltage regulators (12V, 5V, 3.3V), Power distribution rails, and Common ground connections. Ensure voltage compatibility: 12V devices receive 12V, 5V receive 5V, 3.3V receive 3.3V. Add level shifters wherever required.
12. **Complete Sensor Suite**: Include all sensors properly connected with exact names and interfaces (IMU, Ultrasonic sensor, Encoders, Limit switches, Status LEDs, plus any robot-specific sensors).
13. **Controller Architecture**: If multiple controllers are used, explicitly show UART/I2C/SPI connections, their purpose, and Master/slave relationship. Remove redundant controllers if they don't serve a clear purpose.
14. **Validation & Completion**: Verify every component connection and ensure no floating, incomplete, or ambiguous connections. Validate that the design can realistically be built without electrical conflicts. Follow real engineering best practices. Apply these rules to all future robot schematics regardless of robot type.
15. **Validation Report**: Use the `validation` array to output a validation report listing every improvement made (e.g., "Added reverse polarity protection") and assumptions used (e.g., "Assumed 24V for primary joint motors").
16. **Professional Engineering Documentation Quality**: Every component must have complete power, ground, and signal connections. Every signal path must be identifiable. Every voltage rail must be labeled. Every driver, regulator, sensor, and actuator must show realistic real-world wiring suitable for PCB design, debugging, and robot assembly. Target 9.5-10/10 electrical accuracy.
17. **Advanced Power Protection**: You MUST include a standard Protection Diode (e.g., 1N5408) for reverse-polarity protection in series with the main battery positive line, placed immediately after the Master Power Switch and before the Fuse. 
18. **Strict MCU Power Sourcing**: If a 5V Buck Converter is present, route the +5V output directly to the Arduino's 5V pin, NOT the VIN pin. If no 5V buck converter exists, power the Arduino via VIN using the 7-9V/12V source.
19. **Explicit Signal Documentation**: Explicitly specify the actual hardware pin label (e.g., D2, D3, D5) on the MCU for all signal connections. Do not rely on generic wiring.

OUTPUT FORMAT:
{{
  "subsystems": [
    {{
      "name": "subsystem name",
      "components": [
        {{
          "id": "unique_id",
          "name": "exact component name",
          "role": "what it does",
          "voltage": "operating voltage",
          "interface": "communication protocol"
        }}
      ]
    }}
  ],
  "connections": [
    {{
      "from": "component_id",
      "from_port": "exact_pin_name",
      "to": "component_id",
      "to_port": "exact_pin_name",
      "wire_type": "power | ground | signal | data | pwm | can",
      "relation": "powered_by | controlled_by | drives | communicates_with"
    }}
  ],
  "bom": [
    {{"id": "id", "name": "exact name", "qty": 1}}
  ],
  "missing": [
    {{"name": "component name"}}
  ],
  "validation": [
    {{"type": "error | warning", "message": "validation check"}}
  ],
  "assembly_graph": [
    {{"parent": "parent_id", "child": "child_id", "parent_port": "port_name", "child_port": "port_name"}}
  ],
  "chat_reply": "A brief warm conversational line acknowledging the design and describing what you built."
}}"""

    # Build user prompt
    user_prompt = f"USER REQUEST: {query}\n\n"
    if history_str:
        user_prompt = f"{history_str}USER REQUEST: {query}\n\n"
    if component_graph_text:
        user_prompt += f"{component_graph_text}\n"
    if rag_results:
        user_prompt += f"COMPONENT SPECS & DATA SHEETS:\n{rag_results}\n"

    print("[api/design] Invoking LLM...")
    try:
        res_text = _safe_llm_call(prompt=user_prompt, system_prompt=synthesis_system, response_format="json_object")
        print(f"[api/design] RAW LLM SYNTHESIS TEXT:\n{res_text}\n{'='*40}")
        data = extract_json(res_text)
    except Exception as e:
        print(f"[api/design] Error parsing LLM JSON: {e}")
        data = {}

    connections = data.get("connections", [])
    normalized_connections = []
    bom = data.get("bom", [])
    subsystems = data.get("subsystems", [])
    missing = data.get("missing", [])
    validation = data.get("validation", [])
    chat_reply = data.get("chat_reply")
    
    # Ensure every component has an ID
    if isinstance(subsystems, list):
        for sub in subsystems:
            if isinstance(sub, dict) and isinstance(sub.get("components"), list):
                for comp in sub.get("components", []):
                    if isinstance(comp, dict) and not comp.get("id"):
                        name = comp.get("name", "component")
                        comp["id"] = re.sub(r"[^a-zA-Z0-9]+", "_", name.lower()).strip("_")

    if isinstance(connections, list):
        for conn in connections:
            if not isinstance(conn, dict):
                continue
            c_from = conn.get("from") or conn.get("id_from") or conn.get("from_id")
            c_to = conn.get("to") or conn.get("id_to") or conn.get("to_id")
            if c_from and c_to:
                normalized_connections.append({
                    "from": str(c_from),
                    "from_port": str(conn.get("from_port") or "IO1"),
                    "to": str(c_to),
                    "to_port": str(conn.get("to_port") or "IO1"),
                    "wire_type": str(conn.get("wire_type") or "signal"),
                    "relation": conn.get("relation", "connected_to"),
                    "protocol": conn.get("protocol", "DC")
                })

    # Check CAD availability based on query
    cad_available = False
    cad_url = None
    assembly_transforms = []
    
    from cad_registry import get_known_cads
    known_cads = get_known_cads()
    
    # Extract all text from BOM and subsystems to match against
    matched_cads = set()
    
    # New Intelligence: PRIORITIZE the entire CAD model using closest_robot_type mapped by the LLM Router
    if closest_robot_type and closest_robot_type.lower() in known_cads:
        print(f"[api/design] Router mapped query to semantic alias '{closest_robot_type}'. Matching FULL CAD automatically.")
        matched_cads.add(known_cads[closest_robot_type.lower()])
        
    # Check each BOM item and subsystem ONLY IF we didn't find the entire CAD model
    if not matched_cads:
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

    # Universal CAD Scraper Fallback
    if not matched_cads:
        print(f"[api/design] No CAD matched locally. Triggering fallback scraper for '{query}'...")
        try:
            from scraper.cad_scraper import scrape_missing_component
            scraped_filename = await scrape_missing_component(query)
            if scraped_filename:
                matched_cads.add(scraped_filename)
        except Exception as e:
            print(f"[api/design] CAD scraper failed: {e}")

    # LAST OPTION: Try to match any word in the query against known_cads
    if not matched_cads:
        print("[api/design] Last option fallback: fuzzy matching words in query to robot cads")
        query_words = set(query.lower().split())
        for key, filename in known_cads.items():
            key_words = set(key.lower().split())
            if query_words & key_words: # intersection
                matched_cads.add(filename)
                break

    primary_cads = pick_primary_cad(list(matched_cads))
    
    # ── CAD URL builder ────────────────────────────────────────────────────
    frontend_public_cad = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "public", "cad"))

    def _build_cad_url(filename: str) -> str:
        """Build a CAD URL: prefer local /api/cad/ endpoint, fall back to S3 via index."""
        local_path = os.path.join(frontend_public_cad, filename)
        kb_search = os.path.abspath(os.path.join(_src_dir, "..", "knowledgebase"))
        import glob as _glob
        kb_matches = _glob.glob(os.path.join(kb_search, "**", filename), recursive=True)
        if kb_matches or os.path.exists(local_path):
            print(f"[api/design] CAD served via local backend: /api/cad/{filename}")
            return f"/api/cad/{filename}"
        if S3_BUCKET_URL:
            from cad_registry import get_s3_url
            return get_s3_url(filename, S3_BUCKET_URL)
        print(f"[api/design] WARNING: CAD file {filename!r} not found locally or in S3. Serving /api/cad/ path anyway.")
        return f"/api/cad/{filename}"

    cad_urls = [_build_cad_url(f) for f in primary_cads]
    cad_url = cad_urls[0] if cad_urls else None
    cad_available = len(cad_urls) > 0

    # ─── PHASE 5: Assembly Engine (Compute Transforms) ────────────────────────

    assembly_transforms = []
    assembly_mode = "side_by_side"

    
    # Try to build assembly graph from LLM synthesis data
    llm_assembly_graph = data.get("assembly_graph", [])
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
            
            valid_comp_urls = [t["cad_url"] for t in assembly_transforms if t.get("cad_url")]
            
            if not valid_comp_urls and cad_url:
                cad_urls = [cad_url]
                assembly_mode = "side_by_side" # Fallback to standard rendering
            else:
                cad_urls = valid_comp_urls
                
            cad_available = len(cad_urls) > 0
            if cad_urls and not cad_url:
                cad_url = cad_urls[0]
    
    # Analyze matched CADs
    extracted_components = set()
    try:
        from step_analyzer import analyze_step_file
        import glob
        cad_base_dir = os.path.join(_src_dir, "..", "knowledgebase")
        meta_dir = os.path.join(cad_base_dir, "CAD_Metadata")
        os.makedirs(meta_dir, exist_ok=True)
        
        for f in matched_cads:
            search_pattern = os.path.join(cad_base_dir, "**", f)
            found_files = glob.glob(search_pattern, recursive=True)
            if found_files:
                target_file = found_files[0]
                meta_res = analyze_step_file(target_file)
                if "components" in meta_res:
                    extracted_components.update(meta_res["components"])
                    
                # Save metadata
                meta_filename = f.replace(".STEP", "").replace(".step", "") + "_metadata.json"
                meta_path = os.path.join(meta_dir, meta_filename)
                with open(meta_path, "w", encoding="utf-8") as mf:
                    json.dump(meta_res, mf, indent=2)
                    
    except Exception as e:
        print(f"[api/design] CAD metadata extraction failed: {e}")
    
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
        assembly_mode=assembly_mode,
        chat_reply=chat_reply
    )

@router.post("/api/design", response_model=DesignResponse)
async def generate_robot_design(request: Request, design_request: DesignRequest):
    query = ""
    if design_request.query:
        query = design_request.query.strip()
    elif design_request.messages:
        query = design_request.messages[-1].content.strip()
        
    if not query:
        raise HTTPException(status_code=400, detail="Query or messages content cannot be empty.")
    
    dict_messages = []
    if design_request.messages:
        dict_messages = [{"role": m.role, "content": m.content} for m in design_request.messages]
        
    return await run_synthesis_pipeline(request, query, dict_messages)

from fastapi.responses import StreamingResponse
import asyncio

@router.post("/api/design/stream")
async def generate_robot_design_stream(request: Request, design_request: DesignRequest):
    messages = design_request.messages or []
    
    query = ""
    if design_request.query:
        query = design_request.query.strip()
    elif messages:
        query = messages[-1].content.strip()
        
    dict_messages = [{"role": m.role, "content": m.content} for m in messages]
    if not dict_messages and query:
        dict_messages = [{"role": "user", "content": query}]

    # Run semantic state classification to determine if we should generate the design
    CLASSIFY_SYSTEM_PROMPT = """You are a conversational analyzer. Analyze the chat history and output exactly either 'YES' or 'NO'.

A complete robot design specification requires the user to have explicitly discussed or answered questions about all three of these categories:
1. PAYLOAD or SCALE (e.g., maximum payload weight or footprint size)
2. ENVIRONMENT (e.g., indoor/outdoor, terrain type, or surface flatness)
3. NAVIGATION, MOUNTING, or STEERING (e.g., mobile base vs. stationary bench mount, LiDAR SLAM, magnetic tape guidance)

Check the messages history:
- Has the user explicitly discussed or answered questions about payload/scale? (Yes/No)
- Has the user explicitly discussed or answered questions about environment? (Yes/No)
- Has the user explicitly discussed or answered questions about navigation/mounting? (Yes/No)

If the user has explicitly discussed or answered questions about ALL THREE categories, output exactly: YES
Otherwise, output exactly: NO"""

    classify_prompt = f"Analyze this conversation history and reply with YES or NO:\n{json.dumps(dict_messages)}"
    try:
        classification = _safe_llm_call(
            prompt=classify_prompt,
            system_prompt=CLASSIFY_SYSTEM_PROMPT,
            response_format="text"
        ).strip().upper()
    except Exception as e:
        print(f"[api/design] Classification call failed: {e}")
        classification = "NO"
        
    should_generate = "YES" in classification
        
    async def event_generator():
        if not should_generate:
            CHAT_GUIDE_SYSTEM_PROMPT = """You are Yantraa, a friendly, concise, and technically sharp AI robotics co-pilot.
            
Your goal is to guide the user in designing their robot. Ask exactly ONE single question at a time to collect these missing details in sequence:
1. PAYLOAD (e.g., "What is the maximum payload capacity you are targeting?")
2. ENVIRONMENT (e.g., "Will this robot operate indoor on flat surfaces, or does it need to handle outdoor terrain?")
3. NAVIGATION or MOUNTING (e.g., "Will this robot be stationary/mounted, or does it need a mobile base?")

Follow these rules:
- If the user is greeting you (like "hello", "hi") or asking who you are, respond conversationally, introduce yourself as Yantraa, and ask them what they are planning to build today. Do NOT ask for payload or environment yet.
- If they have described their robot but payload/scale is missing, ask exactly ONE simple question about PAYLOAD.
- If payload is known but environment is missing, ask exactly ONE simple question about ENVIRONMENT.
- If payload and environment are known but navigation/mounting is missing, ask exactly ONE simple question about NAVIGATION or MOUNTING.

Keep your response brief and conversational. Ask ONLY ONE question in this turn. Do NOT ask multiple questions, and do NOT generate any design or components yet."""
            
            try:
                from llm import invoke_yantra_ai_chat_stream
                stream_messages = [{"role": m.role, "content": m.content} for m in messages]
                if not stream_messages and query:
                    stream_messages = [{"role": "user", "content": query}]
                token_gen = invoke_yantra_ai_chat_stream(
                    messages=stream_messages,
                    system_prompt=CHAT_GUIDE_SYSTEM_PROMPT,
                    temperature=0.7
                )
                for token in token_gen:
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'token', 'content': f'Error: {str(e)}'})}\n\n"
        else:
            try:
                yield f"data: {json.dumps({'type': 'status', 'content': 'Reading your prompt...' })}\n\n"
                await asyncio.sleep(0.6)
                
                yield f"data: {json.dumps({'type': 'status', 'content': 'Mapping subsystems...' })}\n\n"
                await asyncio.sleep(0.6)
                
                yield f"data: {json.dumps({'type': 'status', 'content': 'Selecting components...' })}\n\n"
                await asyncio.sleep(0.6)
                
                yield f"data: {json.dumps({'type': 'status', 'content': 'Building your BOM...' })}\n\n"
                
                final_messages = [{"role": m.role, "content": m.content} for m in messages]
                
                # Execute pipeline
                res_data = await run_synthesis_pipeline(request, query, final_messages)
                
                # Convert the DesignResponse model to dict
                res_dict = {
                    "subsystems": res_data.subsystems,
                    "connections": res_data.connections,
                    "bom": res_data.bom,
                    "missing": res_data.missing,
                    "validation": res_data.validation,
                    "cad_available": res_data.cad_available,
                    "cad_url": res_data.cad_url,
                    "cad_urls": res_data.cad_urls,
                    "extracted_components": res_data.extracted_components,
                    "chat_reply": res_data.chat_reply,
                    "assembly_transforms": res_data.assembly_transforms,
                    "assembly_mode": res_data.assembly_mode
                }
                
                yield f"data: {json.dumps({'type': 'final_design', 'design': res_dict })}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'status', 'content': f'Error: {str(e)}' })}\n\n"
                err_dict = {
                    'type': 'final_design',
                    'design': {
                        'subsystems': [],
                        'connections': [],
                        'bom': [],
                        'missing': [], 
                        'validation': [{'type': 'error', 'message': f'Generation failed: {str(e)}'}],
                        'chat_reply': f'Sorry, I encountered an error during generation: {str(e)}'
                    }
                }
                yield f"data: {json.dumps(err_dict)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
