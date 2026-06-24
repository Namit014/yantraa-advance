import os
import sys
import uuid
import json
import subprocess
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

# Ensure src/ is on sys.path
_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from llm import invoke_yantra_ai

router = APIRouter()

class GenerateCadRequest(BaseModel):
    query: str

class GenerateCadResponse(BaseModel):
    cad_url: Optional[str] = None
    status: str
    message: str

def _strip_markdown_code(text: str) -> str:
    """Remove ```python fences"""
    text = text.strip()
    if text.startswith("```python"):
        text = text[len("```python"):]
    elif text.startswith("```"):
        text = text[len("```"):]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def do_generate_cad(query: str) -> tuple[bool, Optional[str]]:
    filename = f"gen_{uuid.uuid4().hex[:8]}.step"
    cad_dir = os.path.abspath(os.path.join(_src_dir, "..", "frontend", "public", "cad"))
    os.makedirs(cad_dir, exist_ok=True)
    out_path = os.path.join(cad_dir, filename)
    out_path_escaped = out_path.replace("\\\\", "\\\\\\\\") # Python string escaping for paths

    system_prompt = """You are a CAD engineer AI that writes Python code using the `build123d` library to generate 3D models.
Write a COMPLETE Python script that imports build123d, generates the requested 3D object, and exports it to the specified file path.
Use `from build123d import *`. 
IMPORTANT: Use standard Python operators for boolean operations: `-` for difference, `+` for union, `*` for intersection (e.g., `final_shape = cube - hole`). Do NOT use non-existent functions like `Difference()`.
Your script MUST end with a command exporting the final shape(s) or assembly to the file path provided in the prompt. For example: `export_step(my_shape, "path/to/file.step")` or `my_shape.export_step("path/to/file.step")`.
Do NOT include any explanations or markdown outside the code block. ONLY provide the Python code."""

    prompt = f"""User request: {query}
Output file path: {out_path_escaped}
Write the build123d python script."""

    print(f"[api/generate_cad] Requesting code for: {query}")
    try:
        raw_code = invoke_yantra_ai(
            prompt=prompt,
            system_prompt=system_prompt,
            response_format="text"
        )
        script_code = _strip_markdown_code(raw_code)
        
        # Write to temp file
        temp_script_path = os.path.join(cad_dir, "temp_cad_gen.py")
        with open(temp_script_path, "w", encoding="utf-8") as f:
            f.write(script_code)
            
        print("[api/generate_cad] Generated code, executing...")
        
        # Execute using python 3.10 which has build123d installed
        result = subprocess.run(
            ["py", "-3.10", temp_script_path], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            print(f"[api/generate_cad] Execution failed:\\n{result.stderr}")
            return False, None
            
        if os.path.exists(out_path):
            print(f"[api/generate_cad] Success: {filename}")
            return True, f"/cad/{filename}"
        else:
            return False, None

    except Exception as e:
        print(f"[api/generate_cad] Exception: {e}")
        return False, None

@router.post("/api/generate_cad", response_model=GenerateCadResponse)
async def generate_cad_endpoint(request: Request, body: GenerateCadRequest):
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    success, url = do_generate_cad(query)
    if success:
        return GenerateCadResponse(status="success", message="Generated", cad_url=url)
    return GenerateCadResponse(status="error", message="Failed to generate CAD", cad_url=None)
