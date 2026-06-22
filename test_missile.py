import requests
import json
import time

try:
    print("Querying /api/design for 'Build a detailed Military missile robot'...")
    res = requests.post("http://localhost:8000/api/design", json={"query": "Build a detailed Military missile robot"}, timeout=120)
    data = res.json()
    print("CAD Available:", data.get("cad_available"))
    print("CAD URLs:", data.get("cad_urls"))
    print(f"Subsystems generated: {len(data.get('subsystems', []))}")
    print(f"Connections generated: {len(data.get('connections', []))}")
    print(f"Validation errors/warnings: {len(data.get('validation', []))}")
    print("\nSample Component from Subsystems:")
    if data.get('subsystems') and data['subsystems'][0].get('components'):
        print(json.dumps(data['subsystems'][0]['components'][0], indent=2))
except Exception as e:
    print(f"Error: {e}")
