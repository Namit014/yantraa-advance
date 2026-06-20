import urllib.request
try:
    response = urllib.request.urlopen("http://127.0.0.1:8000/docs")
    print(f"Backend is up! Status: {response.status}")
except Exception as e:
    print(f"Backend is down: {e}")
