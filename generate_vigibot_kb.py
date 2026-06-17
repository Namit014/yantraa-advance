import os
import json

kb_dir = os.path.join("d:\\yantraa-advance", "knowledgebase", "Autonomous_Mobile_Robot", "Vigibot")
os.makedirs(kb_dir, exist_ok=True)

# 1. vigibot_overview.md
overview_content = """# Vigibot (VigiCAD) Overview

**Category:** Autonomous Mobile Robot (AMR)
**Platform:** 4WD Differential Drive Platform with Pan-Tilt Camera
**Controller:** Raspberry Pi
**Software:** Vigibot OS / Web Interface

Vigibot is an open-source, easily accessible mobile robot platform designed for telepresence, remote monitoring, and autonomous navigation. The standard VigiCAD model features a 4-wheel drive chassis, an integrated Raspberry Pi for control and streaming, and a pan-tilt camera system for wide field-of-view monitoring. It can optionally be equipped with a gripper or arm extension for manipulation.

## Specifications
- **Robot Name:** Vigibot
- **Robot Type:** Autonomous Mobile Robot
- **Drive Type:** 4WD Differential Drive
- **Controller:** Raspberry Pi (Zero / 3 / 4)
- **Vision System:** Pan-Tilt Camera
- **Optional End Effector:** Gripper
"""
with open(os.path.join(kb_dir, "vigibot_overview.md"), "w") as f:
    f.write(overview_content)

# 2. vigibot_datasheet.md
datasheet_content = """# Vigibot Datasheet

## General Specifications
- **Type:** Autonomous Mobile Robot
- **Locomotion:** 4WD Differential Drive
- **Main Controller:** Raspberry Pi
- **Motor Driver:** L298N / TB6612FNG or similar

## Vision & Sensors
- **Camera:** Raspberry Pi Camera Module (v2 or HQ)
- **Camera Mount:** Pan and Tilt mechanisms driven by micro servos
- **Optional Sensors:** Ultrasonic (HC-SR04), IR obstacle sensors

## Mechanical Structure
- **Chassis:** 3D Printed or Laser Cut acrylic plates
- **Actuators:** 4x DC Gear Motors (TT Motors)
- **Wheels:** 4x Rubber tires with plastic rims
- **Servos:** SG90 / MG90S micro servos for Pan-Tilt and optional Gripper

## Power
- **Battery:** 2x 18650 Li-ion cells or 2S LiPo battery
- **Power Distribution:** 5V UBEC or step-down converter for Raspberry Pi
"""
with open(os.path.join(kb_dir, "vigibot_datasheet.md"), "w") as f:
    f.write(datasheet_content)

# 3. vigibot_components.json
components = [
    {"name": "Chassis", "description": "Main structural body holding all electronics and motors."},
    {"name": "Wheel", "description": "Rubber tire on a plastic rim for locomotion."},
    {"name": "DC Motor", "description": "TT gear motor providing drive power to the wheels."},
    {"name": "Motor Driver", "description": "H-bridge controller (e.g. L298N) controlling DC motors."},
    {"name": "Battery", "description": "Power source, typically 18650 cells or LiPo."},
    {"name": "Raspberry Pi", "description": "Main compute unit handling video streaming, networking, and hardware control."},
    {"name": "Camera Module", "description": "Captures video for telepresence and vision processing."},
    {"name": "Pan Servo", "description": "Micro servo controlling horizontal camera movement."},
    {"name": "Tilt Servo", "description": "Micro servo controlling vertical camera movement."},
    {"name": "Gripper", "description": "Optional end effector for grabbing objects."},
    {"name": "Arm Extension", "description": "Optional linkage to extend gripper reach."},
    {"name": "Power Distribution Components", "description": "Voltage regulators (UBEC) and switches."},
    {"name": "Mounting Brackets", "description": "3D printed parts holding sensors, servos, and camera."},
    {"name": "Fasteners", "description": "M2/M3 screws, nuts, and standoffs."}
]
with open(os.path.join(kb_dir, "vigibot_components.json"), "w") as f:
    json.dump(components, f, indent=4)

# 4. vigibot_bom.json
bom = [
    {"component_name": "Chassis Plate", "category": "Mechanical", "quantity": "1 set", "robot_subsystem": "Chassis"},
    {"component_name": "DC Gear Motor (TT Motor)", "category": "Actuator", "quantity": "4", "robot_subsystem": "Drive System"},
    {"component_name": "Robot Wheel", "category": "Mechanical", "quantity": "4", "robot_subsystem": "Drive System"},
    {"component_name": "L298N / TB6612 Motor Driver", "category": "Electronics", "quantity": "1", "robot_subsystem": "Drive System"},
    {"component_name": "Raspberry Pi", "category": "Compute", "quantity": "1", "robot_subsystem": "Control System"},
    {"component_name": "Micro Servo (SG90/MG90S)", "category": "Actuator", "quantity": "2-3", "robot_subsystem": "Vision System / Manipulation"},
    {"component_name": "Raspberry Pi Camera", "category": "Sensor", "quantity": "1", "robot_subsystem": "Vision System"},
    {"component_name": "18650 Battery Pack", "category": "Power", "quantity": "1", "robot_subsystem": "Power System"},
    {"component_name": "5V Step-Down Converter", "category": "Power", "quantity": "1", "robot_subsystem": "Power System"},
    {"component_name": "M3 Standoffs & Screws", "category": "Hardware", "quantity": "1 set", "robot_subsystem": "Structure"}
]
with open(os.path.join(kb_dir, "vigibot_bom.json"), "w") as f:
    json.dump(bom, f, indent=4)

