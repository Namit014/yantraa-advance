from typing import List, Optional
from .schemas import ComponentNode, PinConnection, ConnectionAudit
from .compatibility_matrix import CompatibilityMatrixEngine

class PinMappingEngine:
    """
    Extends mapping from Component -> Port to Component -> Port -> Pin.
    Validates connections strictly at the Pin -> Pin level.
    """
    
    @classmethod
    def attempt_pin_connection(cls, source_comp: ComponentNode, source_port_id: str, source_pin_id: str,
                               target_comp: ComponentNode, target_port_id: str, target_pin_id: str) -> Optional[PinConnection]:
        
        # Locate pins
        source_pin = None
        for port in source_comp.ports:
            if port.port_id == source_port_id:
                for pin in port.pins:
                    if pin.pin_id == source_pin_id:
                        source_pin = pin
                        
        target_pin = None
        for port in target_comp.ports:
            if port.port_id == target_port_id:
                for pin in port.pins:
                    if pin.pin_id == target_pin_id:
                        target_pin = pin
                        
        if not source_pin or not target_pin:
            return None
            
        # Run Electrical and Protocol compatibility
        if not CompatibilityMatrixEngine.check_electrical_compatibility(source_pin, target_pin):
            return None
            
        if not CompatibilityMatrixEngine.check_protocol_compatibility(source_pin.protocol, target_pin.protocol):
            return None
            
        audit = ConnectionAudit(
            created_by="PinMappingEngine",
            evidence=["Electrical checks passed", "Protocol checks passed"],
            compatibility_score=0.99
        )
        
        return PinConnection(
            id=f"{source_comp.id}_{source_pin_id}_{target_comp.id}_{target_pin_id}",
            source_component_id=source_comp.id,
            source_port_id=source_port_id,
            source_pin_id=source_pin_id,
            target_component_id=target_comp.id,
            target_port_id=target_port_id,
            target_pin_id=target_pin_id,
            audit=audit
        )
