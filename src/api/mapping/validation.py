from typing import List, Dict, Any
import re

def validate_engineering_constraints(components: List[Dict[str, Any]], connections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validates engineering constraints such as motor/controller compatibility.
    """
    errors = []
    
    comp_map = {c["id"]: c for c in components}
    
    for conn in connections:
        src_id = conn.get("from")
        dst_id = conn.get("to")
        
        if src_id not in comp_map or dst_id not in comp_map:
            continue
            
        src = comp_map[src_id]
        dst = comp_map[dst_id]
        
        # Rule: Motor cannot drive Controller
        if src.get("category") == "actuator" and dst.get("category") == "controller":
            errors.append({
                "type": "error",
                "message": f"Rule Violation: Actuator '{src.get('name')}' cannot drive Controller '{dst.get('name')}'."
            })
            
        # Rule: Bearing cannot control Servo
        if src.get("category") == "mechanical" and dst.get("category") == "actuator":
            if conn.get("relation_type", "") in ["controls", "drives"]:
                errors.append({
                    "type": "error",
                    "message": f"Rule Violation: Mechanical part '{src.get('name')}' cannot control Actuator '{dst.get('name')}'."
                })
                
        # Rule: Voltage matching (basic check)
        src_volts = _extract_voltage(src.get("default_voltage", ""))
        dst_volts = _extract_voltage(dst.get("default_voltage", ""))
        
        if conn.get("wire_type") == "power" and src_volts and dst_volts:
            if src_volts != dst_volts:
                # Unless it's a buck converter, etc (simplified for now)
                if src.get("category") != "power" and dst.get("category") != "power":
                    errors.append({
                        "type": "warning",
                        "message": f"Voltage Mismatch: {src.get('name')} ({src_volts}V) connected to {dst.get('name')} ({dst_volts}V)."
                    })
                    
    # Rule: Controller must have power, ground, communication/IO
    for comp in components:
        if comp.get("category") == "controller":
            has_power = any(c.get("to") == comp["id"] and c.get("wire_type") == "power" for c in connections)
            has_gnd = any(c.get("to") == comp["id"] and c.get("wire_type") == "ground" for c in connections)
            
            if not has_power or not has_gnd:
                errors.append({
                    "type": "warning",
                    "message": f"Controller '{comp.get('name')}' is missing Power or Ground connections."
                })
                
    return errors

def _extract_voltage(voltage_str: str) -> float:
    if not voltage_str:
        return 0.0
    match = re.search(r'(\d+(\.\d+)?)', voltage_str)
    if match:
        return float(match.group(1))
    return 0.0
