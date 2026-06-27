from .extraction import ExtractionEngine
from .alias_registry import AliasRegistry
from .fingerprint import ComponentFingerprint
from .ontology import EngineeringOntology
from .priority_engine import SourcePriorityEngine
from .graph_repair import GraphRepairEngine
from .confidence_engine import ConfidenceEngine

class MappingPipeline:
    """
    Orchestrates the 12-phase pipeline for Component Mapping.
    """
    def __init__(self, raw_evidence: str):
        self.extractor = ExtractionEngine(raw_evidence)
        self.aliases = AliasRegistry()

    def run(self):
        # 1. Extraction
        comps, conns, hier, val = self.extractor.execute_all()

        # 2. Normalization & Fingerprinting
        for c in comps:
            c.canonical_name = self.aliases.get_canonical_name(c.name)
            c.fingerprint_hash = ComponentFingerprint.generate_hash({"name": c.canonical_name})

        # 3. Entity Resolution & Ontology
        # ... logic to merge duplicates ...

        # 4. Connection & Hierarchy Generation
        # ... logic ...

        # 5. Graph Repair
        repairs = GraphRepairEngine.run_repair(comps, conns)

        # 6. Final Graph Build
        return {
            "components": comps,
            "connections": conns,
            "repairs": repairs
        }
