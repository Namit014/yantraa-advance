from typing import List, Dict, Set
from .schemas import ComponentNode
import uuid

class DependencyResolver:
    """
    Infers necessary but omitted components with explicit engineering rules.
    """
    
    # Golden Engineering Dependencies
    DEPENDENCY_RULES = {
        "servo_motor": ["motor_driver", "power_supply", "feedback_interface"],
        "stepper_motor": ["stepper_driver", "power_supply"],
        "24v_system": ["fuse", "grounding", "protection"],
        "industrial_robot": ["emergency_stop", "safety_relay", "power_distribution"],
        "vision_system": ["camera_interface", "processing_unit", "power_regulation"]
    }
    
    @classmethod
    def resolve_dependencies(cls, existing_components: List[ComponentNode]) -> List[ComponentNode]:
        """
        Detects missing dependencies and returns a list of proposed components to add.
        """
        existing_categories = {c.category.lower().replace(" ", "_") for c in existing_components if c.category}
        
        required_categories = set()
        
        for category in existing_categories:
            for rule_category, requirements in cls.DEPENDENCY_RULES.items():
                if rule_category in category or category in rule_category:
                    for req in requirements:
                        required_categories.add(req)
                        
        missing_categories = required_categories - existing_categories
        
        proposed_components = []
        for missing in missing_categories:
            human_name = missing.replace("_", " ").title()
            comp = ComponentNode(
                id=str(uuid.uuid4()),
                name=f"Inferred {human_name}",
                category=missing,
                explainability=f"Automatically inferred dependency based on system requirement: {missing}",
                confidence=1.0,
                datasheet_verified=False
            )
            proposed_components.append(comp)
            
        return proposed_components
