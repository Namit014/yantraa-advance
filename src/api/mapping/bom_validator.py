from typing import List, Dict
from .schemas import ComponentNode

class BOMValidator:
    """
    Validates BOM physical coherence.
    Example: 4-axis robot cannot have 5 motors.
    """
    
    @classmethod
    def validate_bom(cls, components: List[ComponentNode], robot_type: str = "generic") -> List[str]:
        errors = []
        motor_count = sum(1 for c in components if "motor" in c.category.lower())
        driver_count = sum(1 for c in components if "driver" in c.category.lower())
        
        if driver_count > 0 and motor_count != driver_count:
            errors.append(f"Quantity Mismatch: {motor_count} motors but {driver_count} drivers.")
            
        return errors
