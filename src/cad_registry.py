import os
import json

# Maps common aliases to the exact filename of step/stp files present in knowledgebase
KNOWN_CADS = {
    # Robotic Arm / Manipulator
    "arm": "Full_System_A-2363-01.step",
    "robotic arm": "Full_System_A-2363-01.step",
    "6dof arm": "Full_System_A-2363-01.step",
    "manipulator": "Full_System_A-2363-01.step",
    "articulated": "Articulated_robot_cad.STEP",
    "cobot": "Articulated_robot_cad.STEP",
    "collaborative": "Articulated_robot_cad.STEP",
    
    # AGV / AMR / Mobile Robot
    "agv": "Auto_guided_vehical_Robot.step",
    "autonomous mobile": "autonomous_mobile_robot.stp",
    "amr": "autonomous_mobile_robot.stp",
    "mobile robot": "autonomous_mobile_robot.stp",
    
    # Delta
    "delta": "DeltaRobot2.STEP",
    "delta robot": "DeltaRobot2.STEP",
    "parallel": "DeltaRobot2.STEP",
    
    # Cartesian
    "cartesian": "cartesian_robot.STEP",
    "gantry": "cartesian_robot.STEP",
    
    # Other Robots
    "painting": "Painting_Robot.step",
    "scara": "scara_robot_cad.stp",
    "welding": "welding_robot.stp",
    "inspection": "inspection_robot_cad.STEP",
    "humanoid": "Robot_humanoid.step",
    "machine tending": "machine_tending_robot.stp",
    "in-pipe": "InPipeInspectionRobot.STEP",
    "in pipe": "InPipeInspectionRobot.STEP",
    "pipeline": "InPipeInspectionRobot.STEP",
    "corrosion": "InPipeInspectionRobot.STEP",
    
    # Motor Controllers
    "odrive": "odrive_s1.step",
    "odrive s1": "odrive_s1.step",
    "odrive pro": "odrive_pro.step",
    "odrive micro": "odrive_micro.step"
}

_hebi_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "knowledgebase", "Robots_MetaData", "hebi_components.json"))

def get_known_cads() -> dict:
    cads = KNOWN_CADS.copy()
    try:
        if os.path.exists(_hebi_path):
            with open(_hebi_path, "r", encoding="utf-8") as f:
                hebi_data = json.load(f)
                for comp in hebi_data.get("components", []):
                    name = comp.get("name", "")
                    filename = comp.get("filename", "")
                    if name and filename:
                        cads[name.lower()] = filename
                        cads[name.lower().replace("-", " ")] = filename
    except Exception as e:
        print(f"[cad_registry] Error loading HEBI cads: {e}")
    return cads
