from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import sys
import os
import io
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
    # Initialize the Retriever
    # This will load the sentence transformer model and connect to the Qdrant Database
    retriever = Retriever()
    app.state.retriever = retriever
    yield

# Initialize FastAPI app
app = FastAPI(
    title="Yantra Agentic RAG API",
    description="FastAPI interface for the Yantra RAG Pipeline",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
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

try:
    from design import router as design_router
    app.include_router(design_router)
    print("[Yantra API] Registered /api/design")
except Exception as _e:
    print(f"[Yantra API] WARNING: Could not load design router: {_e}")

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


# Define Pydantic models for JSON request/response validation
class QueryRequest(BaseModel):
    query: str

from typing import Optional

class QueryResponse(BaseModel):
    response: str
    status: str = "success"
    cad_available: bool = False
    cad_url: Optional[str] = None

@app.post("/api/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest, req: Request):
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
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty.")

        # Execute the RAG workflow
        retriever = req.app.state.retriever
        final_answer, cad_available, cad_url = retriever.ask(request.query)

        # Return JSON Response
        return QueryResponse(
            response=final_answer, 
            cad_available=cad_available, 
            cad_url=cad_url
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search", response_model=QueryResponse)
async def search_question(query: str, req: Request):
    """
    GET endpoint equivalent for easy browser testing.
    Usage: http://localhost:8000/search?query=your+question
    """
    try:
        if not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty.")

        # Execute the RAG workflow
        retriever = req.app.state.retriever
        final_answer, cad_available, cad_url = retriever.ask(query)

        # Return JSON Response
        return QueryResponse(
            response=final_answer, 
            cad_available=cad_available, 
            cad_url=cad_url
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import FileResponse
import glob

@app.get("/api/cad/{filename}")
async def get_cad_file(filename: str):
    """Serve CAD files dynamically from the knowledgebase directory."""
    cad_base_dir = os.path.join(_project_root, "knowledgebase", "CAD_Models")
    
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
