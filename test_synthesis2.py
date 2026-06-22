import os
import requests
import json

url = "http://127.0.0.1:8000/api/design"
payload = {"query": "Build a Robotic Dog"}
response = requests.post(url, json=payload)
print(response.status_code)
print(response.text)
