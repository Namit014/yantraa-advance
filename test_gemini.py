import os, sys, json
_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, _src_dir)

from llm import _call_gemini
with open('src/api/design.py', 'r', encoding='utf-8') as f:
    code = f.read()
import re
match = re.search(r'synthesis_system = \"\"\"(.*?)\"\"\"', code, re.DOTALL)
sys_prompt = match.group(1)

messages = [{'role': 'system', 'content': sys_prompt}, {'role': 'user', 'content': 'USER REQUEST: scara robot\n'}]
try:
    res = _call_gemini(messages, response_format='json_object')
    print('SUCCESS', res[:100])
except Exception as e:
    print('FAILED:', e)
