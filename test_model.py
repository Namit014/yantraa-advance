import os, requests
from dotenv import load_dotenv
load_dotenv('.env')
key = os.getenv('OPENROUTER_API_KEY')
resp = requests.post('https://openrouter.ai/api/v1/chat/completions', headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}, json={'model': 'qwen/qwen3-next-80b-a3b-instruct:free', 'messages': [{'role': 'user', 'content': 'hello'}], 'response_format': {'type': 'json_object'}})
print(resp.status_code)
print(resp.text)
