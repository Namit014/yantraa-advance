import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

def get_category(folder_name):
    lower_name = folder_name.lower()
    if 'actuator' in lower_name or 'shoulder' in lower_name:
        return 'Actuators'
    if 'gripper' in lower_name or 'spool' in lower_name:
        return 'End_Effectors'
    if 'board' in lower_name or 'battery' in lower_name or 'driver' in lower_name or 'ethernet' in lower_name or 'pof' in lower_name:
        return 'Electronics_and_Power'
    if 'camera' in lower_name:
        return 'Sensors'
    if 'maggie' in lower_name or 'tready' in lower_name:
        return 'Full_Systems'
    
    # Default structural components
    return 'Structural_and_Mounts'

def main():
    base_dir = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    temp_repo_dir = base_dir / "temp_hebi_cad"
    cad_dest_dir = base_dir / "frontend" / "public" / "cad"
    kb_dest_dir = base_dir / "knowledgebase" / "Hebi_CAD"
    metadata_dir = base_dir / "knowledgebase" / "Robots_MetaData"
    
    cad_dest_dir.mkdir(parents=True, exist_ok=True)
    kb_dest_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    
    print("1. Cloning HebiRobotics/hebi-cad (excluding large LFS blobs by default)...")
    if temp_repo_dir.exists():
        # Handle Windows permission errors on .git read-only files by forcing removal
        def onerror(func, path, exc_info):
            import stat
            if not os.access(path, os.W_OK):
                os.chmod(path, stat.S_IWUSR)
                func(path)
            else:
                raise
        shutil.rmtree(temp_repo_dir, onerror=onerror)
        
    env = os.environ.copy()
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    
    subprocess.run(
        ["git", "clone", "https://github.com/HebiRobotics/hebi-cad.git", str(temp_repo_dir)],
        env=env,
        check=True
    )
    
    print("2. Pulling only .step and .stp files via Git LFS...")
    subprocess.run(
        ["git", "lfs", "pull", "--include=*.step,*.stp"],
        cwd=str(temp_repo_dir),
        check=True
    )
    
    print("3. Processing files and generating metadata...")
    hebi_metadata = {
        "categories": {},
        "components": []
    }
    
    for item in temp_repo_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            category = get_category(item.name)
            
            if category not in hebi_metadata["categories"]:
                hebi_metadata["categories"][category] = []
                
            # Find all .step / .stp files in this directory
            step_files = list(item.glob("*.step")) + list(item.glob("*.stp"))
            
            if step_files:
                for step_file in step_files:
                    # 1. Copy to frontend/public/cad
                    dest_file_frontend = cad_dest_dir / step_file.name
                    shutil.copy2(step_file, dest_file_frontend)
                    
                    # 2. Copy to knowledgebase/Hebi_CAD/<Category>/
                    category_dir = kb_dest_dir / category
                    category_dir.mkdir(parents=True, exist_ok=True)
                    dest_file_kb = category_dir / step_file.name
                    shutil.copy2(step_file, dest_file_kb)
                    
                    component_info = {
                        "name": step_file.stem,
                        "folder": item.name,
                        "category": category,
                        "filename": step_file.name,
                        "type": "Hardware"
                    }
                    hebi_metadata["components"].append(component_info)
                    hebi_metadata["categories"][category].append(step_file.stem)
                    print(f"  -> Copied {step_file.name} to {category}")

    metadata_file = metadata_dir / "hebi_components.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(hebi_metadata, f, indent=4)
        
    print(f"Metadata saved to {metadata_file}")
    
    print("4. Cleaning up temporary repository...")
    def onerror(func, path, exc_info):
        import stat
        if not os.access(path, os.W_OK):
            os.chmod(path, stat.S_IWUSR)
            func(path)
        else:
            raise
    shutil.rmtree(temp_repo_dir, onerror=onerror)
    
    print("Done! HEBI CAD integration complete.")

if __name__ == "__main__":
    main()
