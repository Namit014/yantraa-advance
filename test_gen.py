import requests
payload = {
  "components": [
    {"id": "A-2525-01", "name": "A-2525-01", "type": "other"},
    {"id": "A-2433-01", "name": "A-2433-01_Motor_Driver", "type": "module"},
    {"id": "mot1", "name": "Stepper Motor", "type": "motor"}
  ],
  "prompt": "Test"
}
try:
    res = requests.post("http://localhost:8000/api/connections/generate", json=payload)
    print("Status:", res.status_code)
    print("Response:", res.text)
except Exception as e:
    print("Error:", e)
