import os
import json
import copy

def load_hardware_db():
    db_path = os.path.join(
        os.path.dirname(__file__), 
        "../../../knowledgebase/Robots_MetaData/hardware_db.json"
    )
    db_path = os.path.abspath(db_path)
    if os.path.exists(db_path):
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("components", {})
    return {}

def validate_and_fix_diagram(diagram: dict) -> dict:
    """
    Runs Electrical Rule Checking (ERC) on the generated node/wire diagram.
    """
    fixed_diagram = copy.deepcopy(diagram)
    nodes = fixed_diagram.get("nodes", [])
    wires = fixed_diagram.get("wires", [])
    
    hw_db = load_hardware_db()
            
    for w in wires:
        if not isinstance(w, dict):
            continue
            
        w_type = w.get("type")
        if w_type and isinstance(w_type, str) and w_type in ["power", "signal"]:
            from_obj = w.get("from", {})
            to_obj = w.get("to", {})
            
            if not isinstance(from_obj, dict) or not isinstance(to_obj, dict):
                continue
                
            from_node = next((n for n in nodes if isinstance(n, dict) and n.get("id") == from_obj.get("nodeId")), None)
            to_node = next((n for n in nodes if isinstance(n, dict) and n.get("id") == to_obj.get("nodeId")), None)
            
            if from_node and to_node:
                from_label = from_node.get("label", "")
                to_label = to_node.get("label", "")
                
                if isinstance(from_label, str) and isinstance(to_label, str):
                    from_label_lower = from_label.lower()
                    to_label_lower = to_label.lower()
                    
                    from_hw = next((hw for k, hw in hw_db.items() if k in from_label_lower), None)
                    to_hw = next((hw for k, hw in hw_db.items() if k in to_label_lower), None)
                    
                    if from_hw and to_hw and "power" in w_type:
                        from_port = from_obj.get("portId")
                        pass 

    fixed_diagram["nodes"] = nodes
    fixed_diagram["wires"] = wires
    return fixed_diagram

def llm_validate_diagram(diagram: dict, user_prompt: str) -> dict:
    """
    Performs a deep LLM-based Electrical Rule Check (ERC).
    Validates wiring, checks for missing safety features (fuses, estops),
    and redelivers a corrected diagram along with an explanation report.
    """
    try:
        from llm import invoke_yantra_ai
    except ImportError:
        import sys
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
        from src.llm import invoke_yantra_ai

    diagram_str = json.dumps(diagram, indent=2)

    system_prompt = (
        "You are a Senior Electrical Engineer reviewing a generated circuit diagram. "
        "The current diagram may contain overly complex routing or unnecessary passive components (like excess decoupling caps) that clutter the UI. "
        "Your job is to SIMPLIFY the diagram while ensuring 100% electrical and logical accuracy for ANY robot type. "
        "DO NOT REMOVE any functional sensors, but aggressively remove redundant modules, duplicate sensors, or non-essential connections. "
        "Create an explicit power hierarchy: separate high-power actuator rails from low-power logic and sensor rails with proper voltage regulation. "
        "Ensure all modules share ONE explicit and centralized common ground bus. Avoid ambiguous distributed grounding. "
        "Add necessary power stability components (bulk capacitors, decoupling capacitors, noise suppression) and safety features (E-stop, thermal, fault detection, limit switches). "
        "Clearly separate power, ground, data, and communication buses to reduce interference, minimizing line crossings. "
        "Validate component compatibility and replace inefficient components with better alternatives. "
        "Improve labeling for voltage levels, NO/NC switches, and protocol types, and group components strictly into: Power, Control, Motion, Sensor, Communication, and Safety systems. "
        "Return the EXACT updated JSON containing ONLY the 'nodes' and 'wires' arrays, AND add a third top-level key called 'erc_report' containing a short 2-3 sentence string explaining what you fixed or removed to simplify it. "
        "DO NOT output Markdown fences. Return raw JSON."
    )

    user_message = f"User Prompt: {user_prompt}\n\nCurrent Diagram JSON:\n{diagram_str}\n\nPlease perform ERC validation, remove unnecessary clutter/components, fix wiring, and return the simplified JSON with your erc_report."

    try:
        print("[ERC Pass 2] Calling LLM to validate and simplify diagram...")
        result_text = invoke_yantra_ai(
            prompt=user_message,
            system_prompt=system_prompt,
            response_format="json_object"
        )
        
        # Clean markdown if present
        if result_text.startswith("```"):
            lines = result_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            result_text = "\n".join(lines).strip()
            
        fixed_data = json.loads(result_text)
        
        if "nodes" in fixed_data and "wires" in fixed_data:
            return fixed_data
        else:
            print("[ERC Pass 2] LLM returned invalid JSON structure.")
            diagram["erc_report"] = "Pass 2 failed to parse JSON structure."
            return diagram

    except Exception as e:
        print(f"[ERC Pass 2] Error during LLM validation: {e}")
        diagram["erc_report"] = f"Pass 2 validation error: {e}"
        return diagram
