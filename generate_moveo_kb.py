import os
import json

kb_dir = os.path.join("d:\\yantraa-advance", "knowledgebase", "Articulated_Robot", "BCN3D_Moveo")
os.makedirs(kb_dir, exist_ok=True)

# 1. moveo_overview.md
overview_content = """# BCN3D Moveo Overview

**Category:** Articulated Robot
**Platform:** 5-DOF robotic arm.
**Controller:** Arduino Mega 2560 + RAMPS 1.4
**Software:** Marlin / GRBL (Customized for kinematics)

BCN3D Moveo is an open-source, fully 3D printed robotic arm designed for educational purposes by BCN3D Technologies and the Departament d’Ensenyament from the Generalitat de Catalunya. It provides a low-cost, reproducible platform for learning mechanical design, automatism, and industrial programming.

## Specifications
- **Robot Name:** BCN3D Moveo
- **Robot Type:** Articulated Robot
- **Degrees of Freedom:** 5
- **End Effector Type:** Parallel Jaw Gripper
- **Controller Type:** Arduino Mega
- **Actuator Type:** NEMA Stepper Motors
- **Transmission Type:** Timing Belt and Pulley
- **Manufacturing Method:** 3D Printing (FDM)
"""
with open(os.path.join(kb_dir, "moveo_overview.md"), "w") as f:
    f.write(overview_content)

# 2. moveo_datasheet.md
datasheet_content = """# BCN3D Moveo Datasheet

## General Specifications
- **Type:** Articulated Robotic Arm
- **Degrees of Freedom (DOF):** 5
- **Main Controller:** Arduino Mega 2560
- **Shield:** RAMPS 1.4
- **Stepper Drivers:** Pololu A4988 / DRV8825

## Actuation
- **Actuators:** NEMA 17 Stepper Motors
- **Transmission:** GT2 Timing Belts and Pulleys, Planetary Gears (depending on joint)

## Mechanical Structure
- **Links:** Base, Shoulder, Upper Arm, Elbow, Forearm, Wrist, Gripper
- **Materials:** PLA/ABS/PETG (3D Printed)
- **Joint Hardware:** 608ZZ Bearings, M3/M4/M8 Fasteners, 8mm smooth rods

## End Effector
- **Type:** Parallel Jaw Gripper
- **Actuation:** Micro servo or stepper motor
"""
with open(os.path.join(kb_dir, "moveo_datasheet.md"), "w") as f:
    f.write(datasheet_content)

# 3. moveo_components.json
components = [
    {"name": "Base", "description": "Stationary mount of the robot."},
    {"name": "Rotating Base", "description": "Provides the base panning motion (Axis 1)."},
    {"name": "Shoulder", "description": "First vertical articulating joint (Axis 2)."},
    {"name": "Upper Arm", "description": "Main structural link between shoulder and elbow."},
    {"name": "Elbow", "description": "Second vertical articulating joint (Axis 3)."},
    {"name": "Forearm", "description": "Structural link between elbow and wrist."},
    {"name": "Wrist", "description": "Provides pitch and roll motion (Axis 4 and 5)."},
    {"name": "Gripper", "description": "Parallel jaw end effector for manipulation."},
    {"name": "NEMA17 Stepper Motors", "description": "Primary actuators for the robot joints."},
    {"name": "Timing Belts", "description": "GT2 closed-loop timing belts for power transmission."},
    {"name": "Timing Pulleys", "description": "GT2 pulleys attaching to stepper motor shafts and joint shafts."},
    {"name": "Shafts", "description": "8mm smooth rods used as pivot points for joints."},
    {"name": "Bearings", "description": "608ZZ and 688ZZ bearings to support rotating shafts."},
    {"name": "Arduino Mega", "description": "Primary microcontroller executing kinematics and G-code."},
    {"name": "RAMPS 1.4", "description": "Shield providing stepper driver sockets and power distribution."},
    {"name": "Power Supply", "description": "12V/24V DC power supply for motors and electronics."}
]
with open(os.path.join(kb_dir, "moveo_components.json"), "w") as f:
    json.dump(components, f, indent=4)

# 4. moveo_bom.json
bom = [
    {"component_name": "NEMA17 Stepper Motor", "category": "Actuator", "quantity": "5", "robot_subsystem": "Drive System"},
    {"component_name": "GT2 Timing Belt", "category": "Mechanical", "quantity": "4", "robot_subsystem": "Transmission"},
    {"component_name": "GT2 Pulley (16T/20T)", "category": "Mechanical", "quantity": "8", "robot_subsystem": "Transmission"},
    {"component_name": "608ZZ Bearing", "category": "Mechanical", "quantity": "10+", "robot_subsystem": "Joints"},
    {"component_name": "8mm Smooth Rod", "category": "Mechanical", "quantity": "5", "robot_subsystem": "Joints"},
    {"component_name": "Arduino Mega 2560", "category": "Compute", "quantity": "1", "robot_subsystem": "Control System"},
    {"component_name": "RAMPS 1.4 Shield", "category": "Electronics", "quantity": "1", "robot_subsystem": "Control System"},
    {"component_name": "A4988/DRV8825 Stepper Driver", "category": "Electronics", "quantity": "5", "robot_subsystem": "Control System"},
    {"component_name": "12V 10A+ Power Supply", "category": "Power", "quantity": "1", "robot_subsystem": "Power System"},
    {"component_name": "3D Printed Structural Parts", "category": "Structure", "quantity": "1 set", "robot_subsystem": "Structure"}
]
with open(os.path.join(kb_dir, "moveo_bom.json"), "w") as f:
    json.dump(bom, f, indent=4)

