import os
import sys
import json
import requests
from dotenv import load_dotenv
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

load_dotenv()

# Path setup
_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from src.mapping.component_registry import ComponentRegistry
from src.mapping.component_normalizer import ComponentNormalizer
from src.mapping.dependency_engine import DependencyEngine
from src.mapping.template_engine import TemplateEngine
from src.mapping.compatibility_engine import CompatibilityEngine
from src.mapping.port_mapper import PortMapper
from src.mapping.graph_builder import GraphBuilder
from src.mapping.validator import Validator
from src.mapping.confidence import ConfidenceEngine
from src.mapping.optimizer import Optimizer
from src.mapping.learning.mapping_history import MappingHistory

# OpenRouter config
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

class ComponentIn(BaseModel):
    id: str
    name: str
    type: str = "other"

class GenerateRequest(BaseModel):
    components: List[ComponentIn]
    prompt: str

class FeedbackRequest(BaseModel):
    input_components: List[str]
    generated_graph: dict
    user_modified: bool
    accepted: bool

router = APIRouter()

def _call_llm_explanation(graph_data: dict, prompt: str) -> str:
    """Uses LLM only to explain the generated graph."""
    if not OPENROUTER_API_KEY:
        return "Explanation unavailable: OpenRouter API key not configured."
        
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Yantra Connections",
    }
    
    system = (
        "You are an expert robotics engineer. The user provided components, and our deterministic rules engine "
        "has generated a connection graph. Your job is ONLY to write a brief, human-readable summary of how these "
        "components connect (power, control, data). Do NOT generate JSON. Do NOT generate graph data."
    )
    
    user = f"User Request: {prompt}\n\nGenerated Graph Data:\n{json.dumps(graph_data, indent=2)}\n\nPlease summarize this architecture."
    
    payload = {
        "model": "google/gemini-flash-1.5",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
    }
    
    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        print(f"[connections/generate] LLM Explanation failed: {exc}")
        return "A deterministic architecture was successfully generated, but AI explanation failed."


@router.post("/api/connections/generate")
async def generate_connections(request: GenerateRequest):
    if not request.components:
        raise HTTPException(status_code=400, detail="No components provided.")

    # Instantiate the pipeline engines
    registry = ComponentRegistry()
    normalizer = ComponentNormalizer()
    dependency_engine = DependencyEngine(registry)
    template_engine = TemplateEngine()
    compatibility_engine = CompatibilityEngine()
    port_mapper = PortMapper()
    graph_builder = GraphBuilder(registry, compatibility_engine, port_mapper)
    validator = Validator()
    confidence_engine = ConfidenceEngine()
    optimizer = Optimizer()

    # Pass 1: Component Normalization
    normalized_ids = [normalizer.normalize(c.name) for c in request.components]
    normalized_ids = [c for c in normalized_ids if c != "unknown"]

    # Pass 2: Dependency Expansion
    expanded_ids = dependency_engine.expand_dependencies(normalized_ids)

    # Pass 3 & 4: Architecture Detection & Template Matching
    arch_name = template_engine.detect_architecture(expanded_ids, registry)
    templated_ids = template_engine.apply_template(arch_name, expanded_ids, registry)

    # Pass 5, 6 & 7: Graph Construction (incorporates Rules, Port Mapping, Compatibility)
    G = graph_builder.build_graph(templated_ids)

    # Pass 8: Validation
    issues = validator.validate(G, registry)

    # Pass 9: Confidence Scoring
    G = confidence_engine.calculate(G)

    # Pass 9b: Graph Optimization
    G = optimizer.optimize(G)

    # Convert to JSON
    graph_json = graph_builder.to_json(G)
    
    # Run LLM ONLY for explanation
    explanation = _call_llm_explanation(graph_json, request.prompt)
    
    # Pass 10: Auto Layout will be handled by ELK.js on the frontend
    # We return the nodes/wires and the explanation text
    
    graph_json["explanation"] = explanation
    graph_json["issues"] = issues
    graph_json["architecture_detected"] = arch_name

    return graph_json

@router.post("/api/connections/feedback")
async def save_connection_feedback(request: FeedbackRequest):
    history = MappingHistory()
    history.record_graph(
        input_components=request.input_components,
        generated_graph=request.generated_graph,
        user_modified=request.user_modified,
        accepted=request.accepted
    )
    return {"status": "success"}
