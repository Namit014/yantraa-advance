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
    error: Optional[str] = None

def extract_json(text: str) -> dict:
    """Extract and parse JSON object from LLM response text."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from markdown code block
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try finding the outermost { } block
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not extract JSON from LLM response: {text[:300]}")

from llm import DEFAULT_MODEL

def _safe_llm_call(prompt: str, system_prompt: str, response_format: str = "json_object", model: str = DEFAULT_MODEL) -> str:
    try:
        res = invoke_yantra_ai(
            prompt=prompt,
            system_prompt=system_prompt,
            response_format=response_format,
            model=model
        )
        if res.startswith("OpenRouter API Error") or res.startswith("Error calling AI"):
            print(f"[api/design] Warning: API call failed. Falling back to default model...")
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
        router_data = extract_json(raw_router)
        
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
}

CRITICAL: Your response must be valid JSON only. No markdown, no backticks, no explanation text before or after the JSON object. Start your response with { and end with }."""

    synthesis_prompt = f"""{component_graph_text}RETRIEVED COMPONENTS:
{rag_results}

USER REQUEST:
{query}"""

    synthesis_data = {}
    try:
        raw_synthesis = _safe_llm_call(synthesis_prompt, synthesis_system, response_format="json_object")
        synthesis_data = extract_json(raw_synthesis)
    except Exception as e:
        print(f"[api/design] Phase 3 Synthesis parsing failed: {e}")
        try:
            with open("debug_synthesis.txt", "w", encoding="utf-8") as debug_file:
                debug_file.write(raw_synthesis)
        except Exception:
            pass
        return DesignResponse(
            subsystems=[],
            connections=[],
            bom=[],
            missing=[],
            validation=[],
            cad_available=False,
            cad_url=None,
            cad_urls=[],
            chat_reply=None,
            error="Design generation failed — LLM returned unparseable output. Try rephrasing your request or try again."
        )

    # ─── PHASE 4: Assemble Final Response & CAD Checks ───────────────────────
    print("[api/design] Phase 4: Finalizing assembly...")
    subsystems = synthesis_data.get("subsystems", [])
    connections = synthesis_data.get("connections", [])
    bom = synthesis_data.get("bom", [])
    missing = synthesis_data.get("missing", [])
    validation = synthesis_data.get("validation", [])

    # Ensure validation is a list
    if validation is None:
        validation = []

    # Normalize BOM
    if not bom and "bill_of_materials" in synthesis_data:
        bom = synthesis_data["bill_of_materials"]
    if bom is None:
        bom = []

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

    # Run basic local validation pass
    local_validation = []
    
    # 1. Flag any subsystem with 0 components
    for sub in subsystems:
        if not sub.get("components"):
            local_validation.append({
                "type": "warning",
                "message": f"Subsystem '{sub.get('name', 'Unknown')}' has no components."
            })
            
    # 2. Flag any component that appears in connections but is missing from subsystems
    all_comp_ids = set()
    for sub in subsystems:
        for comp in sub.get("components", []):
            if comp.get("id"):
                all_comp_ids.add(str(comp.get("id")))
                
    for conn in normalized_connections:
        c_from = conn.get("from")
        c_to = conn.get("to")
        if c_from and str(c_from) not in all_comp_ids:
            local_validation.append({
                "type": "error",
                "message": f"Connection source '{c_from}' is not defined in any subsystem components."
            })
        if c_to and str(c_to) not in all_comp_ids:
            local_validation.append({
                "type": "error",
                "message": f"Connection target '{c_to}' is not defined in any subsystem components."
            })
            
    # 3. Flag if no power subsystem is present
    has_power_sub = any("power" in str(sub.get("name", "")).lower() for sub in subsystems)
    if not has_power_sub:
        local_validation.append({
            "type": "warning",
            "message": "No dedicated power subsystem detected in the design."
        })
        
    validation.extend(local_validation)

    # Check CAD availability based on query
    from cad_registry import get_known_cads
    known_cads = get_known_cads()
    
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
    # Use dynamic API URLs so that they are served cleanly through main.py
    cad_urls = [f"/api/cad/{f}" for f in matched_cads]
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
        cad_urls=cad_urls,
        error=None
    )
