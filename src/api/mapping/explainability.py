from typing import List
from .schemas import ComponentNode, ConnectionEdge

class ExplainabilityEngine:
    """
    Phase 12: Explainability.
    Every node and edge must answer: 'Why does this exist?'
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
        if edge.explainability:
            return edge.explainability
            
        reasons = []
        for ev in edge.evidence:
            reasons.append(f"Derived from {ev.source_type.value} ({ev.source_file})")
            
        if not reasons:
            return "Inferred by Reasoning Engine."
            
        return " | ".join(reasons)
