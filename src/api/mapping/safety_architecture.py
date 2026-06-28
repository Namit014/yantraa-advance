from typing import List
from .schemas import ComponentNode, PinConnection

class SafetyArchitectureValidator:
    """
    Enforces industrial robotics safety standards.
    """
    
    @classmethod
    def validate_safety(cls, components: List[ComponentNode], connections: List[PinConnection]) -> List[str]:
        errors = []
        categories = {c.category.lower() for c in components if c.category}
        
        if "emergency_stop" not in categories:
            errors.append("Safety Violation: No Emergency Stop present in the architecture.")
            
        if "fuse" not in categories and "circuit_breaker" not in categories:
            errors.append("Safety Violation: No Overcurrent Protection present.")
            
        return errors