# 5. vigibot_connections.json
connections = {
    "connections": [
        {"source": "Battery", "target": "Power Distribution Components", "connection_type": "Electrical (Power)"},
        {"source": "Power Distribution Components", "target": "Motor Driver", "connection_type": "Electrical (Power)"},
        {"source": "Power Distribution Components", "target": "Raspberry Pi", "connection_type": "Electrical (5V Power)"},
        {"source": "Raspberry Pi", "target": "Motor Driver", "connection_type": "Logic (PWM/GPIO)"},
        {"source": "Motor Driver", "target": "DC Motor", "connection_type": "Electrical (High Current)"},
        {"source": "DC Motor", "target": "Wheel", "connection_type": "Mechanical (Shaft)"},
        {"source": "Raspberry Pi", "target": "Camera Module", "connection_type": "Data (CSI Ribbon Cable)"},
        {"source": "Raspberry Pi", "target": "Pan Servo", "connection_type": "Logic (PWM)"},
        {"source": "Raspberry Pi", "target": "Tilt Servo", "connection_type": "Logic (PWM)"},
        {"source": "Pan Servo", "target": "Mounting Brackets", "connection_type": "Mechanical (Mount)"},
        {"source": "Tilt Servo", "target": "Camera Module", "connection_type": "Mechanical (Mount)"},
        {"source": "Raspberry Pi", "target": "Gripper", "connection_type": "Logic (PWM)"}
    ]
}
with open(os.path.join(kb_dir, "vigibot_connections.json"), "w") as f:
    json.dump(connections, f, indent=4)

# 6. vigibot_architecture.json
architecture = {
    "name": "Vigibot",
    "children": [
        {
            "name": "Chassis",
            "children": [
                {"name": "Base Plates"},
                {"name": "Mounting Brackets"}
            ]
        },
        {
            "name": "Drive System",
            "children": [
                {"name": "DC Motors"},
                {"name": "Wheels"},
                {"name": "Motor Driver"}
            ]
        },
        {
            "name": "Power System",
            "children": [
                {"name": "Battery"},
                {"name": "Power Distribution Components"}
            ]
        },
        {
            "name": "Vision System",
            "children": [
                {"name": "Camera Module"},
                {"name": "Pan Servo"},
                {"name": "Tilt Servo"}
            ]
        },
        {
            "name": "Control System",
            "children": [
                {"name": "Raspberry Pi"}
            ]
        },
        {
            "name": "Optional Manipulation System",
            "children": [
                {"name": "Arm Extension"},
                {"name": "Gripper"}
            ]
        }
    ]
}
with open(os.path.join(kb_dir, "vigibot_architecture.json"), "w") as f:
    json.dump(architecture, f, indent=4)

# 7. vigibot_subsystems.json
subsystems = {
    "Drive_System": [
        "DC Motor",
        "Wheel",
        "Motor Driver"
    ],
    "Vision_System": [
        "Camera Module",
        "Pan Servo",
        "Tilt Servo"
    ],
    "Control_System": [
        "Raspberry Pi"
    ],
    "Power_System": [
        "Battery",
        "Power Distribution Components"
    ],
    "Manipulation_System": [
        "Gripper",
        "Arm Extension"
    ],
    "Structure": [
        "Chassis",
        "Mounting Brackets",
        "Fasteners"
    ]
}
with open(os.path.join(kb_dir, "vigibot_subsystems.json"), "w") as f:
    json.dump(subsystems, f, indent=4)

# 8. vigibot_cad_metadata.json
cad_metadata = {
    "repository_assemblies": [
        "Vigibot_Main_Assembly.step",
        "Pan_Tilt_Subassembly.step",
        "Drive_Train_Subassembly.step",
        "Gripper_Subassembly.step"
    ],
    "part_categories": [
        "Chassis Plates",
        "Motor Mounts",
        "Camera Mounts",
        "Wheels",
        "Servos",
        "Fasteners"
    ],
    "mechanical_subsystems": [
        "Drive Train",
        "Pan-Tilt Unit",
        "End Effector / Gripper",
        "Electronics Deck"
    ]
}
with open(os.path.join(kb_dir, "vigibot_cad_metadata.json"), "w") as f:
    json.dump(cad_metadata, f, indent=4)

print("Generated all Vigibot knowledge files successfully.")
