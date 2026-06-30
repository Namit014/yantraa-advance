import os
import json
import re
import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

load_dotenv()

router = APIRouter()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# We need a highly capable model for complex schematic generation
SCHEMATICS_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-pro")

class SchematicRequest(BaseModel):
    prompt: str

@router.post("/generate")
async def generate_schematic(request: SchematicRequest):
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY is not set.")

    system_prompt = """
You are an expert Electronics Engineer designing standard, professional electronic schematics (similar to KiCad or CircuitLab).
The user will provide a description of a robot or circuit.
Your task is to generate the complete schematic netlist down to the discrete component level.
Do NOT just create block-level modules (e.g., avoid a single "Motor Driver Board" block). Instead, break it down or provide standard discrete components (like NE555, BC547, Resistors, Diodes, Capacitors, standard ICs) where appropriate, or use standard IC representations with specific pins.

Output a strictly valid JSON object (no markdown fences) with the following structure:
{
  "components": [
    {
      "id": "R1",
      "label": "10k",
      "type": "resistor",
      "pins": [
        { "id": "1", "label": "1", "side": "left" },
        { "id": "2", "label": "2", "side": "right" }
      ]
    },
    {
      "id": "U1",
      "label": "NE555",
      "type": "ic",
      "pins": [
        { "id": "1", "label": "GND", "side": "bottom" },
        { "id": "2", "label": "TRIG", "side": "left" },
        { "id": "3", "label": "OUT", "side": "right" },
        { "id": "8", "label": "VCC", "side": "top" }
      ]
    }
  ],
  "nets": [
    {
      "id": "net_gnd",
      "label": "GND",
      "connections": [
        { "component": "U1", "pin": "1" },
        { "component": "C1", "pin": "2" }
      ]
    }
  ],
  "bom": [
    { "name": "NE555 Timer IC", "qty": 1 },
    { "name": "10k Resistor", "qty": 4 }
  ],
  "validation": [
    { "type": "warning", "message": "Ensure decoupling capacitor is placed near U1." }
  ]
}

Rules for Pins & Sides:
- 'side' must be one of: "top", "bottom", "left", "right"
- VCC/Power pins usually go on "top"
- GND pins usually go on "bottom"
- Inputs on "left", Outputs on "right"
- The type can be: "resistor", "capacitor", "diode", "transistor", "ic", "mcu", "motor", "power", "sensor", "switch", "display", "led".

Generate a realistic and complete circuit schematic for the user's prompt.
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": SCHEMATICS_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate a detailed schematic for: {request.prompt}"}
        ],
        "temperature": 0.2
    }

    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        raw_text = data["choices"][0]["message"]["content"].strip()
        
        # Clean markdown fences if present
        raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
        raw_text = re.sub(r"\n?```$", "", raw_text).strip()
        
        parsed_json = json.loads(raw_text)
        return parsed_json
    except requests.exceptions.RequestException as e:
        print(f"[Schematics API] OpenRouter request failed: {e}")
        raise HTTPException(status_code=502, detail="Upstream AI provider failed.")
    except json.JSONDecodeError as e:
        print(f"[Schematics API] JSON Parse Error: {e}\nRaw output: {raw_text}")
        raise HTTPException(status_code=500, detail="AI returned invalid JSON.")
    except Exception as e:
        print(f"[Schematics API] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
