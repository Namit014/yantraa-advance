import json
from src.llm import invoke_yantra_ai
from .schemas import ComponentNode, ConnectionEdge, EvidenceReference, SourceType

class ExtractionEngine:
    """
    Phase 1, 2, 4, 5: V4 Engineering Semantic Extraction.
    Extracts engineering meaning from CAD filenames, classifies functions strictly,
    and extracts kinematic chains and assembly decompositions.
    """
    def __init__(self, raw_evidence: str):
        self.raw_evidence = raw_evidence

    def execute_all(self) -> dict:
        prompt = f"""
EVIDENCE_CONTEXT:
{self.raw_evidence}

Extract the engineering architecture strictly from the evidence above.
You must perform Semantic Extraction (Phase 1), Functional Classification (Phase 2),
Kinematic Chain Extraction (Phase 4), and Assembly Decomposition (Phase 5).

RULES:
1. Translate raw filenames into explicit engineering roles (e.g. A-2228-01 -> J2 Servo Motor).
2. Category must strictly be one of: Actuator, Sensor, Controller, Driver, Transmission, Structural, Power, Communication, Safety, End Effector, Mechanical Support, Motion Guide, Fluid System, Thermal System.
3. Every component must belong to a parent assembly in 'parent_assembly'.
4. Include a 'kinematic_chain' array showing the ordered sequence of joints/links from Base to End Effector.
5. Edges must use specific verbs: powers, controls, drives, supports, mounted_to, communicates_with, provides_feedback_to, transmits_motion_to, contains, belongs_to. DO NOT use generic types like 'signal' or 'linkage'.

OUTPUT FORMAT:
{{
  "components": [
    {{
      "id": "c1", 
      "name": "A-2475-08", 
      "engineering_name": "J2 Servo Motor", 
      "engineering_role": "Drives Shoulder Joint", 
      "category": "Actuator", 
      "parent_assembly": "Shoulder Assembly",
      "evidence": "text segment"
    }}
  ],
  "kinematic_chain": ["Base Assembly", "J1", "Link1", "J2", "Link2", "End Effector"],
  "connections": [
    {{"source": "c1", "target": "c2", "type": "drives", "evidence": "text segment"}}
  ]
}}
"""
        system_prompt = "You are Yantraa V4 Semantic Mapping Engine. Convert raw data into highly accurate engineering structures. Output ONLY valid JSON."
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
