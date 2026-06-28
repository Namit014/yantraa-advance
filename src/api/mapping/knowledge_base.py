from typing import List, Dict

class KnowledgeBaseEngine:
    """
    Scalable structured knowledge base outlining explicit dependencies.
    """
    
    # Placeholder for KB
    KB_RULES = {
        "servo_motor": {
            "requires": ["motor_driver"]
        },
        "stepper_motor": {
            "requires": ["stepper_driver"]
        },
        "24v_system": {
            "requires": ["fuse", "emergency_stop"]
        }
    }
    
    @classmethod
    def get_requirements_for(cls, component_category: str) -> List[str]:
        return cls.KB_RULES.get(component_category.lower(), {}).get("requires", [])
