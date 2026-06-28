import uuid
from typing import Dict, Any, List

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
from .ontology import EngineeringOntology
from .graph_repair import GraphRepairEngine, GraphValidationEngine
from .explainability import ExplainabilityEngine
from .schemas import (
    ComponentNode, PinConnection, ConnectionEdge, ConnectionType,
    GraphHealth, ConnectionAudit, ConnectionEdgeMigrator
)


class MappingPipeline:
    """
    Orchestrates the Hybrid Architecture flow for Component Mapping.
    LLMs extract → Ontology + Reasoning infer chains → Deterministic Engines Validate.
    Backward Compatible: accepts legacy ConnectionEdge (auto-upgraded) and new PinConnection.
    """

    def __init__(self, raw_evidence: str, requirements: Dict[str, str] = None):
        self.extractor = ExtractionEngine(raw_evidence)
        self.requirements = requirements or {}

    def run(self) -> Dict[str, Any]:
        # ─── STAGE 1: LLM Extraction ──────────────────────────────────────────
        extracted_data = self.extractor.execute_all()

        comps: List[ComponentNode] = []
        legacy_conns: List[ConnectionEdge] = []
        pin_conns: List[PinConnection] = []

        # Load extracted components
        raw_comps = extracted_data.get("components", extracted_data.get("physical_components", []))
        for rc in raw_comps:
            comps.append(ComponentNode(
                id=rc.get("id", str(uuid.uuid4())),
                name=rc.get("name", "Unknown"),
                canonical_name=rc.get("engineering_name", rc.get("name", "Unknown")),
                engineering_role=rc.get("engineering_role"),
                category=rc.get("category", "Unknown"),
                parent_assembly=rc.get("parent_assembly"),
                explainability=rc.get("evidence", "")
            ))

        # Load extracted connections as legacy edges (backward compatible)
        raw_conns = extracted_data.get("connections", [])
        for rc in raw_conns:
            raw_type = rc.get("type", "SIGNAL").upper()
            # Safely resolve ConnectionType; fall back to SIGNAL alias which maps to UNKNOWN_SIGNAL_PROTOCOL
            try:
                conn_type = ConnectionType(rc.get("type", "controls"))
            except ValueError:
                # e.g. LLM returned "SIGNAL" or any unknown string
                conn_type = ConnectionType.SIGNAL

            legacy_conns.append(ConnectionEdge(
                id=rc.get("id", str(uuid.uuid4())),
                source=rc.get("source", ""),
                target=rc.get("target", ""),
                type=conn_type,
                confidence=rc.get("confidence", 0.8),
                explainability=rc.get("evidence", "Extracted by LLM")
            ))

        # ─── STAGE 2: Ontology Chain Inference ────────────────────────────────
        inferred_conns = EngineeringOntology.infer_chains(comps, legacy_conns)
        legacy_conns.extend(inferred_conns)

        # ─── STAGE 3: Dependency Resolution & KB ──────────────────────────────
        missing_comps = DependencyResolver.resolve_dependencies(comps)
        comps.extend(missing_comps)

        # ─── STAGE 4: Datasheet Grounding ─────────────────────────────────────
        for c in comps:
            DatasheetEngine.verify_component(c)

        # ─── STAGE 5: BOM & Manufacturing Validation ──────────────────────────
        bom_errors = BOMValidator.validate_bom(comps)
        mfg_errors = ManufacturingValidator.validate_manufacturing_readiness(comps)

        # ─── STAGE 6: Traceability ────────────────────────────────────────────
        RequirementsEngine.trace_requirements(comps, self.requirements)

        # ─── STAGE 7: Safety & FMEA ───────────────────────────────────────────
        safety_errors = SafetyArchitectureValidator.validate_safety(comps, pin_conns)
        fmea_risks = FMEAEngine.analyze_failure_modes(comps, pin_conns)

        # ─── STAGE 8: Graph Integrity (uses both legacy + new connections) ─────
        integrity_report = GraphValidationEngine.validate(comps, legacy_conns, pin_conns)
        repair_report = GraphRepairEngine.run_repair(comps, legacy_conns, pin_conns)

        all_errors = integrity_report.errors + safety_errors + bom_errors + mfg_errors
        all_warnings = integrity_report.warnings + repair_report + [str(r) for r in fmea_risks]

        # ─── STAGE 9: Confidence Scoring ──────────────────────────────────────
        confidence = SimulationConfidenceEngine.calculate_confidence(comps, pin_conns)

        # ─── STAGE 10: Approval Workflow ───────────────────────────────────────
        state = ApprovalWorkflowEngine.approve_graph(
            ["Electrical", "Mechanical", "Controls", "Safety", "Manufacturing"]
        )

        # ─── STAGE 11: Build BOM & Serialize ──────────────────────────────────
        bom = [
            {
                "id": c.id,
                "name": c.canonical_name or c.name,
                "category": c.category,
                "parent_assembly": c.parent_assembly,
                "explainability": ExplainabilityEngine.generate_node_explanation(c),
                "datasheet_verified": c.datasheet_verified,
                "confidence": c.confidence
            }
            for c in comps
        ]

        # Serialize connections — prefer new PinConnections; fallback to legacy edges
        serialized_connections = []
        for conn in legacy_conns:
            domain = ConnectionEdgeMigrator.get_protocol_domain(conn)
            serialized_connections.append({
                "id": conn.id,
                "source": conn.source,
                "target": conn.target,
                "type": conn.type.value,
                "protocol_domain": domain,
                "confidence": conn.confidence,
                "explainability": ExplainabilityEngine.generate_edge_explanation(conn),
                "is_legacy": True
            })
        for conn in pin_conns:
            serialized_connections.append({
                "id": conn.id,
                "source": conn.source_component_id,
                "target": conn.target_component_id,
                "source_pin": conn.source_pin_id,
                "target_pin": conn.target_pin_id,
                "type": "PIN_CONNECTION",
                "explainability": ExplainabilityEngine.generate_pin_connection_explanation(conn),
                "is_legacy": False
            })

        return {
            "status": "success",
            "state": state.value,
            "graph_health_score": integrity_report.overall_accuracy,
            "bom": bom,
            "components": [c.model_dump() for c in comps],
            "connections": serialized_connections,
            "validation": [{"type": "error", "message": e} for e in all_errors],
            "warnings": [{"type": "warning", "message": w} for w in all_warnings],
            "fmea_risks": [str(r) for r in fmea_risks],
            "kinematic_chain": extracted_data.get("kinematic_chain", []),
            "report_markdown": self._build_report(comps, serialized_connections, all_errors, all_warnings, integrity_report)
        }

    def _build_report(
        self,
        comps: List[ComponentNode],
        connections: list,
        errors: List[str],
        warnings: List[str],
        health: GraphHealth
    ) -> str:
        lines = [
            "## 🤖 Yantraa Robot Design",
            "",
            f"### 📦 Components ({len(comps)})",
        ]
        for c in comps:
            ds = "✅ Datasheet" if c.datasheet_verified else "⚠️ Inferred"
            lines.append(f"- **{c.canonical_name or c.name}** `{c.category}` [{ds}]")

        lines += ["", f"### 🔗 Connections ({len(connections)})"]
        for conn in connections[:10]:  # Cap for readability
            lines.append(f"- `{conn['source']}` → `{conn['target']}` ({conn['type']})")

        lines += ["", "### 🔍 Validation Checks:"]
        if errors:
            for e in errors:
                lines.append(f"❌ *ERROR:* {e}")
        else:
            lines.append("✅ All validation checks passed.")

        if warnings:
            for w in warnings:
                lines.append(f"⚠️ *WARNING:* {w}")

        lines += [
            "",
            f"### 📊 Health Score: `{health.overall_accuracy:.1f}%`"
        ]
        return "\n".join(lines)
