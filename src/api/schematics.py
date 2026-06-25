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
    
    # Ignore mechanical/structural components
    ignore_keywords = ["bracket", "adapter", "tube", "mount", "frame", "chassis", "plate", "screw", "nut", "bolt", "link"]
    if any(kw in norm_name or kw in norm_role for kw in ignore_keywords):
        return "ignore", None

    # Try direct match
    for key, hw in hw_db.items():
        if key in norm_name:
            return key, hw
            
    # Try role match
    for key, hw in hw_db.items():
        if key in norm_role:
            return key, hw
            
    # Heuristics based on common parts
    if "motor driver" in norm_name or "motor driver" in norm_role or "esc" in norm_name:
        return "l298n", hw_db.get("l298n")
    if "motor" in norm_name or "motor" in norm_role or "actuator" in norm_name or "pump" in norm_name or "a 2475" in norm_name or "a 2438" in norm_name:
        return "dc motor", hw_db.get("dc motor")
    if "servo" in norm_name or "gripper" in norm_name or "a 2055" in norm_name:
        return "servo", hw_db.get("servo")
    if "sensor" in norm_name or "sensor" in norm_role or "camera" in norm_name or "encoder" in norm_name:
        return "ultrasonic sensor", hw_db.get("ultrasonic sensor")
    if "power" in norm_name or "power" in norm_role or "battery" in norm_name or "supply" in norm_name or "a 2525" in norm_name:
        return "battery", hw_db.get("battery")
    if "microcontroller" in norm_name or "brain" in norm_role or "board" in norm_name or "pi" in norm_name or "a 2432" in norm_name or "flight" in norm_name:
        return "arduino uno", hw_db.get("arduino uno")
    if "switch" in norm_name or "button" in norm_name or "relay" in norm_name:
        return "limit switch", hw_db.get("limit switch")
    if "wheel" in norm_name or "tire" in norm_name:
        return "wheel", hw_db.get("wheel")
    if "nozzle" in norm_name or "spray" in norm_name or "extruder" in norm_name:
        return "nozzle", hw_db.get("nozzle")
    if "regulator" in norm_name or "buck" in norm_name or "converter" in norm_name or "step down" in norm_name:
        return "buck converter", hw_db.get("buck converter")
        
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
                
                if hw_key == "ignore":
                    continue
                    
                if hw_info:
                    components_to_route.append({
                        "node_id": f"comp_{node_id_counter}",
                        "name": hw_info.get("label", hw_info.get("name", comp.get("name"))),
                        "type": hw_info.get("type", "generic"),
                        "ports": hw_info.get("ports", []),
                        "hw_key": hw_key
                    })
                else:
                    # Fallback for unknown components to ensure they appear on the schematic
                    components_to_route.append({
                        "node_id": f"comp_{node_id_counter}",
                        "name": comp.get("name", "Generic Module").title(),
                        "type": "generic_module",
                        "ports": [
                            {"id": "vcc", "label": "VCC", "type": "power_in"},
                            {"id": "gnd", "label": "GND", "type": "ground"},
                            {"id": "sig", "label": "SIG", "type": "digital_in_out"}
                        ],
                        "hw_key": "generic"
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

        # Ensure at least one sensor always exists
        if not any(c["type"] == "sensor" for c in components_to_route):
            if "ultrasonic sensor" in hw_db:
                components_to_route.append({
                    "node_id": f"comp_{node_id_counter}",
                    "name": hw_db["ultrasonic sensor"].get("label", "HC-SR04 Ultrasonic Sensor"),
                    "type": "sensor",
                    "ports": hw_db["ultrasonic sensor"]["ports"],
                    "hw_key": "ultrasonic sensor"
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
                
        # Insert Master Power Switch
        has_power = any(c["type"] == "power" for c in components_to_route)
        has_switch = any(c["hw_key"] == "power switch" for c in components_to_route)
        if has_power and "power switch" in hw_db and not has_switch:
            components_to_route.append({
                "node_id": f"comp_{node_id_counter}",
                "name": hw_db["power switch"].get("label", "Master Power Switch"),
                "type": "protection",
                "ports": hw_db["power switch"]["ports"],
                "hw_key": "power switch"
            })
            node_id_counter += 1

        # Insert Protection Diode
        has_diode = any(c["hw_key"] == "protection diode" for c in components_to_route)
        if has_power and "protection diode" in hw_db and not has_diode:
            components_to_route.append({
                "node_id": f"comp_{node_id_counter}",
                "name": hw_db["protection diode"].get("label", "1N5408 Protection Diode"),
                "type": "protection",
                "ports": hw_db["protection diode"]["ports"],
                "hw_key": "protection diode"
            })
            node_id_counter += 1

        # Insert Fuse if we have motor drivers and power
        has_fuse = any(c["type"] == "protection" and c["hw_key"] == "fuse" for c in components_to_route)
        if has_power and "fuse" in hw_db and not has_fuse:
            components_to_route.append({
                "node_id": f"comp_{node_id_counter}",
                "name": hw_db["fuse"].get("label", "Main Fuse"),
                "type": "protection",
                "ports": hw_db["fuse"]["ports"],
                "hw_key": "fuse"
            })
            node_id_counter += 1

        # Insert Motor Driver if we have motors but no drivers
        has_dc_motors = any(c["type"] == "motor" and c["hw_key"] != "servo" for c in components_to_route)
        has_driver = any(c["type"] == "motor_driver" for c in components_to_route)
        if has_dc_motors and "l298n" in hw_db and not has_driver:
            components_to_route.append({
                "node_id": f"comp_{node_id_counter}",
                "name": hw_db["l298n"].get("label", "L298N Motor Driver"),
                "type": "motor_driver",
                "ports": hw_db["l298n"]["ports"],
                "hw_key": "l298n"
            })
            node_id_counter += 1

        # Insert Buck Converter if we have high power and a microcontroller
        has_mcu = any(c["type"] == "microcontroller" for c in components_to_route)
        has_regulator = any(c["type"] == "regulator" for c in components_to_route)
        if has_power and has_mcu and "buck converter" in hw_db and not has_regulator:
            components_to_route.append({
                "node_id": f"comp_{node_id_counter}",
                "name": hw_db["buck converter"].get("label", "LM2596 5V Buck Converter"),
                "type": "regulator",
                "ports": hw_db["buck converter"]["ports"],
                "hw_key": "buck converter"
            })
            node_id_counter += 1

        # Insert Filtering Capacitors
        if has_driver and "100uf capacitor" in hw_db:
            components_to_route.append({
                "node_id": f"comp_{node_id_counter}",
                "name": "Motor Power Filter Cap (100µF)",
                "type": "passive",
                "ports": hw_db["100uf capacitor"]["ports"],
                "hw_key": "100uf capacitor",
                "sub_role": "driver_filter"
            })
            node_id_counter += 1
            
        if (has_regulator or has_mcu) and "100uf capacitor" in hw_db:
            components_to_route.append({
                "node_id": f"comp_{node_id_counter}",
                "name": "5V Rail Filter Cap (100µF)",
                "type": "passive",
                "ports": hw_db["100uf capacitor"]["ports"],
                "hw_key": "100uf capacitor",
                "sub_role": "regulator_filter"
            })
            node_id_counter += 1

        if has_mcu and "0.1uf capacitor" in hw_db:
            components_to_route.append({
                "node_id": f"comp_{node_id_counter}",
                "name": "MCU Bypass Cap (0.1µF)",
                "type": "passive",
                "ports": hw_db["0.1uf capacitor"]["ports"],
                "hw_key": "0.1uf capacitor",
                "sub_role": "mcu_bypass"
            })
            node_id_counter += 1

        # Motor Grouping: if 4 motors, name them Left/Right
        dc_motors_list = [c for c in components_to_route if c["type"] == "motor" and c["hw_key"] != "servo"]
        if len(dc_motors_list) == 4:
            dc_motors_list[0]["name"] = "Front Left Motor"
            dc_motors_list[1]["name"] = "Back Left Motor"
            dc_motors_list[2]["name"] = "Front Right Motor"
            dc_motors_list[3]["name"] = "Back Right Motor"

        # Clean up duplicates of unique parts to prevent isolated unrouted nodes
        cleaned_components = []
        seen_mcu = False
        seen_battery = False
        seen_fuse = False
        seen_switch = False
        seen_diode = False
        
        for c in components_to_route:
            if c["type"] == "microcontroller":
                if seen_mcu: continue
                seen_mcu = True
            if c["type"] == "power" and c["hw_key"] == "battery":
                if seen_battery: continue
                seen_battery = True
            if c["hw_key"] == "fuse":
                if seen_fuse: continue
                seen_fuse = True
            if c["hw_key"] == "power switch":
                if seen_switch: continue
                seen_switch = True
            if c["hw_key"] == "protection diode":
                if seen_diode: continue
                seen_diode = True
            cleaned_components.append(c)
            
        components_to_route = cleaned_components

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
        def add_edge(source_node, source_port, target_node, target_port, wire_type, label=""):
            nonlocal edge_id_counter
            edges.append({
                "id": f"wire_{edge_id_counter}",
                "source": source_node,
                "sourceHandle": source_port,
                "target": target_node,
                "targetHandle": target_port,
                "type": "smoothstep",
                "animated": wire_type in ["i2c_data", "i2c_clock", "pwm_out"],
                "data": {"wireType": wire_type, "label": label}
            })
            edge_id_counter += 1

        power_sources = [c for c in components_to_route if c["type"] == "power"]
        primary_power = power_sources[0] if power_sources else None
        
        switches = [c for c in components_to_route if c["hw_key"] == "power switch"]
        power_switch = switches[0] if switches else None

        diodes = [c for c in components_to_route if c["hw_key"] == "protection diode"]
        protection_diode = diodes[0] if diodes else None

        fuses = [c for c in components_to_route if c["type"] == "protection" and c["hw_key"] == "fuse"]
        primary_fuse = fuses[0] if fuses else None
        
        regulators = [c for c in components_to_route if c["type"] == "regulator"]
        buck = regulators[0] if regulators else None
        
        mcus = [c for c in components_to_route if c["type"] == "microcontroller"]
        mcu = mcus[0] if mcus else None
        
        drivers = [c for c in components_to_route if c["type"] == "motor_driver"]
        motors = [c for c in components_to_route if c["type"] == "motor"]
        sensors = [c for c in components_to_route if c["type"] == "sensor"]

        used_mcu_ports = set()
        
        def get_available_mcu_port(port_type: str, fallback_allowed: bool = True):
            if not mcu: return None
            if port_type in ["i2c_data", "i2c_clock"]:
                for p in mcu["ports"]:
                    if p["type"] == port_type:
                        used_mcu_ports.add(p["id"])
                        return p["id"]
            for p in mcu["ports"]:
                if p["type"] == port_type and p["id"] not in used_mcu_ports:
                    used_mcu_ports.add(p["id"])
                    return p["id"]
            if not fallback_allowed:
                return None
            if port_type in ["digital_out", "digital_in", "digital_in_out", "pwm_out"]:
                for p in mcu["ports"]:
                    if p["type"] in ["pwm_out", "digital_in_out", "digital_in", "digital_out", "analog_in"] and p["id"] not in used_mcu_ports:
                        used_mcu_ports.add(p["id"])
                        return p["id"]
            for p in mcu["ports"]:
                if p["type"] in ["pwm_out", "digital_in_out", "digital_in", "digital_out", "analog_in"]:
                    return p["id"]
            return mcu["ports"][0]["id"] if mcu["ports"] else "generic_pin"

        p_vcc = next((p["id"] for p in primary_power["ports"] if p["type"] == "power_out"), None) if primary_power else None
        p_gnd = next((p["id"] for p in primary_power["ports"] if p["type"] == "ground"), None) if primary_power else None

        # 1. Battery -> Switch -> Diode -> Fuse
        high_power_source = primary_power["node_id"] if primary_power else None
        high_power_port = p_vcc
        
        if primary_power and p_vcc:
            next_node = primary_power["node_id"]
            next_port = p_vcc
            
            if power_switch:
                sw_in = next((p["id"] for p in power_switch["ports"] if p["type"] == "power_in"), None)
                sw_out = next((p["id"] for p in power_switch["ports"] if p["type"] == "power_out"), None)
                if sw_in and sw_out:
                    add_edge(next_node, next_port, power_switch["node_id"], sw_in, "power", "+12V_BATT")
                    next_node = power_switch["node_id"]
                    next_port = sw_out

            if protection_diode:
                d_in = next((p["id"] for p in protection_diode["ports"] if p["type"] == "power_in"), None)
                d_out = next((p["id"] for p in protection_diode["ports"] if p["type"] == "power_out"), None)
                if d_in and d_out:
                    add_edge(next_node, next_port, protection_diode["node_id"], d_in, "power", "+12V_SWITCHED")
                    next_node = protection_diode["node_id"]
                    next_port = d_out
                    
            if primary_fuse:
                fuse_in = next((p["id"] for p in primary_fuse["ports"] if p["type"] == "power_in"), None)
                fuse_out = next((p["id"] for p in primary_fuse["ports"] if p["type"] == "power_out"), None)
                if fuse_in and fuse_out:
                    add_edge(next_node, next_port, primary_fuse["node_id"], fuse_in, "power", "+12V_PROTECTED")
                    next_node = primary_fuse["node_id"]
                    next_port = fuse_out
                    
            high_power_source = next_node
            high_power_port = next_port

        # 2. High Power to Buck Converter & Motor Drivers
        if high_power_source and high_power_port:
            if buck:
                buck_vin = next((p["id"] for p in buck["ports"] if p["type"] == "power_in"), None)
                if buck_vin:
                    add_edge(high_power_source, high_power_port, buck["node_id"], buck_vin, "power", "+12V IN")
            
            for driver in drivers:
                driver_vin = next((p["id"] for p in driver["ports"] if p["type"] == "power_in" and p.get("voltage", 12.0) > 5.0), None)
                if not driver_vin:
                    driver_vin = next((p["id"] for p in driver["ports"] if p["type"] == "power_in"), None)
                if driver_vin:
                    add_edge(high_power_source, high_power_port, driver["node_id"], driver_vin, "power", "+12V VMOT")

        # 3. 5V Logic Power
        logic_5v_source = None
        logic_5v_port = None
        if buck:
            buck_vout = next((p["id"] for p in buck["ports"] if p["type"] == "power_out"), None)
            if buck_vout:
                logic_5v_source = buck["node_id"]
                logic_5v_port = buck_vout
        elif mcu:
            mcu_5v = next((p["id"] for p in mcu["ports"] if p["type"] == "power_out" and p.get("voltage", 5.0) == 5.0), None)
            if not mcu_5v:
                mcu_5v = next((p["id"] for p in mcu["ports"] if p["type"] == "power_out"), None)
            if mcu_5v:
                logic_5v_source = mcu["node_id"]
                logic_5v_port = mcu_5v

        # Distribute Logic Power
        for c in components_to_route:
            if c["type"] in ["power", "protection", "regulator"]: continue
            if c["type"] == "motor" and c["hw_key"] != "servo": continue
            if c["type"] == "microcontroller" and logic_5v_source != mcu["node_id"]:
                c_vcc = next((p["id"] for p in c["ports"] if p["id"] == "5v"), None)
                if not c_vcc:
                    c_vcc = next((p["id"] for p in c["ports"] if p["type"] == "power_in"), None)
                
                if c_vcc and logic_5v_source:
                    add_edge(logic_5v_source, logic_5v_port, c["node_id"], c_vcc, "power", "+5V")
                elif high_power_source and not logic_5v_source:
                    # No buck converter, power MCU via VIN
                    c_vin = next((p["id"] for p in c["ports"] if p["id"] == "vin" or p["type"] == "power_in"), None)
                    if c_vin:
                        add_edge(high_power_source, high_power_port, c["node_id"], c_vin, "power", "VIN Power")
                        
            elif c["type"] in ["sensor", "motor_driver", "generic_module", "motor"]:
                if c["type"] == "motor_driver":
                    c_vcc = next((p["id"] for p in c["ports"] if p["type"] == "power_in" and p.get("voltage", 5.0) <= 5.0), None)
                else:
                    c_vcc = next((p["id"] for p in c["ports"] if p["type"] == "power_in" and p.get("voltage", 5.0) == 5.0), None)
                    if not c_vcc:
                        c_vcc = next((p["id"] for p in c["ports"] if p["type"] == "power_in"), None)
                
                if c_vcc and logic_5v_source:
                    add_edge(logic_5v_source, logic_5v_port, c["node_id"], c_vcc, "power", "+5V")

        # 4. Common Ground
        if primary_power and p_gnd:
            for c in components_to_route:
                if c["type"] == "power": continue
                # Do not connect ground if it's the power switch or diode
                if c["hw_key"] in ["power switch", "protection diode"]: continue
                
                for p in c["ports"]:
                    if p["type"] == "ground":
                        add_edge(primary_power["node_id"], p_gnd, c["node_id"], p["id"], "ground", "GND")

        # 5. Connect Capacitors
        for c in components_to_route:
            if c["type"] == "passive":
                sub_role = c.get("sub_role")
                c_pos = next((p["id"] for p in c["ports"] if p["type"] == "power_in"), None)
                c_neg = next((p["id"] for p in c["ports"] if p["type"] == "ground"), None)
                if c_pos and c_neg:
                    if sub_role == "driver_filter" and high_power_source:
                        add_edge(high_power_source, high_power_port, c["node_id"], c_pos, "power", "+12V")
                    elif sub_role in ["regulator_filter", "mcu_bypass"] and logic_5v_source:
                        add_edge(logic_5v_source, logic_5v_port, c["node_id"], c_pos, "power", "+5V")

        # Route Drivers to Motors
        dc_motors = [c for c in components_to_route if c["type"] == "motor" and c["hw_key"] not in ["servo", "stepper motor"]]
        stepper_motors = [c for c in components_to_route if c["type"] == "motor" and c["hw_key"] == "stepper motor"]
        
        for driver in drivers:
            phase_ports = [p["id"] for p in driver["ports"] if p["type"] == "motor_phase"]
            
            if stepper_motors and len(phase_ports) >= 4:
                motor = stepper_motors.pop(0)
                m_phases = [p["id"] for p in motor["ports"] if p["type"] == "motor_phase"]
                for i in range(4):
                    add_edge(driver["node_id"], phase_ports.pop(0), motor["node_id"], m_phases[i], "motor_phase", f"PH{i+1}")
            elif dc_motors and len(phase_ports) >= 2:
                if len(dc_motors) == 4 and len(drivers) == 1:
                    out1, out2 = phase_ports[0], phase_ports[1]
                    out3 = phase_ports[2] if len(phase_ports) > 2 else phase_ports[0]
                    out4 = phase_ports[3] if len(phase_ports) > 3 else phase_ports[1]
                    
                    for i in [0, 1]:
                        m_ins = [p["id"] for p in dc_motors[i]["ports"] if p["type"] in ["power_in", "ground"]]
                        if len(m_ins) >= 2:
                            add_edge(driver["node_id"], out1, dc_motors[i]["node_id"], m_ins[0], "motor_phase", "LEFT+")
                            add_edge(driver["node_id"], out2, dc_motors[i]["node_id"], m_ins[1], "motor_phase", "LEFT-")
                            
                    for i in [2, 3]:
                        m_ins = [p["id"] for p in dc_motors[i]["ports"] if p["type"] in ["power_in", "ground"]]
                        if len(m_ins) >= 2:
                            add_edge(driver["node_id"], out3, dc_motors[i]["node_id"], m_ins[0], "motor_phase", "RIGHT+")
                            add_edge(driver["node_id"], out4, dc_motors[i]["node_id"], m_ins[1], "motor_phase", "RIGHT-")
                    dc_motors = []
                else:
                    while dc_motors and len(phase_ports) >= 2:
                        motor = dc_motors.pop(0)
                        m_ins = [p["id"] for p in motor["ports"] if p["type"] in ["power_in", "ground"]]
                        if len(m_ins) >= 2:
                            add_edge(driver["node_id"], phase_ports.pop(0), motor["node_id"], m_ins[0], "motor_phase", "M+")
                            add_edge(driver["node_id"], phase_ports.pop(0), motor["node_id"], m_ins[1], "motor_phase", "M-")

        # Route MCU Logic to Drivers and Sensors
        def get_mcu_port_label(port_id):
            if not mcu: return ""
            p = next((x for x in mcu["ports"] if x["id"] == port_id), None)
            if not p: return port_id.upper()
            return p.get("label", port_id.upper()).split(" ")[0] # E.g. "D9 (PWM)" -> "D9"

        if mcu:
            for driver in drivers:
                for p in driver["ports"]:
                    if p["type"] in ["pwm_in", "digital_in"]:
                        mcu_port = get_available_mcu_port("pwm_out") if "pwm" in p["type"] else get_available_mcu_port("digital_in_out")
                        if mcu_port:
                            lbl_match = p.get("label", "SIG").upper()
                            mcu_lbl = get_mcu_port_label(mcu_port)
                            add_edge(mcu["node_id"], mcu_port, driver["node_id"], p["id"], "digital", f"{mcu_lbl} -> {lbl_match}")
                            
            for c in components_to_route:
                if c["node_id"] == mcu["node_id"] or c["type"] in ["power", "protection", "regulator", "motor", "motor_driver", "passive"]: continue
                
                c_sda = next((p["id"] for p in c["ports"] if p["type"] == "i2c_data"), None)
                c_scl = next((p["id"] for p in c["ports"] if p["type"] == "i2c_clock"), None)
                if c_sda and c_scl:
                    mcu_sda = get_available_mcu_port("i2c_data")
                    mcu_scl = get_available_mcu_port("i2c_clock")
                    if mcu_sda and mcu_scl:
                        sda_lbl = get_mcu_port_label(mcu_sda)
                        scl_lbl = get_mcu_port_label(mcu_scl)
                        add_edge(mcu["node_id"], mcu_sda, c["node_id"], c_sda, "i2c_data", f"{sda_lbl} -> SDA")
                        add_edge(mcu["node_id"], mcu_scl, c["node_id"], c_scl, "i2c_clock", f"{scl_lbl} -> SCL")
                        
                for p in c["ports"]:
                    lbl = p.get("label", "").upper()
                    if p["type"] == "pwm_in":
                        mcu_pwm = get_available_mcu_port("pwm_out")
                        if mcu_pwm:
                            mcu_lbl = get_mcu_port_label(mcu_pwm)
                            add_edge(mcu["node_id"], mcu_pwm, c["node_id"], p["id"], "pwm_out", f"{mcu_lbl} -> {lbl or 'PWM'}")

                for p in c["ports"]:
                    lbl = p.get("label", "").upper()
                    if p["type"] in ["analog_out", "analog_in"]:
                        mcu_analog = get_available_mcu_port("analog_in")
                        if mcu_analog:
                            mcu_lbl = get_mcu_port_label(mcu_analog)
                            add_edge(mcu["node_id"], mcu_analog, c["node_id"], p["id"], "analog", f"{mcu_lbl} -> {lbl or 'ANALOG'}")

                for p in c["ports"]:
                    lbl = p.get("label", "").upper()
                    if p["type"] in ["digital_in", "digital_out", "digital_in_out"]:
                        mcu_digi = get_available_mcu_port("digital_in_out")
                        if mcu_digi:
                            mcu_lbl = get_mcu_port_label(mcu_digi)
                            add_edge(mcu["node_id"], mcu_digi, c["node_id"], p["id"], "digital", f"{mcu_lbl} -> {lbl or 'DIGI'}")

        # Route servo motors directly to MCU
        if mcu:
            for motor in [c for c in components_to_route if c["type"] == "motor" and c["hw_key"] == "servo"]:
                sig = next((p["id"] for p in motor["ports"] if p["type"] == "pwm_in"), None)
                mcu_pwm = get_available_mcu_port("pwm_out")
                if sig and mcu_pwm:
                    mcu_lbl = get_mcu_port_label(mcu_pwm)
                    add_edge(mcu["node_id"], mcu_pwm, motor["node_id"], sig, "pwm_out", f"{mcu_lbl} -> SERVO_PWM")

        # Route mechanicals from Motors to Wheels/Nozzles
        mechanicals = [c for c in components_to_route if c["type"] == "mechanical"]
        mech_idx = 0
        for motor in motors:
            if mech_idx >= len(mechanicals): break
            mech_out = next((p["id"] for p in motor["ports"] if p["type"] == "mechanical_out"), None)
            if mech_out:
                mech_comp = mechanicals[mech_idx]
                mech_in = next((p["id"] for p in mech_comp["ports"] if p["type"] == "mechanical_in"), None)
                if mech_in:
                    add_edge(motor["node_id"], mech_out, mech_comp["node_id"], mech_in, "mechanical", "AXLE")
                    mech_idx += 1

        return {
            "status": "success",
            "nodes": nodes,
            "edges": edges
        }
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
