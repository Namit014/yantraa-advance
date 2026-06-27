from typing import Tuple
from .ontology import EngineeringOntology

class EngineeringRules:
    """
    Engineering Rule Validator.
    Catches logical graph errors based on ontology and physical constraints.
    """
    @staticmethod
    def validate_connection(source_type: str, target_type: str, connection_type: str) -> Tuple[bool, str]:
        src_parent = EngineeringOntology.get_parent_class(source_type)
        tgt_parent = EngineeringOntology.get_parent_class(target_type)

        if src_parent == "Controller" and tgt_parent == "Mechanical Support":
            return False, f"Controller ({source_type}) must not drive Mechanical Support ({target_type})"
        
        if src_parent == "Sensor" and connection_type == "POWER" and tgt_parent == "Motor":
            return False, f"Sensor ({source_type}) cannot power Motor ({target_type})"
        
        return True, "Valid"
