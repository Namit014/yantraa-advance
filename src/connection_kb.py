# src/connection_kb.py

CONNECTION_RULES = [
    "Microcontrollers connect to motor drivers via PWM or UART.",
    "Motor drivers connect to motors via power lines.",
    "Power supply connects to all components requiring Vin.",
    "Sensors connect to microcontrollers via I2C, SPI, Analog, or Digital signals.",
    "Communication modules connect to microcontrollers via UART, SPI, or I2C.",
    "Displays connect to microcontrollers via I2C, SPI, or parallel data lines."
]

def validate_connections(nodes, wires):
    """
    Validates connections against rules.
    Returns:
        valid_wires: list of validated/repaired wire dictionaries
        validation_logs: list of warning/error messages
    """
    # Create lookup map for node types
    node_types = {}
    for n in nodes:
        node_types[n["id"]] = n.get("type", "other").lower()

    valid_wires = []
    validation_logs = []

    for wire in wires:
        if not isinstance(wire, dict):
            continue
            
        from_obj = wire.get("from", {})
        to_obj = wire.get("to", {})
        
        if not isinstance(from_obj, dict) or not isinstance(to_obj, dict):
            continue

        # Check source and target nodes
        src_id = from_obj.get("nodeId")
        tgt_id = to_obj.get("nodeId")
        
        if not src_id or not tgt_id:
            continue
        
        src_type = node_types.get(src_id, "other")
        tgt_type = node_types.get(tgt_id, "other")
        
        wire_type = wire.get("type", "signal")
        if not isinstance(wire_type, str):
            wire_type = "signal"
        wire_type = wire_type.lower()
        
        # Rule 1: Microcontrollers connect to motor drivers (module/ic-chip), not direct to motor
        if src_type == "microcontroller" and tgt_type == "motor":
            validation_logs.append(
                f"Validation Warning: Direct connection from Microcontroller '{src_id}' "
                f"to Motor '{tgt_id}' is invalid. Should go through a motor driver."
            )
            
        # Rule 2: Motor drivers connect to motors via power lines
        if src_type == "ic-chip" and tgt_type == "motor" and wire_type not in ["power", "pwm", "signal"]:
            wire["type"] = "power"
            wire["color"] = "#FF4444"
            validation_logs.append(
                f"Auto-Repaired: Corrected wire type to 'power' and color to '#FF4444' "
                f"for Motor Driver '{src_id}' -> Motor '{tgt_id}' connection."
            )
            
        # Rule 3: Power supply connects to all components requiring Vin
        if src_type == "power" and wire_type not in ["power", "ground"]:
            wire["type"] = "power"
            wire["color"] = "#FF4444"
            validation_logs.append(
                f"Auto-Repaired: Corrected wire type to 'power' and color to '#FF4444' "
                f"for Power Supply '{src_id}' output."
            )

        valid_wires.append(wire)

    return valid_wires, validation_logs
