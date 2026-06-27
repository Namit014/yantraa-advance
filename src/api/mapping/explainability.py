from typing import List
from .schemas import ExplainabilityRecord

class ExplainabilityEngine:
    """
    Every edge answers 'why' a connection exists, which is extremely useful for debugging Yantraa.
    """
    
    @staticmethod
    def generate_explanation(source_name: str, target_name: str, relationship: str, reasons: List[str]) -> ExplainabilityRecord:
        return ExplainabilityRecord(
            source=source_name,
            target=target_name,
            relationship=relationship,
            why=reasons
        )
