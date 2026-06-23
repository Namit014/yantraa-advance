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
        if "tb6612" in norm_name:
            return "tb6612fng", hw_db.get("tb6612fng")
        elif "a4988" in norm_name:
            return "a4988", hw_db.get("a4988")
        return "l298n", hw_db.get("l298n")
    if "stepper" in norm_name or "stepper" in norm_role:
        return "stepper motor", hw_db.get("stepper motor")
    if "servo" in norm_name or "servo" in norm_role:
        return "servo", hw_db.get("servo")
    if "battery" in norm_name or "power" in norm_name:
        return "battery", hw_db.get("battery")
        
    # Microcontroller specific match
    if "mega" in norm_name or "mega" in norm_role:
        return "arduino mega", hw_db.get("arduino mega")
    if "esp32" in norm_name or "esp32" in norm_role:
        return "esp32", hw_db.get("esp32")
    if "stm32" in norm_name or "stm32" in norm_role:
        return "stm32", hw_db.get("stm32")
    if "pico" in norm_name or "pico" in norm_role:
        return "raspberry pi pico", hw_db.get("raspberry pi pico")
    if "raspberry pi" in norm_name or "raspberry pi" in norm_role:
        return "raspberry pi 4", hw_db.get("raspberry pi 4")
    if "arduino" in norm_name or "microcontroller" in norm_role:
        return "arduino uno", hw_db.get("arduino uno")
        
    # Sensors
    if "imu" in norm_name or "mpu" in norm_name or "gyro" in norm_name:
        return "mpu6050", hw_db.get("mpu6050")
    if "ultrasonic" in norm_name or "sonar" in norm_name:
        return "ultrasonic sensor", hw_db.get("ultrasonic sensor")
    if "ir" in norm_name or "infrared" in norm_name:
        return "ir sensor", hw_db.get("ir sensor")
    
    # Motor
    if "motor" in norm_name or "motor" in norm_role:
        return "dc motor", hw_db.get("dc motor")
        
    return None, None

