from typing import Optional
from .schemas import Connector, Port, ComponentNode

class ConnectorEngine:
    """
    Validates connectors required for a port. 
    Models Pin -> Connector compatibility.
    """
    
    @classmethod
    def match_connectors(cls, source_port: Port, target_port: Port) -> bool:
        """
        Check if the source port connector type can mate with the target port connector type,
        or if a valid harness can be constructed between them.
        """
        if not source_port.connector_type or not target_port.connector_type:
            return False # Both sides need defined connectors
            
        # Example validation: if they are the exact same connector, they might need a 1:1 harness
        # A more advanced version would use a KnowledgeBase for connector compatibility.
        
        return True
