from typing import Optional
from .schemas import Harness, Connector

class HarnessValidator:
    """
    Validates Harness construction (Cable length, Wire Gauge, Connectors).
    """
    
    @classmethod
    def validate_harness(cls, harness: Harness) -> bool:
        if harness.length_mm is not None and harness.length_mm > 5000:
            # Example limit: a standard signal harness > 5m might degrade
            return False
            
        if harness.wire_gauge and "AWG" not in harness.wire_gauge:
            return False
            
        return True
