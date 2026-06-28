from typing import List
from .schemas import ComponentNode

class ManufacturingValidator:
    """
    Checks lifecycle status, lead times, obsolete parts, and supplier availability.
    """
    
    @classmethod
    def validate_manufacturing_readiness(cls, components: List[ComponentNode]) -> List[str]:
        errors = []
        # In reality, this would check Octopart or DigiKey API
        # For now, it's a placeholder struct
        for c in components:
            if "discontinued" in str(c.part_number).lower():
                errors.append(f"Manufacturing Error: Component {c.name} is discontinued.")
                
        return errors
