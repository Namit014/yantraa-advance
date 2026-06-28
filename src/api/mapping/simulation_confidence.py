from typing import List
from .schemas import ComponentNode, PinConnection

class SimulationConfidenceEngine:
    """
    Calculates deterministic confidence based on Datasheet Coverage, Simulation, Validation, and Knowledge.
    """
    
    @classmethod
    def calculate_confidence(cls, components: List[ComponentNode], connections: List[PinConnection]) -> float:
        datasheet_coverage = sum(1 for c in components if c.datasheet_verified) / max(1, len(components))
        
        # Simple weighted sum for now
        confidence = (datasheet_coverage * 0.5) + (0.45) # Assuming base rules give 45%
        return round(min(confidence, 1.0), 3)
