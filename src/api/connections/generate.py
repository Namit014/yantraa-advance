"""
backend/api/connections/generate.py
POST /api/connections/generate

Accepts { components: [{id, name, type}], prompt: str }
1. For each component, queries Qdrant RAG for its pinout/connection data
2. Calls OpenRouter (google/gemini-flash-1.5) with RAG context
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
# Gemini 2.5 Flash via OpenRouter
CONNECTIONS_MODEL = "openrouter/owl-alpha"

# ── Pydantic models ────────────────────────────────────────────────────────────


class ComponentIn(BaseModel):
    id: str
    name: str
    type: str = "other"


class GenerateRequest(BaseModel):
    components: List[ComponentIn]
    prompt: str


# ── Router ─────────────────────────────────────────────────────────────────────

router = APIRouter()


def _rag_search(query: str, top_k: int = 5) -> str:
    """Query Qdrant for pinout context for a given component name."""
    try:
        from embedder import Embedder
        from qdrant_client import QdrantClient

        qdrant_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../qdrant_data")
        )
        client = QdrantClient(path=qdrant_path)
        embedder = Embedder()
        vec = embedder.embed_text(query)

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


def _call_llm(system: str, user: str) -> str:
    """Call OpenRouter and return raw content string."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Yantra Connections",
    }
    payload = {
        "model": CONNECTIONS_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
    }
    resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


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
    """
    Generate a simple fallback diagram when the LLM fails or returns invalid JSON.
    Lays out nodes in a grid and connects them sequentially.
    """
    # Shape heuristics
    def pick_shape(c: ComponentIn) -> str:
        n = (c.name + c.id).lower()
        if "raspberry" in n or "rpi" in n:
            return "raspberry-pi"
        if "arduino" in n or "uno" in n or "nano" in n:
            return "arduino-uno"
        if "esp32" in n or "esp8266" in n:
            return "esp32"
        if "breadboard" in n:
            return "breadboard"
        if "ic" in n or "chip" in n or "dip" in n or "74hc" in n:
            return "ic-chip"
        return "generic-board"

    def pick_type(c: ComponentIn) -> str:
        t = c.type.lower()
        n = c.name.lower()
        if "controller" in t or "microcontroller" in t or "arduino" in n or "raspberry" in n or "esp" in n:
            return "microcontroller"
        if "sensor" in t or "sensor" in n:
            return "sensor"
        if "motor" in t or "actuator" in t:
            return "motor"
        if "power" in t or "battery" in n or "supply" in n:
            return "power"
        if "display" in t or "lcd" in n or "oled" in n:
            return "display"
        return "module"

    COLS = 3
    nodes = []
    for i, comp in enumerate(components):
        col = i % COLS
        row = i // COLS
        x = 80 + col * 320
        y = 80 + row * 280

        ports = [
            {"id": f"{comp.id}-vcc", "label": "VCC", "side": "top", "offsetPercent": 20},
            {"id": f"{comp.id}-gnd", "label": "GND", "side": "top", "offsetPercent": 80},
            {"id": f"{comp.id}-out", "label": "OUT", "side": "right", "offsetPercent": 50},
            {"id": f"{comp.id}-in", "label": "IN", "side": "left", "offsetPercent": 50},
        ]

        nodes.append(
            {
                "id": comp.id,
                "label": comp.name,
                "type": pick_type(comp),
                "shape": pick_shape(comp),
                "x": x,
                "y": y,
                "ports": ports,
            }
        )

    # Connect sequentially
    wires = []
    for i in range(len(nodes) - 1):
        src = nodes[i]
        tgt = nodes[i + 1]
        wires.append(
            {
                "id": f"wire-{i}",
                "from": {"nodeId": src["id"], "portId": f'{src["id"]}-out'},
                "to": {"nodeId": tgt["id"], "portId": f'{tgt["id"]}-in'},
                "color": "#4488FF",
                "label": "signal",
                "type": "signal",
            }
        )

    return {"nodes": nodes, "wires": wires}


