import os
import sys
import json
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Ensure src/ is on sys.path
_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from api.mapping.kb import get_component_specs, MANUFACTURER_DB
from api.mapping.normalization import normalize_component, fetch_manufacturer_data
from api.mapping.graph_optimizer import optimize_graph, generate_netlist
from api.mapping.validation import validate_engineering_constraints
from api.mapping.repair import auto_repair_graph
from llm import invoke_yantra_ai

router = APIRouter()

class GenerateArchitectureRequest(BaseModel):
    query: str
    
MASTER_PROMPT = """You are an expert Robotics System Architect.
Build a complete engineering-grade component mapping for the topic: '{query}'

Return ONLY valid JSON matching this schema version v4:
{{
  "version": "v4",
  "robot": {{"type": "robot type"}},
  "components": [
    {{
      "id": "comp_1",
      "name": "Component Name",
      "category": "actuator",
      "confidence": 0.99
    }}
  ],
  "connections": [
    {{
      "id": "conn_1",
      "from": "comp_1",
      "from_port": "pin",
      "to": "comp_2",
      "to_port": "pin",
      "wire_type": "power|signal",
      "relation_type": "controls",
      "confidence": 0.99,
      "reason": "Why this connection exists"
    }}
  ]
}}
Ensure realistic components and standard controller-driver-motor topology.
"""

@router.post("/api/mapping/generate_architecture")
async def generate_architecture(req: GenerateArchitectureRequest):
    prompt = MASTER_PROMPT.format(query=req.query)
    
    # 1. Multi-pass LLM Reasoning (Simulated as single pass with Master Prompt for speed)
    print("[architecture] Calling LLM for architecture generation...", flush=True)
    
    max_retries = 3
    data = None
    
    for attempt in range(max_retries):
        try:
            res_text = invoke_yantra_ai(
                prompt=prompt,
                system_prompt="You are a robotics architect. Return ONLY valid JSON.",
                response_format="json_object"
            )
            
            # Clean response
            res_text = res_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(res_text)
            break
        except Exception as e:
            print(f"[architecture] LLM Error (Attempt {attempt+1}/{max_retries}): {e}", flush=True)
            if attempt == max_retries - 1:
                raise HTTPException(status_code=500, detail="Failed to generate valid architecture from AI after multiple attempts.")
            time.sleep(1)
        
    components = data.get("components", [])
    connections = data.get("connections", [])
    
    # 2. Component Normalization Engine & KB Enrichment
    print("[architecture] Running Normalization & Knowledge Base Enrichment...")
    for comp in components:
        # Normalize
        norm_data = normalize_component(comp.get("name", ""))
        comp.update(norm_data)
        
        # Manufacturer DB
        fetch_manufacturer_data(comp, MANUFACTURER_DB)
        
        # Engineering KB (Pins, Specs)
        specs = get_component_specs(comp["standard_component"])
        comp.update(specs)
        
    # 3. Auto Repair Engine
    print("[architecture] Running Auto-Repair...")
    components, connections = auto_repair_graph(components, connections)
    
    # 4. Graph Optimizer
    print("[architecture] Optimizing Graph...")
    connections = optimize_graph(connections)
    
    # 5. Physics & Assembly Validation Engine
    print("[architecture] Running Validation...")
    validation_errors = validate_engineering_constraints(components, connections)
    
    # 6. Circuit/Netlist Generation
    print("[architecture] Generating Netlist...")
    nets = generate_netlist(connections)
    
    # Construct final v4 schema
    final_output = {
        "version": "v4",
        "robot": data.get("robot", {}),
        "components": components,
        "connections": connections,
        "nets": nets,
        "validation": validation_errors,
        "warnings": [],
        "confidence": {"overall": 0.95}
    }
    
    print("[architecture] Generation complete.")
    return final_output
