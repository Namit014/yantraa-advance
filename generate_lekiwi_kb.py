import os
import json
import urllib.request
import xml.etree.ElementTree as ET

kb_dir = os.path.join("d:\\yantraa-advance", "knowledgebase", "Mobile_Manipulator", "LeKiwi")
os.makedirs(kb_dir, exist_ok=True)

# 1. lekiwi_overview.md
overview_content = """# LeKiwi Overview

**Category:** Mobile Manipulator
**Platform:** Holonomic mobile base with an SO-100/SO-101 robotic arm.
**Controller:** Raspberry Pi 5
**Software:** HuggingFace LeRobot

LeKiwi is a low-cost, open-source mobile manipulator robot designed for teleoperation and imitation learning. It consists of a 3-omni-wheel drive system and a 6-DOF robotic arm mounted on top. It uses standard components like STS3215 servos, a Raspberry Pi 5, and USB cameras to provide a robust platform for AI robotics research.
"""
with open(os.path.join(kb_dir, "lekiwi_overview.md"), "w") as f:
    f.write(overview_content)

# 2. lekiwi_components.json
components = [
    {"name": "Omni wheels", "description": "4-inch omni-directional wheels for holonomic movement."},
    {"name": "STS3215 servos", "description": "Used for driving the omni wheels and operating the robotic arm."},
    {"name": "Servo driver", "description": "Controls the STS3215 servos."},
    {"name": "Raspberry Pi 5", "description": "Main compute unit for running LeRobot software and connecting cameras."},
    {"name": "USB cameras", "description": "Provides base and wrist visual feedback."},
    {"name": "Battery system", "description": "Provides power; configurations include a 5V laptop power bank or a 12V Li-ion battery."},
    {"name": "SO-100 / SO-101 arm", "description": "6-DOF articulated robotic arm mounted on the mobile base."},
    {"name": "Gripper", "description": "End effector attached to the robotic arm."},
    {"name": "Mounting hardware", "description": "Assorted M2, M3, and M4 screws and nuts, plus 3D printed standardized base plates."}
]
with open(os.path.join(kb_dir, "lekiwi_components.json"), "w") as f:
    json.dump(components, f, indent=4)

# 3. lekiwi_bom.json
bom = [
    {"component_name": "4-inch Omni wheels", "category": "Mechanical", "quantity": "3", "robot_subsystem": "Mobile Base"},
    {"component_name": "STS3215 servos", "category": "Actuator", "quantity": "3 (base) + 6 (arm)", "robot_subsystem": "Drive System / Arm"},
    {"component_name": "Servo driver board", "category": "Electronics", "quantity": "1", "robot_subsystem": "Control System"},
    {"component_name": "Raspberry Pi 5 (4GB)", "category": "Compute", "quantity": "1", "robot_subsystem": "Control System"},
    {"component_name": "USB Camera", "category": "Sensor", "quantity": "2", "robot_subsystem": "Vision System"},
    {"component_name": "Battery (5V Powerbank or 12V Li-ion)", "category": "Power", "quantity": "1", "robot_subsystem": "Power System"},
    {"component_name": "M2/M3/M4 Assorted Screw Set", "category": "Hardware", "quantity": "1 set", "robot_subsystem": "Structural"},
    {"component_name": "3D Printed Plates & Mounts", "category": "Mechanical", "quantity": "1 set", "robot_subsystem": "Structural"}
]
with open(os.path.join(kb_dir, "lekiwi_bom.json"), "w") as f:
    json.dump(bom, f, indent=4)

# 4. lekiwi_connections.json
connections = {
    "connections": [
        {"source": "STS3215 Servo", "target": "Wheel Hub"},
        {"source": "Wheel Hub", "target": "Omni Wheel"},
        {"source": "Battery", "target": "Servo Driver"},
        {"source": "Battery", "target": "Raspberry Pi 5"},
        {"source": "Servo Driver", "target": "Raspberry Pi 5"},
        {"source": "Servo Driver", "target": "STS3215 Servo"},
        {"source": "Raspberry Pi 5", "target": "Base USB Camera"},
        {"source": "Raspberry Pi 5", "target": "Wrist USB Camera"},
        {"source": "Raspberry Pi 5", "target": "Arm Controller (SO-100/SO-101)"}
    ]
}
with open(os.path.join(kb_dir, "lekiwi_connections.json"), "w") as f:
    json.dump(connections, f, indent=4)

# 5. lekiwi_architecture.json
architecture = {
    "name": "LeKiwi",
    "children": [
        {
            "name": "Mobile Base",
            "children": [
                {"name": "Drive System"},
                {"name": "Power System"},
                {"name": "Vision System"}
            ]
        },
        {
            "name": "SO-101 Arm",
            "children": [
                {"name": "End Effector"}
            ]
        }
    ]
}
with open(os.path.join(kb_dir, "lekiwi_architecture.json"), "w") as f:
    json.dump(architecture, f, indent=4)

# 6. Parse URDF and create lekiwi_urdf_summary.json
urdf_url = "https://raw.githubusercontent.com/SIGRobotics-UIUC/LeKiwi/main/URDF/LeKiwi.urdf"
try:
    req = urllib.request.urlopen(urdf_url)
    urdf_content = req.read().decode('utf-8')
    root = ET.fromstring(urdf_content)
    
    links = [link.attrib['name'] for link in root.findall('link')]
    joints = []
    
    for joint in root.findall('joint'):
        j_name = joint.attrib.get('name')
        j_type = joint.attrib.get('type')
        parent = joint.find('parent').attrib.get('link') if joint.find('parent') is not None else None
        child = joint.find('child').attrib.get('link') if joint.find('child') is not None else None
        joints.append({
            "name": j_name,
            "type": j_type,
            "parent": parent,
            "child": child
        })
        
    urdf_summary = {
        "robot_name": root.attrib.get("name", "Unknown"),
        "links": links,
        "joints": joints
    }
except Exception as e:
    urdf_summary = {"error": str(e)}

with open(os.path.join(kb_dir, "lekiwi_urdf_summary.json"), "w") as f:
    json.dump(urdf_summary, f, indent=4)

# 7. lekiwi_datasheet.md
datasheet_content = """# LeKiwi Datasheet

## General Specifications
- **Type:** Mobile Manipulator
- **Degrees of Freedom (DOF):** 3 (Mobile Base Holonomic) + 6 (Arm) = 9 DOF total
- **Main Controller:** Raspberry Pi 5 (4GB)

## Mobile Base
- **Drive Type:** Holonomic omni-drive (3 wheels)
- **Wheels:** 4-inch Omni wheels
- **Actuators:** STS3215 serial bus servos
- **Power:** 5V (Laptop Powerbank) or 12V (Li-ion Battery Pack)

## Manipulator (SO-100/SO-101)
- **Type:** 6-DOF Articulated Arm
- **Actuators:** STS3215 servos
- **End Effector:** Parallel Jaw Gripper

## Vision System
- **Sensors:** 2x USB Cameras
- **Placements:** 
  - Base camera for forward navigation view
  - Wrist camera for manipulation feedback
"""
with open(os.path.join(kb_dir, "lekiwi_datasheet.md"), "w") as f:
    f.write(datasheet_content)

print("Generated all files successfully.")
