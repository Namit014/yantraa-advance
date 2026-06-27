from typing import List
from .schemas import EvidenceReference, SourceType

class ProvenanceManager:
    """
    Manages Evidence provenance. Right now nodes and edges store evidence, 
    but this provides a dedicated provenance system for tracking and querying.
    """
    def __init__(self):
        self.evidence_log = []

    def record_evidence(self, source_type: SourceType, file: str, confidence: float, **kwargs) -> EvidenceReference:
        ref = EvidenceReference(
            source_type=source_type,
            source_file=file,
            confidence=confidence,
            page_number=kwargs.get("page_number"),
            paragraph=kwargs.get("paragraph"),
            image_region=kwargs.get("image_region"),
            cad_assembly_path=kwargs.get("cad_assembly_path")
        )
        self.evidence_log.append(ref)
        return ref
