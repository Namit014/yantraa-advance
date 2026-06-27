import requests
try:
    response = requests.post("http://localhost:8000/api/design", json={"query": "build an scara robot"})
    print("Status:", response.status_code)
    print("Body:", response.json())
except Exception as e:
    print("Error:", e)
