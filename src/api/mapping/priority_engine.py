from .schemas import Conflict, SourceType

class SourcePriorityEngine:
    """
    Source Priority Policy Engine.
    Resolves conflicts based on configurable policies (e.g. CAD > BOM).
    """
    
    @staticmethod
    def resolve_conflict(source1: SourceType, val1: str, source2: SourceType, val2: str):
        # Using ConfidenceEngine weights to determine priority
        from .confidence_engine import ConfidenceEngine
        w1 = ConfidenceEngine.SOURCE_WEIGHTS.get(source1, 0.0)
        w2 = ConfidenceEngine.SOURCE_WEIGHTS.get(source2, 0.0)

        if w1 > w2:
            winner = val1
        elif w2 > w1:
            winner = val2
        else:
            winner = None # Tie

        conflict_record = Conflict(
            issue_type="Data Mismatch",
            description=f"Conflict between {source1} ({val1}) and {source2} ({val2})",
            involved_nodes=[val1, val2]
        )
        return winner, conflict_record
