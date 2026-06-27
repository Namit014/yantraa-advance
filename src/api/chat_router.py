import os
import sys
from fastapi import APIRouter
from pydantic import BaseModel
from scoring_engine import ScoringEngine

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from faq_retriever import FAQRetriever

router = APIRouter()
engine = ScoringEngine()
retriever = FAQRetriever()

class PromptRequest(BaseModel):
    prompt: str

@router.post("/route")
async def route_prompt(req: PromptRequest):
    scores = engine.score_prompt(req.prompt)
    if scores["overall"] >= 4:
        return {"status": "success", "action": "route_to_ai", "scores": scores}
    else:
        faqs = retriever.retrieve_clarification_faqs(req.prompt, scores, top_k=3)
        return {"status": "success", "action": "route_to_clarification", "scores": scores, "faqs": faqs}