# 5. moveo_connections.json
connections = {
    "connections": [
        {"source": "NEMA17 Stepper Motor", "target": "Timing Pulley", "connection_type": "Mechanical (Shaft coupling)"},
        {"source": "Timing Pulley", "target": "Timing Belt", "connection_type": "Mechanical (Mesh)"},
        {"source": "Timing Belt", "target": "Joint Shaft", "connection_type": "Mechanical (Pulley)"},
        {"source": "Joint Shaft", "target": "Bearing", "connection_type": "Mechanical (Support)"},
        {"source": "Bearing", "target": "Robot Link", "connection_type": "Mechanical (Press fit)"},
        {"source": "Arduino Mega", "target": "RAMPS 1.4", "connection_type": "Electrical (Header pins)"},
        {"source": "RAMPS 1.4", "target": "Stepper Driver", "connection_type": "Electrical (Socket)"},
        {"source": "Stepper Driver", "target": "NEMA17 Stepper Motor", "connection_type": "Electrical (Wiring)"},
        {"source": "Power Supply", "target": "RAMPS 1.4", "connection_type": "Power (Screw terminal)"}
    ]
}
with open(os.path.join(kb_dir, "moveo_connections.json"), "w") as f:
    json.dump(connections, f, indent=4)

# 6. moveo_architecture.json
architecture = {
    "name": "BCN3D Moveo",
    "children": [
        {
            "name": "Base Subsystem",
            "children": [
                {"name": "Base Mount"},
                {"name": "Axis 1 (Pan)"}
            ]
        },
        {
            "name": "Arm Assembly",
            "children": [
                {"name": "Shoulder (Axis 2)"},
                {"name": "Upper Arm"},
                {"name": "Elbow (Axis 3)"},
                {"name": "Forearm"}
            ]
        },
        {
            "name": "Wrist & End Effector",
            "children": [
                {"name": "Wrist Pitch (Axis 4)"},
                {"name": "Wrist Roll (Axis 5)"},
                {"name": "Gripper"}
            ]
        },
        {
            "name": "Control Electronics",
            "children": [
                {"name": "Arduino Mega"},
                {"name": "RAMPS 1.4"}
            ]
        }
    ]
}
with open(os.path.join(kb_dir, "moveo_architecture.json"), "w") as f:
    json.dump(architecture, f, indent=4)

# 7. moveo_assembly_tree.json
assembly_tree = {
    "name": "Moveo",
    "children": [
        {
            "name": "Base",
            "children": [
                {
                    "name": "Shoulder",
                    "children": [
                        {
                            "name": "Upper Arm",
                            "children": [
                                {
                                    "name": "Elbow",
                                    "children": [
                                        {
                                            "name": "Forearm",
                                            "children": [
                                                {
                                                    "name": "Wrist",
                                                    "children": [
                                                        {"name": "Gripper"}
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}
with open(os.path.join(kb_dir, "moveo_assembly_tree.json"), "w") as f:
    json.dump(assembly_tree, f, indent=4)

# 8. moveo_joint_structure.json
joint_structure = [
    {
        "joint_name": "Axis 1 (Base Pan)",
        "parent_link": "Base",
        "child_link": "Rotating Base",
        "actuator": "NEMA 17 Stepper",
        "transmission": "Planetary Gear / Belt"
    },
    {
        "joint_name": "Axis 2 (Shoulder Pitch)",
        "parent_link": "Rotating Base",
        "child_link": "Upper Arm",
        "actuator": "NEMA 17 Stepper",
        "transmission": "Timing Belt and Pulley"
    },
    {
        "joint_name": "Axis 3 (Elbow Pitch)",
        "parent_link": "Upper Arm",
        "child_link": "Forearm",
        "actuator": "NEMA 17 Stepper",
        "transmission": "Timing Belt and Pulley"
    },
    {
        "joint_name": "Axis 4 (Wrist Pitch)",
        "parent_link": "Forearm",
        "child_link": "Wrist Base",
        "actuator": "NEMA 17 Stepper",
        "transmission": "Timing Belt and Pulley"
    },
    {
        "joint_name": "Axis 5 (Wrist Roll)",
        "parent_link": "Wrist Base",
        "child_link": "Gripper Mount",
        "actuator": "NEMA 17 Stepper",
        "transmission": "Direct Drive / Belt"
    }
]
with open(os.path.join(kb_dir, "moveo_joint_structure.json"), "w") as f:
    json.dump(joint_structure, f, indent=4)

# 9. moveo_cad_metadata.json
cad_metadata = {
    "repository_assemblies": [
        "Base_Assembly.SLDASM",
        "Axis2_Shoulder_Assembly.SLDASM",
        "Axis3_Elbow_Assembly.SLDASM",
        "Axis4_Wrist_Assembly.SLDASM",
        "Axis5_Gripper_Assembly.SLDASM"
    ],
    "part_categories": [
        "3D Printed Structural",
        "Fasteners (M3, M4, M8)",
        "Bearings (608ZZ, 688ZZ)",
        "Shafts (8mm)",
        "Motors (NEMA17)",
        "Pulleys (GT2)"
    ],
    "mechanical_subsystems": [
        "Base Pivot",
        "Shoulder Joint",
        "Elbow Joint",
        "Wrist Pitch/Roll",
        "Gripper Assembly"
    ]
}
with open(os.path.join(kb_dir, "moveo_cad_metadata.json"), "w") as f:
    json.dump(cad_metadata, f, indent=4)

print("Generated all Moveo files successfully.")
