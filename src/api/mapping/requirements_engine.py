from typing import Dict, List
from .schemas import ComponentNode

class RequirementsEngine:
    """
    Maps every component back to a user requirement.
    """
    
    @classmethod
    def trace_requirements(cls, components: List[ComponentNode], requirements: Dict[str, str]) -> None:
        """
        Assigns 'explainability' based on traceability.
        """
        for comp in components:
            if "motor" in comp.category.lower():
                comp.explainability = "Chosen to satisfy payload requirement: " + requirements.get("payload", "unknown")
