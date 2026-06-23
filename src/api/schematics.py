from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
import traceback

router = APIRouter()

# Load hardware db
_hardware_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "knowledgebase", "Robots_MetaData", "hardware_db.json"))

def load_hardware_db():
    if os.path.exists(_hardware_db_path):
        with open(_hardware_db_path, "r", encoding="utf-8") as f:
            return json.load(f).get("components", {})
    return {}

class SchematicsRequest(BaseModel):
    designData: Dict[str, Any]

def normalize_name(name: str) -> str:
    return name.lower().replace("-", " ").strip()

def match_hardware(component_name: str, component_role: str, hw_db: dict):
    norm_name = normalize_name(component_name)
    norm_role = normalize_name(component_role)
    
    # Try direct match
    for key, hw in hw_db.items():
        if key in norm_name or norm_name in key:
            return key, hw
            
    # Try role match
    for key, hw in hw_db.items():
        if key in norm_role or norm_role in key:
            return key, hw
            
    # Heuristics based on common parts
    if "motor driver" in norm_name or "motor driver" in norm_role:
        return "l298n", hw_db.get("l298n")
    if "stepper" in norm_name or "stepper" in norm_role:
        return "stepper motor", hw_db.get("stepper motor")
    if "servo" in norm_name or "servo" in norm_role:
        return "servo", hw_db.get("servo")
    if "battery" in norm_name or "power" in norm_name:
        return "battery", hw_db.get("battery")
    if "arduino" in norm_name or "microcontroller" in norm_role:
        return "arduino uno", hw_db.get("arduino uno")
    if "imu" in norm_name or "mpu" in norm_name or "gyro" in norm_name:
        return "mpu6050", hw_db.get("mpu6050")
        
    return None, None

@router.post("/api/schematics/generate")
async def generate_schematics(req: SchematicsRequest):
    try:
        hw_db = load_hardware_db()
        design = req.designData
        subsystems = design.get("subsystems", [])
        
        # 1. Gather all components to represent
        components_to_route = []
        node_id_counter = 1
        
        for sub in subsystems:
            for comp in sub.get("components", []):
                hw_key, hw_info = match_hardware(comp.get("name", ""), comp.get("role", ""), hw_db)
                if hw_info:
                    components_to_route.append({
                        "node_id": f"comp_{node_id_counter}",
                        "name": comp.get("name", hw_key),
                        "type": hw_info.get("type"),
                        "ports": hw_info.get("ports", []),
                        "hw_key": hw_key
                    })
                    node_id_counter += 1
                    
        # Add default power source if none exists
        if not any(c["type"] == "power" for c in components_to_route):
            if "battery" in hw_db:
                components_to_route.append({
                    "node_id": f"comp_{node_id_counter}",
                    "name": "Battery Pack",
                    "type": "power",
                    "ports": hw_db["battery"]["ports"],
                    "hw_key": "battery"
                })
                node_id_counter += 1

        nodes = []
        edges = []
        
        # Build Nodes
        y_offset_power = 0
        y_offset_logic = 0
        y_offset_peri = 0
        
        for c in components_to_route:
            # Simple layout categorization
            if c["type"] == "power":
                pos = {"x": 100, "y": 100 + y_offset_power}
                y_offset_power += 250
            elif c["type"] == "microcontroller":
                pos = {"x": 500, "y": 100 + y_offset_logic}
                y_offset_logic += 400
            else:
                pos = {"x": 900, "y": 100 + y_offset_peri}
                y_offset_peri += 250
                
            nodes.append({
                "id": c["node_id"],
                "type": "schematicNode",
                "position": pos,
                "data": {
                    "label": c["name"].title(),
                    "hwType": c["type"],
                    "ports": c["ports"]
                }
            })
            
        # 2. Deterministic Routing
        # Find primary power source
        power_sources = [c for c in components_to_route if c["type"] == "power"]
        primary_power = power_sources[0] if power_sources else None
        
        # Find microcontroller
        mcus = [c for c in components_to_route if c["type"] == "microcontroller"]
        mcu = mcus[0] if mcus else None
        
        edge_id_counter = 1
        def add_edge(source_node, source_port, target_node, target_port, wire_type):
            nonlocal edge_id_counter
            edges.append({
                "id": f"wire_{edge_id_counter}",
                "source": source_node,
                "sourceHandle": source_port,
                "target": target_node,
                "targetHandle": target_port,
                "type": "smoothstep",
                "animated": wire_type in ["i2c_data", "i2c_clock", "pwm_out"],
                "data": {"wireType": wire_type}
            })
            edge_id_counter += 1

        # Track used ports on MCU to avoid collisions
        used_mcu_ports = set()
        def get_available_mcu_port(port_type: str):
            if not mcu: return None
            for p in mcu["ports"]:
                if p["type"] == port_type and p["id"] not in used_mcu_ports:
                    used_mcu_ports.add(p["id"])
                    return p["id"]
            return None

        # Route Power
        if primary_power:
            p_vcc = next((p["id"] for p in primary_power["ports"] if p["type"] == "power_out"), None)
            p_gnd = next((p["id"] for p in primary_power["ports"] if p["type"] == "ground"), None)
            
            for c in components_to_route:
                if c["node_id"] == primary_power["node_id"]: continue
                # Connect VCC
                c_vin = next((p["id"] for p in c["ports"] if p["type"] == "power_in"), None)
                if c_vin and p_vcc:
                    add_edge(primary_power["node_id"], p_vcc, c["node_id"], c_vin, "power")
                # Connect GND
                c_gnd = next((p["id"] for p in c["ports"] if p["type"] == "ground"), None)
                if c_gnd and p_gnd:
                    add_edge(primary_power["node_id"], p_gnd, c["node_id"], c_gnd, "ground")

        # Route Logic from MCU
        if mcu:
            for c in components_to_route:
                if c["node_id"] == mcu["node_id"] or c["type"] == "power": continue
                
                # I2C Routing
                c_sda = next((p["id"] for p in c["ports"] if p["type"] == "i2c_data"), None)
                c_scl = next((p["id"] for p in c["ports"] if p["type"] == "i2c_clock"), None)
                if c_sda and c_scl:
                    mcu_sda = get_available_mcu_port("i2c_data")
                    mcu_scl = get_available_mcu_port("i2c_clock")
                    if mcu_sda and mcu_scl:
                        add_edge(mcu["node_id"], mcu_sda, c["node_id"], c_sda, "i2c_data")
                        add_edge(mcu["node_id"], mcu_scl, c["node_id"], c_scl, "i2c_clock")
                        
                # PWM Routing (Servos / Motor Drivers)
                c_pwm = next((p["id"] for p in c["ports"] if p["type"] == "pwm_in"), None)
                if c_pwm:
                    mcu_pwm = get_available_mcu_port("pwm_out")
                    if mcu_pwm:
                        add_edge(mcu["node_id"], mcu_pwm, c["node_id"], c_pwm, "pwm_out")
                        
                # Digital Routing (Motor Driver IN1, IN2)
                for p in c["ports"]:
                    if p["type"] == "digital_in":
                        mcu_digi = get_available_mcu_port("pwm_out") # Fallback to PWM pins for digital out
                        if mcu_digi:
                            add_edge(mcu["node_id"], mcu_digi, c["node_id"], p["id"], "digital_out")

        return {
            "status": "success",
            "nodes": nodes,
            "edges": edges
        }
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
