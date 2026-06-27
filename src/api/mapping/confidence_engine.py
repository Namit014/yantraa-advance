from .schemas import SourceType
from typing import List

class ConfidenceEngine:
    """
    Relationship Confidence Engine.
    Calculates component, connection, hierarchy, and subsystem confidences.
    """
    SOURCE_WEIGHTS = {
        SourceType.CAD: 1.0,
        SourceType.BOM: 0.95,
        SourceType.MANUAL: 0.85,
        SourceType.DATASHEET: 0.8,
        SourceType.WEB: 0.6
    }

    @staticmethod
    def calculate_connection_confidence(sources: List[SourceType]) -> float:
        if not sources:
            return 0.0
        # Simple max weight for now, can be expanded to multi-source consensus
        return max(ConfidenceEngine.SOURCE_WEIGHTS.get(s, 0.5) for s in sources)
