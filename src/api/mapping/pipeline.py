from .extraction import ExtractionEngine
from .alias_registry import AliasRegistry
from .fingerprint import ComponentFingerprint, EntityResolutionEngine
from .ontology import EngineeringOntology
from .graph_repair import GraphRepairEngine, GraphValidationEngine
from .explainability import ExplainabilityEngine
from .schemas import ComponentNode, ConnectionEdge, EvidenceReference, SourceType, ConnectionType
import uuid

class MappingPipeline:
    """
    Orchestrates the 14-phase pipeline for Component Mapping.
    """
    def __init__(self, raw_evidence: str):
        self.extractor = ExtractionEngine(raw_evidence)
        self.aliases = AliasRegistry()

    def run(self):
        # Phase 1: Extraction
        extracted_data = self.extractor.execute_all()
        
        comps = []
        conns = []

        # Convert extraction output to Schema Models
        raw_comps = extracted_data.get("physical_components", [])
        for rc in raw_comps:
            comps.append(ComponentNode(
                id=rc.get("id", str(uuid.uuid4())),
                name=rc.get("name", "Unknown"),
                category=rc.get("category", "electronic"),
                confidence=0.95,
                evidence=[EvidenceReference(
                    source_id="llm",
                    source_type=SourceType.MANUAL,
                    source_file="User Query"
                )]
            ))

        raw_conns = extracted_data.get("connections", []) + extracted_data.get("power_paths", []) + extracted_data.get("motion_paths", [])
        for rc in raw_conns:
            conns.append(ConnectionEdge(
                id=str(uuid.uuid4()),
                source=rc.get("source"),
                target=rc.get("target"),
                type=getattr(ConnectionType, rc.get("type", "SIGNAL").upper(), ConnectionType.SIGNAL),
                confidence=0.95,
                evidence=[]
            ))

        # Phase 2 & 3: Normalization & Fingerprinting
        for c in comps:
            c.canonical_name = self.aliases.get_canonical_name(c.name)
            c.fingerprint_hash = ComponentFingerprint.generate_hash({"name": c.canonical_name})

        # Phase 4: Entity Resolution
        comps = EntityResolutionEngine.resolve_entities(comps)

        # Phase 5 & 8: Ontology and Reasoning
        inferred_conns = EngineeringOntology.infer_chains(comps, conns)
        conns.extend(inferred_conns)

        # Phase 9: Graph Repair
        repairs = GraphRepairEngine.run_repair(comps, conns)

        # Phase 11: Graph Validation
        health = GraphValidationEngine.validate(comps, conns)

        # Phase 12: Explainability
        for c in comps:
            c.explainability = ExplainabilityEngine.generate_node_explanation(c)
        for e in conns:
            e.explainability = ExplainabilityEngine.generate_edge_explanation(e)

        # Phase 13 & 14: Final UI Contract
        
        if health.score == 0 and not comps:
            # Phase 14: Empty Graph Protection
            return {
                "status": "failed",
                "stage": "connection_generation",
                "error": "LLM rate limited or failed to extract components.",
                "graph_health_score": 0,
                "subsystems": [],
                "connections": []
            }

        # Convert to UI format
        ui_subsystems = [{"name": "Core System", "components": [c.model_dump() for c in comps]}]
        ui_connections = []
        for c in conns:
            ui_connections.append({
                "from": c.source,
                "to": c.target,
                "type": c.type.value,
                "confidence": c.confidence,
                "explainability": c.explainability
            })

        return {
            "status": "success" if health.score > 80 else "partial_success",
            "stage": "complete",
            "error": " | ".join(health.errors) if health.errors else None,
            "graph_health_score": health.score,
            "subsystems": ui_subsystems,
            "connections": ui_connections,
            "bom": [{"id": c.id, "name": c.name, "qty": 1} for c in comps],
            "validation": [{"type": "error", "message": e} for e in health.errors]
        }
