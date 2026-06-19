import requests
url = "http://127.0.0.1:8000/api/design"
payload = {"query": "Continue"}
response = requests.post(url, json=payload)
print(response.status_code)
print(response.text)
