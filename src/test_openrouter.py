import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get('OPENROUTER_API_KEY')

headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

for model in ['nvidia/nemotron-3-super-120b-a12b:free', 'qwen/qwen3-next-80b-a3b-instruct:free', 'openai/gpt-oss-120b:free']:
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': 'hello'}],
        'max_tokens': 10
    }
    r = requests.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=payload)
    print(model, r.status_code, r.text[:100])
