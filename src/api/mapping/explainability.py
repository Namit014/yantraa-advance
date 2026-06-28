from typing import List
from .schemas import (
    ComponentNode, ConnectionEdge, ConnectionType,
    PinConnection, ConnectionEdgeMigrator
)


class ExplainabilityEngine:
    """
    Phase 12: Explainability.
    Every node and edge must answer: 'Why does this exist?'
    Supports both legacy ConnectionEdge and new PinConnection.
    """

    @staticmethod
    def generate_node_explanation(node: ComponentNode) -> str:
        if node.explainability:
            return node.explainability

        reasons = []
        for ev in node.evidence:
            reasons.append(f"Extracted from {ev.source_type.value} ({ev.source_file})")

        if not reasons:
            return "No direct evidence provided. (Inferred or Generated)"

        return " | ".join(reasons)

    @staticmethod
    def generate_edge_explanation(edge: ConnectionEdge) -> str:
        """Legacy method — accepts ConnectionEdge (deprecated). Still works."""
        if edge.explainability:
            return edge.explainability

        domain = ConnectionEdgeMigrator.get_protocol_domain(edge)
        reasons = [f"Protocol domain: {domain}"]
        for ev in edge.evidence:
            reasons.append(f"Derived from {ev.source_type.value} ({ev.source_file})")

        if not reasons:
            return "Inferred by Reasoning Engine."

        return " | ".join(reasons)

    @staticmethod
    def generate_pin_connection_explanation(conn: PinConnection) -> str:
        """New method — accepts PinConnection (preferred)."""
        if conn.audit and conn.audit.evidence:
            return " | ".join(conn.audit.evidence)
        return (
            f"Pin-level connection: {conn.source_component_id}:{conn.source_pin_id} "
            f"→ {conn.target_component_id}:{conn.target_pin_id}. "
            f"Validated by: {', '.join(conn.audit.validation_agents) if conn.audit else 'None'}."
        )
