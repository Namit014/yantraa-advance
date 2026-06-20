import sys
import os
sys.path.append('src')

from fastapi.testclient import TestClient
from api.main import app
import traceback

try:
    client = TestClient(app)
    response = client.post("/api/ask", json={"query": "What is a robot?"})
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print("TestClient Failed!")
    traceback.print_exc()
