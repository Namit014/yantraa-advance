import os
import time
import base64
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

router = APIRouter()

class GenerateCADRequest(BaseModel):
    prompt: str
    filename: str

from dotenv import load_dotenv

def get_zoo_tokens() -> List[str]:
    # Reload .env file dynamically to pick up any key modifications
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    load_dotenv(os.path.join(project_root, ".env"), override=True)
    
    raw_tokens = os.environ.get("ZOO_API_TOKENS", "")
    tokens = [t.strip() for t in raw_tokens.split(",") if t.strip()]
    
    # Fallback to ZOO_API_TOKEN or KITTYCAD_API_TOKEN
    single_token = os.environ.get("ZOO_API_TOKEN") or os.environ.get("KITTYCAD_API_TOKEN")
    if single_token and single_token not in tokens:
        tokens.insert(0, single_token)
    return tokens

@router.post("/api/generate-cad")
async def generate_cad(req: GenerateCADRequest):
    prompt = req.prompt.strip()
    filename = req.filename.strip()
    if not prompt or not filename:
        raise HTTPException(status_code=400, detail="Prompt and filename are required.")
    
    # Ensure it ends with .step
    if not filename.lower().endswith(".step"):
        filename += ".step"
        
    tokens = get_zoo_tokens()
    if not tokens:
        raise HTTPException(
            status_code=400,
            detail="No Zoo API tokens configured. Please set ZOO_API_TOKENS in your .env file."
        )
        
    last_error = ""
    for token in tokens:
        print(f"[Zoo API] Attempting generation with token: {token[:10]}...")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": prompt,
            "output_format": "step"
        }
        
        try:
            # Step 1: Submit Text-to-CAD job
            res = requests.post(
                "https://api.zoo.dev/ml/text-to-cad",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            # If billing (402) or rate limit (429) errors, rotate to next token
            if res.status_code in (402, 429):
                err_msg = f"Status {res.status_code}: {res.text}"
                print(f"[Zoo API] Token limit reached ({err_msg}). Rotating to next token...")
                last_error = err_msg
                continue
                
            res.raise_for_status()
            job_data = res.json()
            job_id = job_data.get("id")
            if not job_id:
                raise Exception("No operation ID returned by Zoo API.")
                
            print(f"[Zoo API] Job submitted successfully. ID: {job_id}")
            
            # Step 2: Poll for completion
            max_attempts = 30
            attempt = 0
            completed_job_data = None
            
            while attempt < max_attempts:
                time.sleep(5)
                attempt += 1
                
                status_res = requests.get(
                    f"https://api.zoo.dev/async/operations/{job_id}",
                    headers=headers,
                    timeout=20
                )
                status_res.raise_for_status()
                status_data = status_res.json()
                
                status = status_data.get("status", "").lower()
                print(f"[Zoo API] Job {job_id} status check {attempt}/{max_attempts}: {status}")
                
                if status == "completed":
                    completed_job_data = status_data
                    break
                elif status == "failed":
                    err_info = status_data.get("error", "Unknown Zoo API error.")
                    raise Exception(f"Zoo Text-to-CAD generation failed: {err_info}")
            
            if not completed_job_data:
                raise Exception("Timeout waiting for Zoo Text-to-CAD generation.")
                
            # Step 3: Extract outputs and save files
            outputs = completed_job_data.get("outputs", {})
            if not outputs:
                raise Exception("Zoo API returned no outputs on completion.")
                
            step_key = None
            for key in outputs.keys():
                if key.lower().endswith(".step"):
                    step_key = key
                    break
            
            if not step_key:
                step_key = list(outputs.keys())[0]
                
            base64_data = outputs[step_key]
            file_bytes = base64.b64decode(base64_data)
            
            # Write to backend models directory
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            backend_dir = os.path.join(project_root, "knowledgebase", "CAD_Models")
            os.makedirs(backend_dir, exist_ok=True)
            backend_path = os.path.join(backend_dir, filename)
            with open(backend_path, "wb") as f:
                f.write(file_bytes)
                
            # Write to frontend public directory
            frontend_dir = os.path.join(project_root, "frontend", "public", "cad")
            os.makedirs(frontend_dir, exist_ok=True)
            frontend_path = os.path.join(frontend_dir, filename)
            with open(frontend_path, "wb") as f:
                f.write(file_bytes)
                
            print(f"[Zoo API] Successfully generated and saved: {filename}")
            return {
                "status": "success",
                "cad_url": f"/cad/{filename}"
            }
            
        except Exception as e:
            print(f"[Zoo API] Error with token: {e}")
            last_error = str(e)
            continue
            
    # If we exited the loop, all tokens failed
    raise HTTPException(
        status_code=500,
        detail=f"Failed to generate CAD model using Zoo API. Last error: {last_error}"
    )
