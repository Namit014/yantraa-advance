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
    if "raspberry pi 5" in norm_name or "raspberry pi 5" in norm_role:
        return "raspberry pi 5", hw_db.get("raspberry pi 4") # map pi 5 to pi 4 port layout
    if "raspberry pi" in norm_name or "raspberry pi" in norm_role:
        return "raspberry pi 4", hw_db.get("raspberry pi 4")
    if "arduino" in norm_name or "microcontroller" in norm_role or "controller" in norm_role:
        return "arduino uno", hw_db.get("arduino uno")
        
    # Sensors
    if "imu" in norm_name or "mpu" in norm_name or "gyro" in norm_name:
        if "bno055" in norm_name: return "bno055", hw_db.get("bno055")
        return "mpu6050", hw_db.get("mpu6050")
    if "ultrasonic" in norm_name or "sonar" in norm_name or "distance" in norm_name:
        if "vl53l0x" in norm_name or "tof" in norm_name: return "vl53l0x", hw_db.get("vl53l0x")
        return "ultrasonic sensor", hw_db.get("ultrasonic sensor")
    if "ir " in norm_name or "infrared" in norm_name or "obstacle" in norm_name:
        return "ir sensor", hw_db.get("ir sensor")
    if "encoder" in norm_name:
        return "encoder", hw_db.get("encoder")
    if "limit" in norm_name or "switch" in norm_name:
        return "limit switch", hw_db.get("limit switch")
    if "current" in norm_name and "sensor" in norm_name:
        return "current sensor", hw_db.get("current sensor")
    if "lidar" in norm_name:
        return "lidar", hw_db.get("lidar")
    if "gps" in norm_name or "neo" in norm_name:
        return "gps", hw_db.get("gps")
    if "camera" in norm_name or "vision" in norm_name:
        return "camera", hw_db.get("camera")
    if "hall" in norm_name or "magnetic" in norm_name:
        return "hall effect", hw_db.get("hall effect")
    
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
                    
        # Ensure a microcontroller always exists
        if not any(c["type"] == "microcontroller" for c in components_to_route):
            if "arduino uno" in hw_db:
                components_to_route.append({
                    "node_id": f"comp_{node_id_counter}",
                    "name": hw_db["arduino uno"].get("label", "Arduino Uno R3"),
                    "type": "microcontroller",
                    "ports": hw_db["arduino uno"]["ports"],
                    "hw_key": "arduino uno"
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
        # Prevent multiple fuses if the prompt generated some already
        has_fuse = any(c["type"] == "protection" for c in components_to_route)
        if has_power and "fuse" in hw_db and not has_fuse:
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
        
        # Build Nodes (Horizontal Layout via Dagre on frontend, but we still assign basic types here)
        for c in components_to_route:
            nodes.append({
                "id": c["node_id"],
                "type": "schematicNode",
                "position": {"x": 0, "y": 0}, # Dagre will overwrite this
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
        
        def get_available_mcu_port(port_type: str, fallback_allowed: bool = True):
            if not mcu: return None
            
            # Special case for I2C and SPI, they are buses so ports can be shared
            if port_type in ["i2c_data", "i2c_clock"]:
                for p in mcu["ports"]:
                    if p["type"] == port_type:
                        used_mcu_ports.add(p["id"])
                        return p["id"]
                        
            # Try to find exactly matching unused port
            for p in mcu["ports"]:
                if p["type"] == port_type and p["id"] not in used_mcu_ports:
                    used_mcu_ports.add(p["id"])
                    return p["id"]
                    
            if not fallback_allowed:
                return None
                
            # Fallback 1: Use any general digital/analog pin for digital needs
            if port_type in ["digital_out", "digital_in", "digital_in_out", "pwm_out"]:
                for p in mcu["ports"]:
                    if p["type"] in ["pwm_out", "digital_in_out", "digital_in", "digital_out", "analog_in"] and p["id"] not in used_mcu_ports:
                        used_mcu_ports.add(p["id"])
                        return p["id"]
                        
            # Fallback 2: Share an existing pin (better to share than float)
            for p in mcu["ports"]:
                if p["type"] in ["pwm_out", "digital_in_out", "digital_in", "digital_out", "analog_in"]:
                    return p["id"]
                    
            # Fallback 3: Return the very first port (safeguard)
            return mcu["ports"][0]["id"] if mcu["ports"] else "generic_pin"

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
            if not mcu_5v: # Fallback to 3.3V if no 5V
                mcu_5v = next((p["id"] for p in mcu["ports"] if p["type"] == "power_out"), None)
                
            for c in components_to_route:
                if c["type"] in ["sensor", "motor_driver", "motor"]:
                    # Motors handled separately, but some logic might need power
                    if c["type"] == "motor" and c["hw_key"] != "servo": continue
                    
                    c_vcc = next((p["id"] for p in c["ports"] if p["type"] == "power_in" and p.get("voltage", 5.0) == 5.0), None)
                    if not c_vcc:
                        c_vcc = next((p["id"] for p in c["ports"] if p["type"] == "power_in" and p.get("voltage", 3.3) == 3.3), None)
                    if not c_vcc:
                        c_vcc = next((p["id"] for p in c["ports"] if p["type"] == "power_in"), None)
                        
                    # If it has a logic VCC and we have an MCU power out
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
                    if len(m_ins) >= 2:
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

        # Route servo motors directly to MCU (power is handled above)
        if mcu:
            for motor in motors:
                if motor["hw_key"] == "servo":
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
