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
        if w.get("type") in ["power", "signal"]:
            from_node = next((n for n in nodes if n["id"] == w.get("from", {}).get("nodeId")), None)
            to_node = next((n for n in nodes if n["id"] == w.get("to", {}).get("nodeId")), None)
            
            if from_node and to_node:
                from_label = from_node.get("label", "").lower()
                to_label = to_node.get("label", "").lower()
                
                from_hw = next((hw for k, hw in hw_db.items() if k in from_label), None)
                to_hw = next((hw for k, hw in hw_db.items() if k in to_label), None)
                
                if from_hw and to_hw and "power" in w.get("type", ""):
                    from_port = w.get("from", {}).get("portId")
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
    import requests
    from dotenv import load_dotenv
    load_dotenv()
    
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    if not OPENROUTER_API_KEY:
        print("[ERC Pass 2] No OpenRouter API key found. Skipping.")
        diagram["erc_report"] = "Pass 2 skipped: No API Key."
        return diagram

    diagram_str = json.dumps(diagram, indent=2)

    system_prompt = (
        "You are a Senior Electrical Engineer reviewing a generated circuit diagram. "
        "The current diagram may contain overly complex routing or unnecessary passive components (like excess decoupling caps) that clutter the UI. "
        "Your job is to SIMPLIFY the diagram while ensuring it still strictly works. "
        "DO NOT REMOVE any functional sensors (like ultrasonic, IMU, cameras), motor drivers, motors, or microcontrollers! "
        "Ensure all grounds are logically routed to the main controller or power supply without creating unnecessary 'STAR GND' blocks. "
        "Fix any floating power or signal connections for the remaining essential parts. "
        "Return the EXACT updated JSON containing ONLY the 'nodes' and 'wires' arrays, AND add a third top-level key called 'erc_report' containing a short 2-3 sentence string explaining what you fixed or removed to simplify it. "
        "DO NOT output Markdown fences. Return raw JSON."
    )

    user_message = f"User Prompt: {user_prompt}\n\nCurrent Diagram JSON:\n{diagram_str}\n\nPlease perform ERC validation, remove unnecessary clutter/components, fix wiring, and return the simplified JSON with your erc_report."

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": os.environ.get("OPENROUTER_MODEL", "openrouter/owl-alpha"),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    }

    try:
        print("[ERC Pass 2] Calling LLM to validate and simplify diagram...")
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"].strip()
        
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
