from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import io
import zipfile
import xml.etree.ElementTree as ET

router = APIRouter()

class ReactFlowNode(BaseModel):
    id: str
    type: str
    position: Dict[str, float]
    data: Dict[str, Any]

class ReactFlowEdge(BaseModel):
    id: str
    source: str
    target: str

class ROS2ExportRequest(BaseModel):
    nodes: List[ReactFlowNode]
    edges: List[ReactFlowEdge]

def generate_urdf(nodes: List[ReactFlowNode], edges: List[ReactFlowEdge]) -> str:
    """Generate a URDF file containing ros2_control tags for hardware components."""
    root = ET.Element("robot", name="yantra_robot")
    
    # Base link
    ET.SubElement(root, "link", name="base_link")
    
    # Identify actuators and sensors for ros2_control
    ros2_control = ET.SubElement(root, "ros2_control", name="YantraHardwareInterface", type="system")
    hardware = ET.SubElement(ros2_control, "hardware")
    ET.SubElement(hardware, "plugin").text = "mock_components/GenericSystem"
    
    joint_count = 1
    
    for node in nodes:
        node_name = node.data.get("label", node.id).replace(" ", "_").lower()
        node_type = node.data.get("type", "unknown")
        
        if node_type == "actuator":
            # Add a joint to the URDF
            joint_name = f"joint_{node_name}"
            joint = ET.SubElement(root, "joint", name=joint_name, type="revolute")
            ET.SubElement(joint, "parent", link="base_link")
            link_name = f"link_{node_name}"
            ET.SubElement(root, "link", name=link_name)
            ET.SubElement(joint, "child", link=link_name)
            
            # Add ros2_control joint interface
            ctrl_joint = ET.SubElement(ros2_control, "joint", name=joint_name)
            ET.SubElement(ctrl_joint, "command_interface", name="position")
            ET.SubElement(ctrl_joint, "command_interface", name="velocity")
            ET.SubElement(ctrl_joint, "state_interface", name="position")
            ET.SubElement(ctrl_joint, "state_interface", name="velocity")
            
        elif node_type == "sensor":
            sensor = ET.SubElement(ros2_control, "sensor", name=node_name)
            ET.SubElement(sensor, "state_interface", name="value")
            
    # Pretty formatting
    from xml.dom import minidom
    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    return xmlstr

def generate_launch_py(nodes: List[ReactFlowNode], edges: List[ReactFlowEdge]) -> str:
    """Generate a simple ROS2 Python launch file."""
    launch_code = """import os
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': '<load urdf here>'}]
        ),
"""
    # Find software/controller nodes to start as dummy generic nodes
    for node in nodes:
        if node.data.get("type") in ["software", "controller"]:
            node_name = node.data.get("label", node.id).replace(" ", "_").lower()
            launch_code += f"""        Node(
            package='dummy_package',
            executable='dummy_node',
            name='{node_name}',
            output='screen'
        ),\n"""
    
    launch_code += "    ])\n"
    return launch_code

def generate_package_xml() -> str:
    return """<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>yantra_generated_robot</name>
  <version>0.0.0</version>
  <description>Auto-generated ROS2 workspace from Yantra AI Component Mapping</description>
  <maintainer email="user@todo.todo">Yantra User</maintainer>
  <license>TODO</license>

  <buildtool_depend>ament_cmake</buildtool_depend>
  <exec_depend>rclcpp</exec_depend>
  <exec_depend>ros2_control</exec_depend>
  <exec_depend>moveit_core</exec_depend>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
"""

def generate_cmakelists() -> str:
    return """cmake_minimum_required(VERSION 3.8)
project(yantra_generated_robot)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)

install(DIRECTORY
  launch
  urdf
  config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
"""

@router.post("/api/export-ros2")
async def export_ros2_workspace(request: ROS2ExportRequest):
    try:
        urdf_content = generate_urdf(request.nodes, request.edges)
        launch_content = generate_launch_py(request.nodes, request.edges)
        package_xml = generate_package_xml()
        cmakelists = generate_cmakelists()
        
        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            zip_file.writestr("yantra_generated_robot/urdf/robot.urdf", urdf_content)
            zip_file.writestr("yantra_generated_robot/launch/robot.launch.py", launch_content)
            zip_file.writestr("yantra_generated_robot/package.xml", package_xml)
            zip_file.writestr("yantra_generated_robot/CMakeLists.txt", cmakelists)
            
            # Placeholder for MoveIt2 kinematics
            zip_file.writestr("yantra_generated_robot/config/kinematics.yaml", "# Auto-generated MoveIt2 kinematics configuration\\n")
            
        zip_buffer.seek(0)
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=yantra_ros2_workspace.zip"
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate ROS2 workspace: {str(e)}")
