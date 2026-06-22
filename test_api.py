import requests
import json

response = requests.post(
    "http://localhost:8000/api/design",
    json={"query": "build an articulated robot"},
    headers={"Content-Type": "application/json"}
)

print(json.dumps(response.json(), indent=2))
