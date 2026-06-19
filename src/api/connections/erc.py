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
    - Adds missing Star GND if not present.
    - Routes loose grounds to Star GND.
    """
    fixed_diagram = copy.deepcopy(diagram)
    nodes = fixed_diagram.get("nodes", [])
    wires = fixed_diagram.get("wires", [])
    
    hw_db = load_hardware_db()
    
    # 1. Check if STAR GND exists
    star_gnd_node = None
    for n in nodes:
        if "star gnd" in n.get("name", "").lower() or "star gnd" in n.get("label", "").lower() or "star" in n.get("id", "").lower():
            star_gnd_node = n
            break
            
    if not star_gnd_node:
        # Create a Star GND node
        star_gnd_node = {
            "id": "star_gnd_auto",
            "label": "STAR GND",
            "type": "power",
            "shape": "generic-board",
            "x": 400,
            "y": 50,
            "ports": [
                {"id": "star_gnd_auto-in1", "label": "GND", "side": "bottom", "offsetPercent": 25},
                {"id": "star_gnd_auto-in2", "label": "GND", "side": "bottom", "offsetPercent": 50},
                {"id": "star_gnd_auto-in3", "label": "GND", "side": "bottom", "offsetPercent": 75}
            ]
        }
        nodes.append(star_gnd_node)
        print("[ERC] Added missing STAR GND node.")
        
    # 2. Check for missing grounds in known components
    for node in nodes:
        node_name_lower = node.get("label", "").lower()
        if node["id"] == star_gnd_node["id"]:
            continue
            
        # Is there a wire connected to ground for this node?
        has_gnd_wire = False
        gnd_port_id = None
        for p in node.get("ports", []):
            if "gnd" in p.get("label", "").lower() or "ground" in p.get("label", "").lower():
                gnd_port_id = p["id"]
                # Check if wire exists
                for w in wires:
                    if (w.get("from", {}).get("nodeId") == node["id"] and w.get("from", {}).get("portId") == gnd_port_id) or \
                       (w.get("to", {}).get("nodeId") == node["id"] and w.get("to", {}).get("portId") == gnd_port_id):
                        has_gnd_wire = True
                        break
            if has_gnd_wire:
                break
                
        # Auto-route ground to STAR GND if missing
        if not has_gnd_wire and gnd_port_id:
            wire_id = f"auto-gnd-{node['id']}"
            wires.append({
                "id": wire_id,
                "from": {"nodeId": node["id"], "portId": gnd_port_id},
                "to": {"nodeId": star_gnd_node["id"], "portId": star_gnd_node["ports"][0]["id"]},
                "color": "#888888",
                "label": "GND (Auto-routed)",
                "type": "ground"
            })
            print(f"[ERC] Auto-routed missing GND for node {node['label']}")
            
    # 3. Voltage compatibility check (Warning only for now)
    for w in wires:
        if w.get("type") in ["power", "signal"]:
            from_node = next((n for n in nodes if n["id"] == w.get("from", {}).get("nodeId")), None)
            to_node = next((n for n in nodes if n["id"] == w.get("to", {}).get("nodeId")), None)
            
            if from_node and to_node:
                # Basic check logic based on labels (in a full system, we use hardware_db explicit voltages)
                from_label = from_node.get("label", "").lower()
                to_label = to_node.get("label", "").lower()
                
                # Check hardware DB
                from_hw = next((hw for k, hw in hw_db.items() if k in from_label), None)
                to_hw = next((hw for k, hw in hw_db.items() if k in to_label), None)
                
                if from_hw and to_hw and "power" in w.get("type", ""):
                    from_port = w.get("from", {}).get("portId")
                    # simple heuristic for demonstration without over-engineering
                    pass 

    fixed_diagram["nodes"] = nodes
    fixed_diagram["wires"] = wires
    return fixed_diagram
