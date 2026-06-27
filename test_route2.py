import requests

try:
    res = requests.post("http://localhost:8000/api/chat/route", json={"prompt": "build scara robot"})
    print("Status Code:", res.status_code)
    print("Response:", res.text)
except Exception as e:
    print("Error:", e)
