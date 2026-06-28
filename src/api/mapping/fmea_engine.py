from typing import List, Dict
from .schemas import ComponentNode, PinConnection

class FMEAEngine:
    """
    Failure Mode and Effects Analysis.
    Runs "what happens if this fails?" tests.
    """
    
    @classmethod
    def analyze_failure_modes(cls, components: List[ComponentNode], connections: List[PinConnection]) -> List[Dict]:
        risks = []
        # Example check
        power_supplies = [c for c in components if "power_supply" in c.category.lower()]
        if len(power_supplies) == 1:
            risks.append({
                "component": power_supplies[0].name,
                "failure_mode": "Single Point of Failure",
                "effect": "Complete system shutdown"
            })
            
        return risks
