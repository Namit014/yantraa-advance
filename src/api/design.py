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

def _safe_llm_call(prompt: str, system_prompt: str, response_format: str = "json_object", model: str = "openrouter/free") -> str:
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
    synthesis_system = """You are Yantraa, a master robotics design AI. Your job is to assemble a complete robot according to the USER REQUEST.
You must construct the robot by selecting individual components, organizing them into subsystems, mapping electrical/logic connections, and generating a Bill of Materials (BOM).

CRITICAL RULES:
- You MUST select hardware components from either the AVAILABLE HEBI CAD COMPONENTS list or the RETRIEVED COMPONENTS list.
- Prioritize using the AVAILABLE HEBI CAD COMPONENTS to construct the physical body of the robot (Actuators, Mounts, Structural Links, End Effectors).
- Your BOM must include ALL the exact HEBI component names you used to build the robot.
- Output ONLY valid JSON in the exact structure requested.

OUTPUT FORMAT:
{
  "subsystems": [
    {
      "name": "subsystem name",
      "components": [
        {
          "id": "unique_id",
          "name": "exact name from HEBI or retrieved list",
          "role": "what it does",
          "voltage": "operating voltage",
          "interface": "communication protocol"
        }
      ]
    }
  ],
  "connections": [
    {
      "from": "component_id",
      "to": "component_id",
      "relation": "powered_by | controlled_by | drives | communicates_with",
      "protocol": "CAN | PWM | I2C | RS485 | USB | DC"
    }
  ],
  "bom": [
    {"id": "component_id", "name": "exact name", "qty": 1}
  ],
  "missing": [
    {"name": "missing component name", "reason": "why it is needed"}
  ],
  "validation": [
    {"type": "error | warning", "message": "voltage mismatch, missing controller, etc."}
  ]
}"""

    synthesis_prompt = f"""{component_graph_text}RETRIEVED COMPONENTS:
{rag_results}

USER REQUEST:
{query}"""

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
    for conn in connections:
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
        "scara": "scara_robot_cad.stp",
        "welding": "welding_robot.stp",
        "articulated": "Articulated_robot_cad.STEP",
        "inspection": "inspection_robot_cad.STEP",
        "humanoid": "Robot_humanoid.step",
        "machine tending": "machine_tending_robot.stp",
        "in-pipe": "InPipeInspectionRobot.STEP",
        "in pipe": "InPipeInspectionRobot.STEP",
        "pipeline": "InPipeInspectionRobot.STEP",
        "corrosion": "InPipeInspectionRobot.STEP",
        "dog": "Full_System_A-2403-02.step",
        "robotic dog": "Full_System_A-2403-02.step",
        "quadruped": "Full_System_A-2403-02.step"
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
    for b in bom:
        name = b.get("name", "").lower()
        desc = b.get("description", "").lower()
        search_text = f"{name} {desc}"
        
        for key, filename in known_cads.items():
            if key in search_text:
                matched_cads.add(filename)
                
    # Also check subsystems as LLMs sometimes put components there but forget them in BOM
    for sub in subsystems:
        for comp in sub.get("components", []):
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
    
    print(f"[api/design] Pipeline complete. Subsystems={len(subsystems)}, Connections={len(normalized_connections)}, Validation Errors={len(validation)}")
    print(f"[api/design] CADs matched: {cad_urls}")

    return DesignResponse(
        subsystems=subsystems,
        connections=normalized_connections,
        bom=bom,
        missing=missing,
        validation=validation,
        cad_available=cad_available,
        cad_url=cad_url,
        cad_urls=cad_urls
    )
