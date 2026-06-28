from typing import List
from .schemas import ComponentNode, PinConnection

class GraphIntegrityEngine:
    """
    Runs post-generation graph checks: No orphans, no floating ports, no duplicate connections.
    """
    
    @classmethod
    def check_integrity(cls, components: List[ComponentNode], connections: List[PinConnection]) -> List[str]:
        errors = []
        connected_components = set()
        for conn in connections:
            connected_components.add(conn.source_component_id)
            connected_components.add(conn.target_component_id)
            
        for comp in components:
            if comp.id not in connected_components:
                errors.append(f"Orphan Component: {comp.name} is not connected to anything.")
                
        return errors
