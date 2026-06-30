"""
backend/api/connections/generate.py
POST /api/connections/generate

Accepts { components: [{id, name, type}], prompt: str, subsystems?: [...] }
1. For each component, queries Qdrant RAG for its pinout/connection data
2. Calls OpenRouter with RAG context
3. Returns structured JSON: { nodes, wires }
"""

import os
import sys
import json
import re
import requests
from dotenv import load_dotenv
from typing import List, Optional

# Import ERC module
from api.connections.erc import validate_and_fix_diagram, load_hardware_db

load_dotenv()
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# ── Path setup ─────────────────────────────────────────────────────────────────
_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# ── OpenRouter config ──────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Use a fast, reliable model for Yantra AI.
CONNECTIONS_MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/owl-alpha")

# ── Pydantic models ────────────────────────────────────────────────────────────

class ComponentIn(BaseModel):
    id: str
    name: str
    type: str = "other"

class SubsystemComponentIn(BaseModel):
    id: str
    name: str
    role: Optional[str] = None
    voltage: Optional[str] = None
    interface: Optional[str] = None

class SubsystemIn(BaseModel):
    name: str
    components: List[SubsystemComponentIn]

class GenerateRequest(BaseModel):
    components: List[ComponentIn]
    prompt: str
    subsystems: Optional[List[SubsystemIn]] = None


# ── Router ─────────────────────────────────────────────────────────────────────

router = APIRouter()


def _rag_search(query: str, top_k: int = 5) -> str:
    """Query Qdrant singleton for pinout context for a given component name."""
    try:
        from embedder import Embedder
        from vectordb import get_qdrant_client

        embedder = Embedder()
        vec = embedder.embed_text(query)

        client = get_qdrant_client()
        results = client.query_points(
            collection_name="yantra_knowledgebase",
            query=vec,
            limit=top_k,
        )
        texts = [p.payload.get("text", "") for p in results.points if p.payload]
        return "\n\n".join(texts[:3])
    except Exception as exc:
        # If RAG fails (empty DB, import error), return empty string gracefully
        print(f"[connections/generate] RAG search failed for '{query}': {exc}")
        return ""


async def _web_fallback_pinout_search(query: str) -> str:
    """Fallback to search the internet for component pinouts if local database is empty."""
    try:
        from scraper.search import search_web
        from scraper.pipeline import rank_urls, is_garbage_text, _url_cache, _save_url_cache
        from scraper.scraper import fetch_clean_text
        
        print(f"[connections/generate] Triggering web fallback for: {query}")
        urls = search_web(query, max_results=5)
        if not urls:
            return ""
        
        ranked_urls = rank_urls(urls)[:3]
        texts = []
        
        for url in ranked_urls:
            if url in _url_cache:
                continue
            text = await fetch_clean_text(url)
            if text and not is_garbage_text(text):
                texts.append(f"Source: {url}\n" + text)
                _url_cache.add(url)
                _save_url_cache(_url_cache)
            if len(texts) >= 2:
                break
                
        # Return truncated context
        return "\n\n---\n\n".join(texts)[:4000]
    except Exception as e:
        print(f"[connections/generate] Web fallback error: {e}")
        return ""


def _call_llm(system: str, user: str) -> str:
    """Call LLM unified from src/llm.py"""
    try:
        from llm import invoke_yantra_ai
    except ImportError:
        try:
            from src.llm import invoke_yantra_ai
        except ImportError:
            import sys
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
            from src.llm import invoke_yantra_ai
            
    return invoke_yantra_ai(
        prompt=user, 
        system_prompt=system, 
        response_format="json_object", 
        temperature=0.3
    )


def _strip_markdown_json(text: str) -> str:
    """Remove ```json``` fences and find the JSON object."""
    cleaned = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*", "", cleaned)
    # Find first { ... } block
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        return cleaned[start : end + 1]
    return cleaned.strip()


def _fallback_diagram(components: List[ComponentIn]) -> dict:
    """Fallback if LLM JSON fails."""
    return {"nodes": [], "wires": [], "erc_report": "Generation failed to parse properly. Please click Generate again to retry."}



