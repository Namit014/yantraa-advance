import requests

payload = {
    "components": [
        {
            "id": "1",
            "name": "Arduino Uno",
            "category": "controller",
            "connects_to": []
        },
        {
            "id": "2",
            "name": "Servo Motor",
            "category": "actuator",
            "connects_to": ["Arduino Uno"]
        }
    ]
}

try:
    res = requests.post("http://localhost:8000/api/mapping/build-graph", json=payload)
    print(res.status_code)
    print(res.json())
except Exception as e:
    print(f"Error: {e}")
