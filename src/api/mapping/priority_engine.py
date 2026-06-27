from .schemas import SourceType, Conflict
from typing import Tuple, Optional

class SourcePriorityEngine:
    """
    Phase 0 & 10: Source Priority Policy Engine.
    Resolves conflicts based on configurable policies.
    CAD = 1.0, BOM = 0.95, SCHEMATIC = 0.95, MANUAL = 0.90, DATASHEET = 0.85, KNOWLEDGE_BASE = 0.80, WEB = 0.60
    """
    
    PRIORITY_WEIGHTS = {
        SourceType.CAD: 1.0,
        SourceType.BOM: 0.95,
        SourceType.SCHEMATIC: 0.95,
        SourceType.MANUAL: 0.90,
        SourceType.DATASHEET: 0.85,
        SourceType.KNOWLEDGE_BASE: 0.80,
        SourceType.WEB: 0.60,
        SourceType.IMAGE: 0.50
    }
    
    @classmethod
    def get_priority(cls, source_type: SourceType) -> float:
        return cls.PRIORITY_WEIGHTS.get(source_type, 0.5)

    @classmethod
    def resolve_conflict(cls, source1: SourceType, val1: str, source2: SourceType, val2: str) -> Tuple[Optional[str], Conflict]:
        w1 = cls.get_priority(source1)
        w2 = cls.get_priority(source2)

        winner = None
        if w1 > w2:
            winner = val1
        elif w2 > w1:
            winner = val2
        else:
            winner = None # Tie

        conflict_record = Conflict(
            issue_type="Data Mismatch",
            description=f"Conflict between {source1.value} ({val1}) and {source2.value} ({val2})",
            involved_nodes=[val1, val2]
        )
        return winner, conflict_record