@router.post("/api/schematics/generate")
async def generate_schematics(req: SchematicsRequest):
    try:
        hw_db = load_hardware_db()
        design = req.designData
        subsystems = design.get("subsystems", [])
        
        components_to_route = []
        node_id_counter = 1
        
        for sub in subsystems:
            for comp in sub.get("components", []):
                hw_key, hw_info = match_hardware(comp.get("name", ""), comp.get("role", ""), hw_db)
                if hw_info:
                    components_to_route.append({
                        "node_id": f"comp_{node_id_counter}",
                        "name": hw_info.get("label", hw_key.title()),
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
                    "name": hw_db["battery"].get("label", "Battery Pack"),
                    "type": "power",
                    "ports": hw_db["battery"]["ports"],
                    "hw_key": "battery"
                })
                node_id_counter += 1
                
        # Insert Fuse if we have motor drivers and power
        has_power = any(c["type"] == "power" for c in components_to_route)
        if has_power and "fuse" in hw_db:
            components_to_route.append({
                "node_id": f"comp_{node_id_counter}",
                "name": hw_db["fuse"].get("label", "Main Fuse"),
                "type": "protection",
                "ports": hw_db["fuse"]["ports"],
                "hw_key": "fuse"
            })
            node_id_counter += 1

        nodes = []
        edges = []
        
        # Build Nodes (Horizontal Layout)
        x_offset_power = 100
        x_offset_logic = 100
        x_offset_driver = 100
        x_offset_peri = 100
        
        for c in components_to_route:
            if c["type"] in ["power", "protection"]:
                pos = {"x": x_offset_power, "y": 50}
                x_offset_power += 200
            elif c["type"] == "microcontroller":
                pos = {"x": x_offset_logic, "y": 250}
                x_offset_logic += 350
            elif c["type"] == "motor_driver":
                pos = {"x": x_offset_driver, "y": 450}
                x_offset_driver += 350
            else: # motors, sensors
                pos = {"x": x_offset_peri, "y": 650}
                x_offset_peri += 300
                
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

        power_sources = [c for c in components_to_route if c["type"] == "power"]
        primary_power = power_sources[0] if power_sources else None
        
        fuses = [c for c in components_to_route if c["type"] == "protection"]
        primary_fuse = fuses[0] if fuses else None
        
        mcus = [c for c in components_to_route if c["type"] == "microcontroller"]
        mcu = mcus[0] if mcus else None
        
        drivers = [c for c in components_to_route if c["type"] == "motor_driver"]
        motors = [c for c in components_to_route if c["type"] == "motor"]
        sensors = [c for c in components_to_route if c["type"] == "sensor"]

        used_mcu_ports = set()
        def get_available_mcu_port(port_type: str):
            if not mcu: return None
            for p in mcu["ports"]:
                if p["type"] == port_type and p["id"] not in used_mcu_ports:
                    used_mcu_ports.add(p["id"])
                    return p["id"]
            if port_type in ["digital_out", "digital_in", "digital_in_out"]:
                for p in mcu["ports"]:
                    if p["type"] in ["pwm_out", "digital_in_out", "digital_in", "digital_out"] and p["id"] not in used_mcu_ports:
                        used_mcu_ports.add(p["id"])
                        return p["id"]
            return None

        # Route Power & Common Ground
        p_vcc = None
        p_gnd = None
        if primary_power:
            p_vcc = next((p["id"] for p in primary_power["ports"] if p["type"] == "power_out"), None)
            p_gnd = next((p["id"] for p in primary_power["ports"] if p["type"] == "ground"), None)
            
            fuse_out_port = None
            if primary_fuse and p_vcc:
                fuse_in = next((p["id"] for p in primary_fuse["ports"] if p["type"] == "power_in"), None)
                fuse_out_port = next((p["id"] for p in primary_fuse["ports"] if p["type"] == "power_out"), None)
                if fuse_in:
                    add_edge(primary_power["node_id"], p_vcc, primary_fuse["node_id"], fuse_in, "power")
            
            high_power_source = primary_fuse["node_id"] if primary_fuse else primary_power["node_id"]
            high_power_port = fuse_out_port if primary_fuse else p_vcc
            
            # Distribute power and ground
            for c in components_to_route:
                if c["type"] in ["power", "protection"]: continue
                
                # Ground to everything
                for p in c["ports"]:
                    if p["type"] == "ground" and p_gnd:
                        add_edge(primary_power["node_id"], p_gnd, c["node_id"], p["id"], "ground")
                
                # High Power to MCU and Motor Drivers
                if c["type"] in ["microcontroller", "motor_driver"]:
                    c_vin = next((p["id"] for p in c["ports"] if p["type"] == "power_in" and p.get("voltage", 12.0) > 5.0), None)
                    if not c_vin:
                        c_vin = next((p["id"] for p in c["ports"] if p["type"] == "power_in"), None)
                    
                    if c_vin and high_power_port:
                        add_edge(high_power_source, high_power_port, c["node_id"], c_vin, "power")

        # Distribute MCU Logic Power to Sensors and Drivers (VCC)
        if mcu:
            mcu_5v = next((p["id"] for p in mcu["ports"] if p["type"] == "power_out" and p.get("voltage", 5.0) == 5.0), None)
            
            for c in components_to_route:
                if c["type"] in ["sensor", "motor_driver"]:
                    c_vcc = next((p["id"] for p in c["ports"] if p["type"] == "power_in" and p.get("voltage", 5.0) == 5.0), None)
                    # If it has a logic VCC and we have an MCU 5V
                    if c_vcc and mcu_5v:
                        add_edge(mcu["node_id"], mcu_5v, c["node_id"], c_vcc, "power")

        # Route Drivers to Motors
        motor_idx = 0
        for driver in drivers:
            # How many motors can this driver drive?
            phase_ports = [p["id"] for p in driver["ports"] if p["type"] == "motor_phase"]
            
            while motor_idx < len(motors) and len(phase_ports) >= 2:
                motor = motors[motor_idx]
                if motor["hw_key"] == "stepper motor" and len(phase_ports) >= 4:
                    m_phases = [p["id"] for p in motor["ports"] if p["type"] == "motor_phase"]
                    for i in range(4):
                        add_edge(driver["node_id"], phase_ports.pop(0), motor["node_id"], m_phases[i], "motor_phase")
                    motor_idx += 1
                elif motor["hw_key"] == "dc motor":
                    m_ins = [p["id"] for p in motor["ports"] if p["type"] in ["power_in", "ground"]]
                    add_edge(driver["node_id"], phase_ports.pop(0), motor["node_id"], m_ins[0], "motor_phase")
                    add_edge(driver["node_id"], phase_ports.pop(0), motor["node_id"], m_ins[1], "motor_phase")
                    motor_idx += 1
                else:
                    break

        # Route MCU Logic to Drivers and Sensors
        if mcu:
            for c in components_to_route:
                if c["node_id"] == mcu["node_id"] or c["type"] in ["power", "protection", "motor"]: continue
                
                # I2C Routing
                c_sda = next((p["id"] for p in c["ports"] if p["type"] == "i2c_data"), None)
                c_scl = next((p["id"] for p in c["ports"] if p["type"] == "i2c_clock"), None)
                if c_sda and c_scl:
                    mcu_sda = get_available_mcu_port("i2c_data")
                    mcu_scl = get_available_mcu_port("i2c_clock")
                    if mcu_sda and mcu_scl:
                        add_edge(mcu["node_id"], mcu_sda, c["node_id"], c_sda, "i2c_data")
                        add_edge(mcu["node_id"], mcu_scl, c["node_id"], c_scl, "i2c_clock")
                        
                # PWM Routing
                for p in c["ports"]:
                    if p["type"] == "pwm_in":
                        mcu_pwm = get_available_mcu_port("pwm_out")
                        if mcu_pwm:
                            add_edge(mcu["node_id"], mcu_pwm, c["node_id"], p["id"], "pwm_out")

                # Analog Routing
                for p in c["ports"]:
                    if p["type"] in ["analog_out", "analog_in"]:
                        mcu_analog = get_available_mcu_port("analog_in")
                        if mcu_analog:
                            add_edge(mcu["node_id"], mcu_analog, c["node_id"], p["id"], "analog")

                # Digital Routing
                for p in c["ports"]:
                    if p["type"] in ["digital_in", "digital_out", "digital_in_out"]:
                        mcu_digi = get_available_mcu_port("digital_in_out")
                        if mcu_digi:
                            add_edge(mcu["node_id"], mcu_digi, c["node_id"], p["id"], "digital")

        # Route servo motors directly to MCU and power
        if mcu and primary_power:
            for motor in motors:
                if motor["hw_key"] == "servo":
                    # Servo usually needs 5V, get from MCU or Battery
                    mcu_5v = next((p["id"] for p in mcu["ports"] if p["type"] == "power_out"), None)
                    p_gnd = next((p["id"] for p in primary_power["ports"] if p["type"] == "ground"), None)
                    if mcu_5v:
                        vcc = next((p["id"] for p in motor["ports"] if p["type"] == "power_in"), None)
                        if vcc: add_edge(mcu["node_id"], mcu_5v, motor["node_id"], vcc, "power")
                    if p_gnd:
                        gnd = next((p["id"] for p in motor["ports"] if p["type"] == "ground"), None)
                        if gnd: add_edge(primary_power["node_id"], p_gnd, motor["node_id"], gnd, "ground")
                        
                    sig = next((p["id"] for p in motor["ports"] if p["type"] == "pwm_in"), None)
                    mcu_pwm = get_available_mcu_port("pwm_out")
                    if sig and mcu_pwm:
                        add_edge(mcu["node_id"], mcu_pwm, motor["node_id"], sig, "pwm_out")

        return {
            "status": "success",
            "nodes": nodes,
            "edges": edges
        }
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
