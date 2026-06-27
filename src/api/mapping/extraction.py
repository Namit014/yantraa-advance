import json
from src.llm import invoke_yantra_ai
from .schemas import ComponentNode, ConnectionEdge, EvidenceReference, SourceType

class ExtractionEngine:
    """
    Phase 1: Multi-Pass Component Extraction Engine.
    Executes extractions for Physical, Assemblies, Interfaces, Connections, Power, Control, and Motion paths.
    """
    def __init__(self, raw_evidence: str):
        self.raw_evidence = raw_evidence

    def execute_all(self) -> dict:
        prompt = f"""
EVIDENCE_CONTEXT:
{self.raw_evidence}

Extract the engineering architecture strictly from the evidence above.
Perform 7 separate internal passes, but output a single JSON object containing these EXACT 7 arrays.
Pass 1: physical_components (motors, sensors, controllers, rails)
Pass 2: assemblies (logical groupings like 'Arm Assembly', 'Base Assembly')
Pass 3: interfaces (ports, connectors)
Pass 4: connections (signal/data wires)
Pass 5: power_paths (power wiring from PSU to components)
Pass 6: control_paths (logical control relationships)
Pass 7: motion_paths (mechanical linkages and drives)

OUTPUT FORMAT:
{{
  "physical_components": [{{"id": "c1", "name": "NEMA23", "category": "actuator", "evidence": "text segment"}}],
  "assemblies": [{{"id": "a1", "name": "Base Assembly", "components": ["c1"]}}],
  "interfaces": [{{"id": "i1", "component_id": "c1", "name": "Power Terminal"}}],
  "connections": [{{"source": "c1", "target": "c2", "type": "SIGNAL", "evidence": "text segment"}}],
  "power_paths": [{{"source": "c1", "target": "c2", "type": "POWER", "evidence": "text segment"}}],
  "control_paths": [{{"source": "c1", "target": "c2", "type": "COMMUNICATION", "evidence": "text segment"}}],
  "motion_paths": [{{"source": "c1", "target": "c2", "type": "MOTION", "evidence": "text segment"}}]
}}
"""
        system_prompt = "You are Yantraa V3 Forensic Component Mapping Engine. You extract precise engineering graphs from evidence. Output ONLY valid JSON."
        try:
            res = invoke_yantra_ai(prompt, system_prompt=system_prompt, response_format="json_object")
            return self._parse_json(res)
        except Exception as e:
            print(f"[extraction] LLM Extraction failed: {e}")
            return {}

    def _parse_json(self, text: str) -> dict:
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}
