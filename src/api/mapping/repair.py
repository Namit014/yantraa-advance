from typing import List, Dict, Any
import time

def auto_repair_graph(components: List[Dict[str, Any]], connections: List[Dict[str, Any]]) -> tuple:
    """
    Auto-repairs common topological mistakes made by the LLM.
    Returns (components, connections).
    """
    comp_map = {c["id"]: c for c in components}
    new_connections = []
    repaired_components = list(components)
    
    # Track additions to avoid duplicate components
    added_drivers = {}

    for conn in connections:
        src_id = conn.get("from")
        dst_id = conn.get("to")
        
        if src_id not in comp_map or dst_id not in comp_map:
            new_connections.append(conn)
            continue
            
        src = comp_map[src_id]
        dst = comp_map[dst_id]
        
        # Repair: Motor -> Controller (Should be Controller -> Motor)
        if src.get("category") == "actuator" and dst.get("category") == "controller":
            # Reverse the connection
            new_conn = dict(conn)
            new_conn["from"] = dst_id
            new_conn["to"] = src_id
            new_conn["from_port"] = conn.get("to_port", "IO")
            new_conn["to_port"] = conn.get("from_port", "SIG")
            new_connections.append(new_conn)
            continue
            
        # Repair: Controller directly to Motor (Needs a Driver)
        if src.get("category") == "controller" and dst.get("category") == "actuator":
            # Create a driver if one doesn't exist for this motor
            driver_key = f"driver_for_{dst_id}"
            if driver_key not in added_drivers:
                driver_id = f"comp_driver_{int(time.time()*1000)}_{dst_id}"
                driver_comp = {
                    "id": driver_id,
                    "name": f"Driver for {dst.get('name')}",
                    "category": "electronic",
                    "subcategory": "Motor Driver",
                    "confidence": 0.99
                }
                added_drivers[driver_key] = driver_id
                repaired_components.append(driver_comp)
                comp_map[driver_id] = driver_comp
                
            driver_id = added_drivers[driver_key]
            
            # Controller -> Driver
            new_connections.append({
                "id": f"conn_c2d_{src_id}_{driver_id}",
                "from": src_id,
                "from_port": conn.get("from_port", "PWM"),
                "to": driver_id,
                "to_port": "STEP",
                "wire_type": "signal",
                "relation_type": "controls",
                "confidence": 0.99
            })
            
            # Driver -> Motor
            new_connections.append({
                "id": f"conn_d2m_{driver_id}_{dst_id}",
                "from": driver_id,
                "from_port": "A+",
                "to": dst_id,
                "to_port": conn.get("to_port", "A+"),
                "wire_type": "power",
                "relation_type": "drives",
                "confidence": 0.99
            })
            continue

        new_connections.append(conn)
        
    return repaired_components, new_connections