@router.post("/api/connections/generate")
async def generate_connections(request: GenerateRequest):
    """
    Step 1: For each component, query Qdrant RAG for pinout data.
    Step 2: Call Gemini 2.5 Flash via OpenRouter with context + prompt.
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
                if ctx:
                    rag_contexts.append(f"## {comp.name}\n{ctx}")
    else:
        ctx = _rag_search(f"{request.prompt} robot components pinout connections datasheet", top_k=8)
        if ctx:
            rag_contexts.append(f"## RAG Context for: {request.prompt}\n{ctx}")

    rag_block = "\n\n".join(rag_contexts) if rag_contexts else "(No explicit pinout data available — use general knowledge)"

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

RAG PINOUT DATA:
{rag_block}

WIRE COLOR CONVENTION:
- power (3.3V/5V/12V): #FF4444
- ground: #888888
- signal/PWM: #FFD700
- data (I2C/SPI/UART): #4488FF
- CAN: #44FF88

NODE SHAPE RULES:
- Use "raspberry-pi" for Raspberry Pi boards
- Use "arduino-uno" for Arduino boards
- Use "esp32" for ESP32/ESP8266 modules
- Use "breadboard" for breadboards
- Use "ic-chip" for ICs, drivers, H-bridges
- Use "generic-board" for everything else

ROBOTICS STANDARDS & REQUIREMENTS:
- SEMANTIC LABELING (CRITICAL): Assign role-based labels to EACH component instead of repeating generic names (e.g., use "J1 Base Rotation Stepper", "End Effector Servo", "Main Power LiPo", "Logic Controller"). NEVER use generic duplicate names like "Stepper Motor" for multiple parts.
- SIGNAL ARCHITECTURE: Clearly separate and label Power lines, Signal lines, and Ground lines. Add explicit control signal labels on the wires: STEP, DIR, PWM, ENABLE, TX, RX, SDA, SCL where applicable.
- MOTOR CONTROL: Enforce a strict 1:1 relationship between drivers and motors. Each motor driver MUST connect only to its designated motor. Ensure VMOT connects to the main motor supply. Include an explicit "100-470 µF Capacitor" node wired closely across VMOT and GND. Show motor phases: A+, A-, B+, B-.
- FEEDBACK LOOPS: Include feedback components like Encoders, Limit Switches, or sensors where necessary for closed-loop control or homing.
- Grounding: Add an explicit "STAR GND" node component. Ensure Logic GND, Motor GND, and Servo GND all explicitly route back to this single "STAR GND" node.
- Emergency Stop: Clearly implement the E-Stop by either placing a Relay/Contactor that physically cuts main motor power, OR wiring it to pull all driver ENABLE pins to their safe state. Mention which method is used.
- Fuse Placement: Explicitly include and wire a "Battery Fuse", a "Main System Fuse", and a "Buck Converter Fuse" as separate components.
- Servo Power: Provide dedicated step-down voltage regulation (e.g., 5V/6V Buck Converter) for Servos. Include an explicit "470-1000 µF Capacitor" node near the servo power pins.
- Safe Power Architecture: NEVER directly connect a 24V PSU and LiPo battery simultaneously without power path management. Maintain proper hierarchical layout flow from Power Source -> Controller -> Actuators.

Return ONLY this JSON structure (no markdown fences):
{{
  "nodes": [
    {{
      "id": string (use the component id from above),
      "label": string (human-readable name),
      "type": "microcontroller"|"sensor"|"motor"|"power"|"display"|"module"|"other",
      "shape": "raspberry-pi"|"arduino-uno"|"esp32"|"breadboard"|"ic-chip"|"generic-board",
      "x": number (canvas x, spread components 280px apart),
      "y": number (canvas y, group by category in rows),
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
      "label": string (e.g. "I2C SDA", "PWM", "GND"),
      "type": "power"|"ground"|"signal"|"data"|"pwm"|"can"
    }}
  ]
}}

IMPORTANT:
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

        return diagram

    except Exception as exc:
        print(f"[connections/generate] LLM/parse error: {exc}")
        print(f"[connections/generate] Falling back to layout algorithm")
        # Return a clean fallback rather than 500
        return _fallback_diagram(request.components)
