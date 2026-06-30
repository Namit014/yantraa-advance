import json

# Engineering Knowledge Base & Manufacturer/Port DBs

COMPONENT_DB = {
    "Stepper Motor": {
        "category": "actuator",
        "default_voltage": "24V",
        "default_current": "1.5A",
        "power_pins": ["A+", "A-", "B+", "B-"],
        "signal_pins": [],
        "typical_driver": "Stepper Driver",
        "communication": "None",
        "mechanical_mount": "NEMA Standard"
    },
    "Arduino Mega": {
        "category": "controller",
        "default_voltage": "5V",
        "default_current": "0.5A",
        "power_pins": ["VIN", "5V", "3.3V", "GND"],
        "signal_pins": ["D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "A0", "A1", "A2", "TX", "RX", "SDA", "SCL"],
        "typical_driver": "None",
        "communication": ["UART", "I2C", "SPI"],
        "mechanical_mount": "PCB Standoffs"
    },
    "Stepper Driver": {
        "category": "electronic",
        "default_voltage": "24V",
        "default_current": "3A",
        "power_pins": ["VMOT", "GND", "VDD", "GND_LOGIC", "A+", "A-", "B+", "B-"],
        "signal_pins": ["STEP", "DIR", "EN"],
        "typical_driver": "None",
        "communication": "Pulse/Direction",
        "mechanical_mount": "Heatsink/Panel"
    },
    "Power Supply": {
        "category": "power",
        "default_voltage": "24V",
        "default_current": "10A",
        "power_pins": ["V+", "V-", "L", "N", "PE"],
        "signal_pins": [],
        "typical_driver": "None",
        "communication": "None",
        "mechanical_mount": "Panel Mount"
    }
}

MANUFACTURER_DB = {
    "TB6600": {"type": "Stepper Driver", "brand": "Generic"},
    "DRV8825": {"type": "Stepper Driver", "brand": "TI"},
    "A4988": {"type": "Stepper Driver", "brand": "Allegro"},
    "TMC2209": {"type": "Stepper Driver", "brand": "Trinamic"},
    "NEMA17": {"type": "Stepper Motor", "brand": "Generic"},
    "NEMA23": {"type": "Stepper Motor", "brand": "Generic"},
    "MG996R": {"type": "Servo Motor", "brand": "TowerPro"}
}

def get_component_specs(component_name: str) -> dict:
    """Retrieve specs and pins from the KB for a component."""
    # Try exact match
    if component_name in COMPONENT_DB:
        return COMPONENT_DB[component_name]
    
    # Try substring match
    for key, val in COMPONENT_DB.items():
        if key.lower() in component_name.lower():
            return val
            
    # Default fallback
    return {
        "category": "unknown",
        "default_voltage": "Unknown",
        "default_current": "Unknown",
        "power_pins": ["VCC", "GND"],
        "signal_pins": ["SIG"],
        "communication": "Unknown"
    }
