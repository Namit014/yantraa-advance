import os
import json

base_dir = "d:\\yantraa-advance\\knowledgebase\\Humanoid_Robot"
op2_dir = os.path.join(base_dir, "NimbRo_OP2")
op2x_dir = os.path.join(base_dir, "NimbRo_OP2X")

os.makedirs(op2_dir, exist_ok=True)
os.makedirs(op2x_dir, exist_ok=True)
os.makedirs(os.path.join(op2_dir, "CAD"), exist_ok=True)
os.makedirs(os.path.join(op2x_dir, "CAD"), exist_ok=True)

# 1. nimbro_overview.md
overview_content = """# NimbRo-OP2 Overview

**Category:** Humanoid Robot
**Platform:** Bipedal Humanoid (RoboCup TeenSize / AdultSize class)
**Controller:** Main PC (Mini-ITX / NUC) + Subcontroller (OpenCR / CM730)
**Actuators:** Dynamixel Smart Servos

The NimbRo-OP2 (and its successor OP2X) is a 3D-printed, open-source humanoid robot designed for research and RoboCup competition. It features a lightweight structure primarily made of 3D-printed parts reinforced with carbon fiber or aluminum where necessary. It has approximately 20 degrees of freedom (DOF) to perform complex bipedal locomotion and manipulation.

## Specifications
- **Robot Name:** NimbRo-OP2 / OP2X
- **Robot Type:** Humanoid Robot
- **Degrees of Freedom:** ~20 (6 per leg, 3 per arm, 2 neck)
- **Drive Type:** Direct Drive / Timing Belt (depends on joint)
- **Actuators:** Robotis Dynamixel (MX-106, MX-64, XH series)
- **Vision System:** Wide-angle USB Camera
"""
with open(os.path.join(op2_dir, "nimbro_overview.md"), "w") as f:
    f.write(overview_content)
with open(os.path.join(op2x_dir, "nimbro_overview.md"), "w") as f:
    f.write(overview_content)

# 2. nimbro_components.json
components = [
    {"name": "Torso", "description": "Main structural body housing the PC, battery, and subcontroller."},
    {"name": "Head", "description": "Contains the vision system (camera) and pan-tilt neck servos."},
    {"name": "Arms", "description": "3-DOF manipulators (shoulder pitch, shoulder roll, elbow pitch)."},
    {"name": "Legs", "description": "6-DOF bipedal legs (hip yaw, hip roll, hip pitch, knee pitch, ankle pitch, ankle roll)."},
    {"name": "Dynamixel Servos", "description": "Smart actuators providing joint movement and feedback."},
    {"name": "Main PC", "description": "High-level compute unit for vision processing and motion planning."},
    {"name": "Subcontroller", "description": "Low-level board communicating with Dynamixel bus and reading IMU data."},
    {"name": "Camera", "description": "USB camera for ball/goal tracking."},
    {"name": "IMU", "description": "Inertial Measurement Unit for balancing and posture control."},
    {"name": "LiPo Battery", "description": "High-current power source for motors and PC."}
]
with open(os.path.join(op2_dir, "nimbro_components.json"), "w") as f:
    json.dump(components, f, indent=4)
with open(os.path.join(op2x_dir, "nimbro_components.json"), "w") as f:
    json.dump(components, f, indent=4)

# 3. nimbro_bom.json
bom = [
    {"component_name": "Dynamixel MX-106 / XH-430", "category": "Actuator", "quantity": "12", "robot_subsystem": "Legs"},
    {"component_name": "Dynamixel MX-64", "category": "Actuator", "quantity": "8", "robot_subsystem": "Arms / Neck"},
    {"component_name": "Main PC (Intel NUC/BRIX)", "category": "Compute", "quantity": "1", "robot_subsystem": "Control System"},
    {"LiPo Battery (3S / 4S)": "Power", "quantity": "1", "robot_subsystem": "Power System"},
    {"component_name": "Subcontroller Board", "category": "Electronics", "quantity": "1", "robot_subsystem": "Control System"},
    {"component_name": "Logitech C920 / WebCam", "category": "Sensor", "quantity": "1", "robot_subsystem": "Vision System"},
    {"component_name": "6-axis IMU", "category": "Sensor", "quantity": "1", "robot_subsystem": "Control System"},
    {"component_name": "3D Printed Exoskeleton", "category": "Structure", "quantity": "1 set", "robot_subsystem": "Structure"}
]
with open(os.path.join(op2_dir, "nimbro_bom.json"), "w") as f:
    json.dump(bom, f, indent=4)
with open(os.path.join(op2x_dir, "nimbro_bom.json"), "w") as f:
    json.dump(bom, f, indent=4)

# 4. nimbro_connections.json
connections = {
    "connections": [
        {"source": "LiPo Battery", "target": "Subcontroller", "connection_type": "Electrical (Power)"},
        {"source": "LiPo Battery", "target": "Main PC", "connection_type": "Electrical (Power via Regulator)"},
        {"source": "Main PC", "target": "Subcontroller", "connection_type": "Data (USB / Serial)"},
        {"source": "Main PC", "target": "Camera", "connection_type": "Data (USB)"},
        {"source": "Subcontroller", "target": "IMU", "connection_type": "Data (I2C/SPI)"},
        {"source": "Subcontroller", "target": "Dynamixel Servos", "connection_type": "Data + Power (RS485 Daisy Chain)"},
        {"source": "Dynamixel Servos", "target": "Joint Linkage", "connection_type": "Mechanical (Horn / Frame)"}
    ]
}
with open(os.path.join(op2_dir, "nimbro_connections.json"), "w") as f:
    json.dump(connections, f, indent=4)
with open(os.path.join(op2x_dir, "nimbro_connections.json"), "w") as f:
    json.dump(connections, f, indent=4)

# 5. nimbro_architecture.json
architecture = {
    "name": "NimbRo Humanoid",
    "children": [
        {
            "name": "Head",
            "children": [{"name": "Neck Pan/Tilt Servos"}, {"name": "Camera"}]
        },
        {
            "name": "Torso",
            "children": [{"name": "Main PC"}, {"name": "Subcontroller & IMU"}, {"name": "Battery"}]
        },
        {
            "name": "Left Arm",
            "children": [{"name": "Shoulder Pitch/Roll"}, {"name": "Elbow Pitch"}]
        },
        {
            "name": "Right Arm",
            "children": [{"name": "Shoulder Pitch/Roll"}, {"name": "Elbow Pitch"}]
        },
        {
            "name": "Left Leg",
            "children": [{"name": "Hip Yaw/Roll/Pitch"}, {"name": "Knee Pitch"}, {"name": "Ankle Pitch/Roll"}]
        },
        {
            "name": "Right Leg",
            "children": [{"name": "Hip Yaw/Roll/Pitch"}, {"name": "Knee Pitch"}, {"name": "Ankle Pitch/Roll"}]
        }
    ]
}
with open(os.path.join(op2_dir, "nimbro_architecture.json"), "w") as f:
    json.dump(architecture, f, indent=4)
with open(os.path.join(op2x_dir, "nimbro_architecture.json"), "w") as f:
    json.dump(architecture, f, indent=4)

print("Generated NimbRo knowledgebase files.")
