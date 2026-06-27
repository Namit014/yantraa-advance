import sys
sys.path.append('src')
from llm import invoke_yantra_ai

try:
    print(invoke_yantra_ai("Test", response_format="json_object"))
except Exception as e:
    print(f"ERROR: {e}")
