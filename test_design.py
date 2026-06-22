import sys
sys.path.append('src')

from fastapi.testclient import TestClient
from api.main import app
import traceback

try:
    print("Initializing TestClient...")
    client = TestClient(app)
    print("Making request to /api/design...")
    response = client.post("/api/design", json={"query": "Make a robot arm"})
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print("TestClient Failed!")
    traceback.print_exc()
