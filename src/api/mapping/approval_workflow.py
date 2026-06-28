from enum import Enum
from typing import List, Dict

class GraphState(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    RELEASED = "RELEASED"

class ApprovalWorkflowEngine:
    """
    Manages the lifecycle of the generated graph architecture.
    """
    
    @classmethod
    def get_required_signatures(cls) -> List[str]:
        return ["Electrical", "Mechanical", "Controls", "Safety", "Manufacturing"]
        
    @classmethod
    def approve_graph(cls, signatures_collected: List[str]) -> GraphState:
        required = cls.get_required_signatures()
        if all(req in signatures_collected for req in required):
            return GraphState.APPROVED
        return GraphState.VALIDATED
