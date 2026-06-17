import json
import re
from pathlib import Path

def extract_bom(markdown_path):
    with open(markdown_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    graph = {
        "robots": {},
        "components": {},
        "edges": []
    }
    
    current_robot = None
    current_family = None
    
    for line in lines:
        if "Feetech motors" in line:
            current_family = "Feetech STS3215"
            graph["components"][current_family] = {"type": "Motor"}
        elif "Dynamixel servo motors" in line:
            current_family = "Dynamixel"
            graph["components"][current_family] = {"type": "Motor"}
            
        robot_match = re.match(r'^### \[(.*?)\]', line)
        if robot_match:
            current_robot = robot_match.group(1).split('/')[-1]
            graph["robots"][current_robot] = {"name": current_robot}
            if current_family:
                graph["edges"].append({
                    "source": current_family, 
                    "target": current_robot, 
                    "relation": "powers"
                })
                
        # Camera matching
        if current_robot and '|' in line and ']' in line:
            camera_match = re.search(r'\|\s*\[?(.*?)(?:\]|\s*\|)', line)
            if camera_match:
                item = camera_match.group(1).strip()
                if "Webcam" in item or "RealSense" in item or "Module" in item or "1080P" in item:
                    graph["components"][item] = {"type": "Camera"}
                    graph["edges"].append({
                        "source": item,
                        "target": current_robot,
                        "relation": "compatible_with"
                    })
                
        # Gripper matching
        if current_robot and ("Gripper" in current_robot or "PincOpen" in current_robot):
            graph["components"][current_robot] = {"type": "Gripper"}
            if current_robot in graph["robots"]:
                del graph["robots"][current_robot] # Reclassify as component

    return graph

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    md_path = base_dir / "knowledgebase" / "cobot_robot" / "lerobotdepot.md"
    out_dir = base_dir / "knowledgebase" / "Robots_MetaData"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "component_graph.json"
    
    if not md_path.exists():
        print(f"Error: Could not find {md_path}")
    else:
        graph = extract_bom(md_path)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(graph, f, indent=4)
        print(f"Component graph generated with {len(graph['robots'])} robots and {len(graph['components'])} components.")
