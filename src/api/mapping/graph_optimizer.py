from typing import List, Dict, Any

def optimize_graph(connections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Optimizes the graph by removing duplicate edges, circular dependencies,
    and self-loops.
    """
    optimized = []
    seen = set()
    
    for conn in connections:
        src = conn.get("from")
        dst = conn.get("to")
        
        if not src or not dst:
            continue
            
        # Remove self-loops
        if src == dst:
            continue
            
        # Create a unique key for deduplication
        # Include pins if available
        src_pin = conn.get("from_port", "")
        dst_pin = conn.get("to_port", "")
        
        edge_key = f"{src}:{src_pin}->{dst}:{dst_pin}"
        if edge_key in seen:
            continue
            
        seen.add(edge_key)
        
        # Basic circular dependency check for power (prevent A -> B -> A)
        if conn.get("wire_type") == "power":
            reverse_key = f"{dst}->{src}"
            # This is a simplification; a real check would do a full cycle detection
            # but for this iteration, we just prevent direct back-powering.
            if any(f"{dst}:" in k and f"->{src}:" in k for k in seen):
                # A cycle is detected, skip adding this edge
                continue
                
        optimized.append(conn)
        
    return optimized

def generate_netlist(connections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generates a KiCad-style netlist from connections.
    """
    nets = []
    net_counter = 1
    
    for conn in connections:
        src = conn.get("from")
        dst = conn.get("to")
        src_pin = conn.get("from_port", "")
        dst_pin = conn.get("to_port", "")
        
        net_name = f"NET{net_counter:03d}"
        
        # Give meaningful names to power nets
        if conn.get("wire_type") == "power":
            if "5V" in src_pin or "5V" in dst_pin:
                net_name = "+5V"
            elif "24V" in src_pin or "24V" in dst_pin:
                net_name = "+24V"
        elif conn.get("wire_type") == "ground":
            net_name = "GND"
            
        nets.append({
            "net_id": net_name,
            "source": f"{src} {src_pin}".strip(),
            "target": f"{dst} {dst_pin}".strip()
        })
        
        if not net_name.startswith("+") and net_name != "GND":
            net_counter += 1
            
    return nets