@router.post("/api/connections/generate")
async def generate_connections(request: GenerateRequest):
    """
    Step 1: For each component, query Qdrant RAG for pinout data.
    Step 2: Call Gemini via OpenRouter with context + prompt.
    Step 3: Return structured node/wire JSON.
    """
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    # ── Step 1: RAG context + Hardware DB per component ─────────────────────────
    rag_contexts: List[str] = []
    hardware_db = load_hardware_db()
    
    if request.components:
        for comp in request.components[:12]:  # limit to avoid huge prompts
            # Check Hardware DB first
            comp_name_lower = comp.name.lower()
            hw_match = next((k for k in hardware_db.keys() if k in comp_name_lower or comp_name_lower in k), None)
            
            if hw_match:
                hw_info = hardware_db[hw_match]
                hw_ctx = f"## {comp.name} (from Hardware DB)\nExplicit Ports and Voltages: {json.dumps(hw_info['ports'])}"
                rag_contexts.append(hw_ctx)
                print(f"[connections/generate] Loaded DB info for {comp.name}")
            else:
                # Fallback to RAG
                ctx = _rag_search(f"{comp.name} pinout datasheet connections")
                
                if len(ctx) < 150: # If RAG context is empty or too short
                    print(f"[connections/generate] RAG insufficient for {comp.name}, scraping web...")
                    web_ctx = await _web_fallback_pinout_search(f"{comp.name} pinout wiring specifications")
                    if web_ctx:
                        ctx = web_ctx + "\n" + ctx
                        
                if ctx:
                    rag_contexts.append(f"## {comp.name}\n{ctx}")
    else:
        ctx = _rag_search(f"{request.prompt} robot components pinout connections datasheet", top_k=8)
        if ctx:
            rag_contexts.append(f"## RAG Context for: {request.prompt}\n{ctx}")

    rag_block = "\n\n".join(rag_contexts) if rag_contexts else ""

    # Grounding context from subsystems if RAG context is empty/insufficient
    grounding_block = ""
    if not rag_block:
        print("[connections/generate] RAG context is empty. Grounding with design subsystems.")
        if request.subsystems:
            subsystems_list = []
            for sub in request.subsystems:
                comp_strs = []
                for comp in sub.components:
                    comp_strs.append(f"  - Component: ID={comp.id}, Name={comp.name}, Role={comp.role or ''}, Voltage={comp.voltage or ''}, Interface={comp.interface or ''}")
                subsystems_list.append(f"Subsystem: {sub.name}\n" + "\n".join(comp_strs))
            grounding_block = "DESIGN SUBSYSTEM STRUCTURE FOR GROUNDING:\n" + "\n\n".join(subsystems_list)
        else:
            grounding_block = "(No detailed design subsystem grounding context available)"
    else:
        grounding_block = f"RAG PINOUT DATA:\n{rag_block}"

    # Load connection rules from connection_kb.py
    from connection_kb import CONNECTION_RULES, validate_connections
    serialized_rules = "\n".join(f"{idx + 1}. {rule}" for idx, rule in enumerate(CONNECTION_RULES))


    # ── Step 2: Build LLM prompt ───────────────────────────────────────────────
    if request.components:
        component_list = "\n".join(
            f"- id={c.id}, name={c.name}, type={c.type}" for c in request.components
        )
    else:
        component_list = "(No components provided. You MUST determine the necessary components based on the USER PROMPT and RAG PINOUT DATA. Invent logical IDs and names for them, and include them in the nodes array.)"

    system_prompt = (
        "You are an expert hardware engineer and circuit diagram generator. "
        "You produce ONLY valid JSON — no markdown, no explanation, no preamble. "
        "Your output must be parseable by json.loads()."
    )

    user_prompt = f"""Given these components and the user's prompt, generate a complete circuit connection diagram.

COMPONENTS:
{component_list}

USER PROMPT: {request.prompt}

GROUNDING CONTEXT:
{grounding_block}

CONNECTION RULES (you must follow these exactly):
{serialized_rules}

WIRE COLOR CONVENTION:
- power (3.3V/5V/12V): #FF4444
- ground: #888888
- control/signal/PWM: #FFD700
- data (I2C/SPI/UART): #4488FF
- sensor/feedback: #00FF00
- safety/e-stop: #FFFF00

NODE SHAPE RULES:
- Use "raspberry-pi" for Raspberry Pi boards
- Use "arduino-uno" for Arduino boards
- Use "esp32" for ESP32/ESP8266 modules
- Use "breadboard" for breadboards
- Use "ic-chip" for ICs, drivers, H-bridges
- Use "generic-board" for everything else

ROBOTICS STANDARDS & REQUIREMENTS:
- SENSORS & LOGICAL COMPLETENESS: If the prompt implies a standard robot (e.g. "2 wheel robot", "rover", "arm"), automatically include common necessary sensors (like ultrasonic sensors, IMU, encoders, limits) to make the design functionally complete. DO NOT omit core functional sensors.
- GRANULAR SCHEMATICS (CRITICAL): Generate highly detailed, granular wire-level schematics. Do not use abstract logical blocks for power or data if pin-level details are known. For Ethernet/EtherCAT, route distinct data channels (e.g. daisy-chaining ETH_IN to ETH_OUT) and route distinct power channels accurately.
- STRICTLY ELECTRICAL: DO NOT include purely mechanical brackets, adapters, tubes, or structural mounts in the diagram. Only electrical/electronic components (motors, controllers, sensors, power) are allowed.
- CORE ELECTRONICS: You MUST include the main microcontroller (e.g., Arduino/Raspberry Pi), required motor drivers (e.g., L298N or A4988) for any actuators provided, and a main power supply/battery.
- SEMANTIC LABELING: Assign role-based labels to EACH component. NEVER use generic duplicate names for multiple parts.
- SIGNAL ARCHITECTURE: Clearly separate and label Power lines, Signal lines, and Ground lines. ALWAYS use "feedback" type and "#00FF00" color for wires connected to sensors!
- MOTOR CONTROL: Enforce a strict 1:1 relationship between drivers and motors where appropriate.
- Layout Readability: Improve text readability by avoiding overlapping labels and maintaining uniform spacing. Distribute nodes using a cleaner hierarchical visual flow from left to right: Power -> Controller -> Drivers -> Motors.

Return ONLY this JSON structure (no markdown fences):
{{
  "nodes": [
    {{
      "id": string (use the component id from above),
      "label": string (human-readable name),
      "type": "microcontroller"|"sensor"|"motor"|"power"|"display"|"module"|"other",
      "shape": "raspberry-pi"|"arduino-uno"|"esp32"|"breadboard"|"ic-chip"|"generic-board",
      "x": number (canvas x, use this to create hierarchical flow: e.g., Power=100, Controller=400, Drivers=700, Motors=1000, Sensors=1300),
      "y": number (canvas y, maintain at least 300px vertical spacing between parallel components to avoid overlapping labels),
      "ports": [
        {{ "id": string, "label": string, "side": "top"|"bottom"|"left"|"right", "offsetPercent": number }}
      ]
    }}
  ],
  "wires": [
    {{
      "id": string,
      "from": {{ "nodeId": string, "portId": string }},
      "to": {{ "nodeId": string, "portId": string }},
      "color": string (hex),
      "label": string (e.g. "I2C SDA", "PWM", "GND", "Sensor Data"),
      "type": "power"|"ground"|"signal"|"data"|"pwm"|"feedback"|"safety"
    }}
  ]
}}

IMPORTANT:
- STRICT ACCURACY: Use EXACT pin names, voltage levels, and interfaces provided in the GROUNDING CONTEXT. DO NOT hallucinate or guess generic pin names if the true pinout is provided.
- Select ONLY the necessary components from the list above, or invent new ones if needed, to build the requested circuit. Do NOT include all components.
- Ports must match the physical pinout of the component.
- Include VCC, GND ports on every node.
- Wire colors MUST follow the convention above.
- Spread nodes so they do not overlap (minimum 250px gap).
- offsetPercent for ports must be between 5 and 95.
- PORT SPACING: Distribute ports evenly on each side using the formula
  offsetPercent = 100/(n+1) * k  where n=total ports on that side, k=1..n.
  Examples: 1 port→50, 2 ports→33,67, 3 ports→25,50,75, 4 ports→20,40,60,80.
  NEVER place two ports at the same offsetPercent on the same side.
- LAYOUT: Group power nodes at top, microcontrollers in the middle row,
  sensors and peripherals at the bottom. This makes right-angle wire routing
  cleaner and minimises crossings.
"""

    # ── Step 3: Call LLM ───────────────────────────────────────────────────────
    try:
        raw_response = _call_llm(system_prompt, user_prompt)
        json_str = _strip_markdown_json(raw_response)
        diagram = json.loads(json_str)

        # Validate minimal structure
        if "nodes" not in diagram or "wires" not in diagram:
            raise ValueError("Missing 'nodes' or 'wires' keys in LLM response")

        # Run Electrical Rule Checker (ERC) to auto-fix and validate
        diagram = validate_and_fix_diagram(diagram)
        
        # Run upstream connection validation rules as an extra safeguard
        from connection_kb import validate_connections
        valid_wires, logs = validate_connections(diagram["nodes"], diagram["wires"])
        diagram["wires"] = valid_wires
        if logs:
            print(f"[connections/generate] Upstream connections validated/repaired: {logs}")

        # Pass 2: Deep LLM ERC Validation
        from api.connections.erc import llm_validate_diagram
        print("[connections/generate] Starting Pass 2: Deep LLM ERC Validation...")
        validated_data = llm_validate_diagram(diagram, request.prompt)
        
        final_diagram = validated_data if ("nodes" in validated_data and "wires" in validated_data) else diagram
        erc_report = validated_data.get("erc_report", "Validation passed with no remarks.")
        
        # Ensure diagram structure is maintained
        if "nodes" not in final_diagram or "wires" not in final_diagram:
            final_diagram = diagram
            
        final_diagram["erc_report"] = erc_report
        print("[connections/generate] Pass 2 Complete.")
        
        return final_diagram

    except Exception as exc:
        print(f"[connections/generate] LLM/parse error: {exc}")
        print(f"[connections/generate] Falling back to layout algorithm")
        # Return a clean fallback rather than 500
        return _fallback_diagram(request.components)
