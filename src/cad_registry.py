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
_synced_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "knowledgebase", "Robots_MetaData", "synced_cads.json"))

def get_known_cads() -> dict:
    # Initialize with list wrappers for KNOWN_CADS
    cads = {k: [v] if isinstance(v, str) else v for k, v in KNOWN_CADS.items()}
    try:
        if os.path.exists(_hebi_path):
            with open(_hebi_path, "r", encoding="utf-8") as f:
                hebi_data = json.load(f)
                for comp in hebi_data.get("components", []):
                    name = comp.get("name", "")
                    filename = comp.get("filename", "")
                    if name and filename:
                        for key in (name.lower(), name.lower().replace("-", " ")):
                            if key not in cads:
                                cads[key] = []
                            if filename not in cads[key]:
                                cads[key].append(filename)
                        
        if os.path.exists(_synced_path):
            with open(_synced_path, "r", encoding="utf-8") as f:
                synced_data = json.load(f)
                for name, filename in synced_data.items():
                    if name not in cads:
                        cads[name] = []
                    # handle both legacy string format and new list format
                    if isinstance(filename, list):
                        for f_item in filename:
                            if f_item not in cads[name]:
                                cads[name].append(f_item)
                    elif isinstance(filename, str):
                        if filename not in cads[name]:
                            cads[name].append(filename)
                    
    except Exception as e:
        print(f"[cad_registry] Error loading CAD registries: {e}")
    return cads

def _save_cad_registry(updated_cads: dict):
    """
    Saves dynamically added CAD models to the synced_cads.json registry.
    We isolate these from the hardcoded dictionary and HEBI list.
    """
    os.makedirs(os.path.dirname(_synced_path), exist_ok=True)
    
    synced_only = {}
    for k, v in updated_cads.items():
        original_v = KNOWN_CADS.get(k)
        if original_v is None:
            synced_only[k] = v
        else:
            original_list = [original_v] if isinstance(original_v, str) else original_v
            if isinstance(v, list) and len(v) > len(original_list):
                synced_only[k] = v
            
    with open(_synced_path, "w", encoding="utf-8") as f:
        json.dump(synced_only, f, indent=4)
