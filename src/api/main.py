from fastapi import FastAPI, HTTPException
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
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS, 
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

try:
    from design import router as design_router
    app.include_router(design_router)
    print("[Yantra API] Registered /api/design")
except Exception as _e:
    print(f"[Yantra API] WARNING: Could not load design router: {_e}")


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
        raise HTTPException(status_code=500, detail=str(e))

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
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
