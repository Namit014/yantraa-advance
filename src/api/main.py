from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import sys
import os
import io
import asyncio
from dotenv import load_dotenv

# Always load .env from the project root, regardless of working directory
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(_project_root, ".env"))

# Force UTF-8 encoding for standard output/error to avoid charmap crashes on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# Add the parent directory (src) to sys.path to allow importing from local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Add the api directory so sub-packages can be found
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from fastapi.middleware.cors import CORSMiddleware
from retriever import Retriever
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the Retriever on startup
    app.state.retriever = Retriever()
    yield
    # Shutdown logic (if any)

# Initialize FastAPI app
app = FastAPI(
    title="Yantra Agentic RAG API",
    description="FastAPI interface for the Yantra RAG Pipeline",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
# Default includes production domain + localhost for development
_default_origins = "http://localhost:3000,https://labs.yantraa.tech,https://www.labs.yantraa.tech,https://yantraa.tech,https://www.yantraa.tech,https://api.yantraa.tech"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", _default_origins).split(",") if o.strip()]
print(f"[Yantra API] CORS Allowed Origins configured in env: {ALLOWED_ORIGINS}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register sub-routers
try:
    from connections.generate import router as connections_router
    app.include_router(connections_router)
    print("[Yantra API] Registered /api/connections/generate")
except Exception as _e:
    print(f"[Yantra API] WARNING: Could not load connections router: {_e}")

from design import router as design_router
app.include_router(design_router)
print("[Yantra API] Registered /api/design")

try:
    from generate import router as generate_router
    app.include_router(generate_router)
    print("[Yantra API] Registered /api/generate-cad")
except Exception as _e:
    print(f"[Yantra API] WARNING: Could not load generate router: {_e}")

try:
    from mapping.generate import router as mapping_router
    app.include_router(mapping_router)
    print("[Yantra API] Registered /api/mapping/build-graph")
except Exception as _e:
    print(f"[Yantra API] WARNING: Could not load mapping router: {_e}")

try:
    from ros2_export import router as ros2_export_router
    app.include_router(ros2_export_router)
    print("[Yantra API] Registered /api/export-ros2")
except Exception as _e:
    print(f"[Yantra API] WARNING: Could not load ros2_export router: {_e}")

# Define Pydantic models for JSON request/response validation
class QueryRequest(BaseModel):
    query: str

from typing import Optional, List

class QueryResponse(BaseModel):
    response: str
    status: str = "success"
    cad_available: bool = False
    cad_url: Optional[str] = None
    fallback_used: bool = False
    source_urls: List[str] = []

from fastapi import Request

@app.post("/api/ask", response_model=QueryResponse)
async def ask_question(request: Request, payload: QueryRequest):
    """
    Executes the following workflow:
    1. User Query (received in JSON payload)
    2. FastAPI Endpoint (this route)
    3. Query Processing (handled inside Retriever: intent extraction and keyword optimization)
    4. Vector Database (Qdrant search inside Retriever)
    5. Retrieve Relevant Chunks (filtered by relevance floor inside Retriever)
    6. LLM (OpenAI / Ollama / HuggingFace via invoke_yantra_ai inside Retriever)
    7. Generate Response (final synthesis)
    8. Return JSON Response (returned below)
    """
    try:
        if not payload.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty.")

        retriever = request.app.state.retriever

        # Execute the RAG workflow asynchronously off the event loop
        final_answer, cad_available, cad_url, fallback_used, source_urls = await asyncio.get_event_loop().run_in_executor(
            None, retriever.ask, payload.query
        )

        # Return JSON Response
        return QueryResponse(
            response=final_answer, 
            cad_available=cad_available, 
            cad_url=cad_url,
            fallback_used=fallback_used,
            source_urls=source_urls
        )

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return QueryResponse(
            response=f"An error occurred in the backend: {str(e)}\n\n{error_details}",
            status="error",
            cad_available=False
        )

@app.get("/search", response_model=QueryResponse)
async def search_question(request: Request, query: str):
    """
    GET endpoint equivalent for easy browser testing.
    Usage: http://localhost:8000/search?query=your+question
    """
    try:
        if not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty.")

        retriever = request.app.state.retriever

        # Execute the RAG workflow asynchronously off the event loop
        final_answer, cad_available, cad_url, fallback_used, source_urls = await asyncio.get_event_loop().run_in_executor(
            None, retriever.ask, query
        )

        # Return JSON Response
        return QueryResponse(
            response=final_answer, 
            cad_available=cad_available, 
            cad_url=cad_url,
            fallback_used=fallback_used,
            source_urls=source_urls
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import FileResponse
import glob
import re

@app.get("/api/cad/{filename}")
async def get_cad_file(filename: str):
    """Serve CAD files dynamically from the knowledgebase directory with traversal protection."""
    if not re.match(r'^[a-zA-Z0-9_\-]+\.(step|stp|STEP|STP)$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    cad_base_dir = os.path.join(_project_root, "knowledgebase")
    
    # Search all subdirectories for the file
    search_pattern = os.path.join(cad_base_dir, "**", filename)
    matches = glob.glob(search_pattern, recursive=True)
    
    if matches and os.path.exists(matches[0]):
        return FileResponse(matches[0])
    
    raise HTTPException(status_code=404, detail="CAD file not found in knowledgebase")

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "ok", "message": "API is running."}

if __name__ == "__main__":
    import uvicorn
    # Allow running directly using `python src/api/main.py`
    print("ALL ROUTES BEFORE RUNNING:", [getattr(r, "path", getattr(r, "name", str(r))) for r in app.routes])
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
