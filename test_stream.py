import requests
url = "http://127.0.0.1:8000/api/cad/Full_System_A-2403-02.step"
response = requests.get(url)
print(response.status_code)
print(len(response.content))
