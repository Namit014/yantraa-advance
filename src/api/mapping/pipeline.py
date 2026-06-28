import uuid
from typing import Dict, Any

from .extraction import ExtractionEngine
from .datasheet_engine import DatasheetEngine
from .dependency_resolver import DependencyResolver
from .knowledge_base import KnowledgeBaseEngine
from .bom_validator import BOMValidator
from .manufacturing_validator import ManufacturingValidator
from .requirements_engine import RequirementsEngine
from .pin_mapping import PinMappingEngine
from .connector_engine import ConnectorEngine
from .adapter_engine import AdapterEngine
from .topology_validator import TopologyValidator
from .safety_architecture import SafetyArchitectureValidator
from .fmea_engine import FMEAEngine
from .graph_integrity import GraphIntegrityEngine
from .simulation_confidence import SimulationConfidenceEngine
from .approval_workflow import ApprovalWorkflowEngine, GraphState
from .schemas import ComponentNode, PinConnection, GraphHealth

class MappingPipeline:
    """
    Orchestrates the Hybrid Architecture flow for Component Mapping.
    LLMs extract -> Deterministic Engines Validate.
    """
    def __init__(self, raw_evidence: str, requirements: Dict[str, str] = None):
        self.extractor = ExtractionEngine(raw_evidence)
        self.requirements = requirements or {}

    def run(self) -> Dict[str, Any]:
        # STAGE 1: LLM Extraction
        extracted_data = self.extractor.execute_all()
        
        comps = []
        conns = []
        
        # Load rough components
        raw_comps = extracted_data.get("physical_components", [])
        for rc in raw_comps:
            comps.append(ComponentNode(
                id=rc.get("id", str(uuid.uuid4())),
                name=rc.get("name", "Unknown"),
                category=rc.get("category", "electronic")
            ))

        # STAGE 2: Dependency Resolution & KB
        missing_comps = DependencyResolver.resolve_dependencies(comps)
        for missing in missing_comps:
            comps.append(ComponentNode(
                id=str(uuid.uuid4()),
                name=f"Inferred {missing}",
                category=missing
            ))
            
        # STAGE 3: Datasheet Grounding
        for c in comps:
            DatasheetEngine.verify_component(c)
            
        # STAGE 4: BOM & Manufacturing Validation
        bom_errors = BOMValidator.validate_bom(comps)
        mfg_errors = ManufacturingValidator.validate_manufacturing_readiness(comps)
        
        if bom_errors or mfg_errors:
            return {"status": "failed", "errors": bom_errors + mfg_errors}
            
        # STAGE 5: Traceability
        RequirementsEngine.trace_requirements(comps, self.requirements)
        
        # STAGE 6: Pin-Level Connection Generation
        # (Placeholder for auto-wiring engine logic using PinMappingEngine)
        
        # STAGE 7: Safety & FMEA
        safety_errors = SafetyArchitectureValidator.validate_safety(comps, conns)
        fmea_risks = FMEAEngine.analyze_failure_modes(comps, conns)
        
        if safety_errors:
            return {"status": "failed", "errors": safety_errors}
            
        # STAGE 8: Graph Integrity
        integrity_errors = GraphIntegrityEngine.check_integrity(comps, conns)
        if integrity_errors:
            return {"status": "failed", "errors": integrity_errors}
            
        # STAGE 9: Confidence Scoring
        confidence = SimulationConfidenceEngine.calculate_confidence(comps, conns)
        
        # STAGE 10: Approval Workflow
        state = ApprovalWorkflowEngine.approve_graph(["Electrical", "Mechanical", "Controls", "Safety", "Manufacturing"])
        
        health = GraphHealth(
            overall_accuracy=confidence * 100,
            errors=integrity_errors + safety_errors + bom_errors + mfg_errors,
            warnings=[str(r) for r in fmea_risks]
        )

        return {
            "status": "success",
            "state": state.value,
            "graph_health_score": health.overall_accuracy,
            "components": [c.model_dump() for c in comps],
            "connections": [c.model_dump() for c in conns],
            "validation": [{"type": "error", "message": e} for e in health.errors]
        }
