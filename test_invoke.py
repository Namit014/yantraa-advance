import os
import sys

# Ensure src/ is on sys.path
_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from llm import invoke_yantra_ai
from api.design import synthesis_system

try:
    print("Testing invoke_yantra_ai...")
    res = invoke_yantra_ai(
        prompt="USER REQUEST: scara robot\n",
        system_prompt=synthesis_system,
        response_format="json_object",
        model="gemini-2.5-flash"
    )
    print("SUCCESS!")
    print(res[:500])
except Exception as e:
    print(f"FAILED: {e}")
