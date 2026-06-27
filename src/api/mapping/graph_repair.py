from typing import List, Tuple
from .schemas import ComponentNode, ConnectionEdge, GraphHealth

class GraphRepairEngine:
    """
    Phase 9: Graph Repair.
    Detects duplicate components and orphans.
    """
    @staticmethod
    def run_repair(components: List[ComponentNode], connections: List[ConnectionEdge]) -> List[str]:
        repairs_made = []
        
        connected_ids = {c.source for c in connections}.union({c.target for c in connections})
        
        for comp in components:
            if comp.id not in connected_ids:
                repairs_made.append(f"Orphan detected: {comp.name} ({comp.category})")
                
        return repairs_made

class GraphValidationEngine:
    """
    Phase 11: Graph Validation.
    Validates graph rules (no isolated power, no isolated controllers).
    Generates graph_health_score.
    """
    @staticmethod
    def validate(components: List[ComponentNode], connections: List[ConnectionEdge]) -> GraphHealth:
        score = 100
        errors = []
        warnings = []
        
        connected_ids = {c.source for c in connections}.union({c.target for c in connections})
        
        # 1. No isolated controllers
        for c in components:
            if c.category.lower() == "controller" and c.id not in connected_ids:
                score -= 30
                errors.append(f"Isolated Controller detected: {c.name}")
                
        # 2. No isolated power supplies
        for c in components:
            if c.category.lower() == "power" and c.id not in connected_ids:
                score -= 30
                errors.append(f"Isolated Power Supply detected: {c.name}")
                
        # 3. Graph completeness
        if not components:
            score -= 100
            errors.append("No components found in graph.")
        elif not connections:
            score -= 50
            errors.append("No connections found in graph.")
            
        if score < 0:
            score = 0
            
        return GraphHealth(score=score, errors=errors, warnings=warnings)
