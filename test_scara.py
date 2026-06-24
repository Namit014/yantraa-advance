import sys
import os
import json
from fastapi.testclient import TestClient

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from api.main import app  # Assuming main.py exports the FastAPI app

client = TestClient(app)

def test_scara_robot():
    print("Sending request for a SCARA robot...")
    response = client.post(
        "/api/design",
        json={"query": "Generate a SCARA robot for assembly tasks."}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("\n--- TEST SUCCESS ---")
        print("Generated Subsystems & Components:")
        for sub in data.get("subsystems", []):
            print(f"Subsystem: {sub['name']}")
            for comp in sub.get("components", []):
                print(f"  - [{comp.get('id')}] {comp.get('name')} | Role: {comp.get('role')} | Interface: {comp.get('interface')}")
                
        print("\nConnections:")
        for conn in data.get("connections", []):
            print(f"  - {conn.get('from')} --[{conn.get('protocol')}]--> {conn.get('to')}")
            
        print("\nValidation Errors/Warnings:")
        for v in data.get("validation", []):
            print(f"  - [{v.get('type')}] {v.get('message')}")
            
        with open("test_scara_output.json", "w") as f:
            json.dump(data, f, indent=2)
        print("\nFull JSON saved to test_scara_output.json")
    else:
        print(f"Failed! Status: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_scara_robot()
