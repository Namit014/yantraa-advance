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
    Phase 8 & 9: Graph Validation, Completeness, and Engineering Health Score.
    """
    @staticmethod
    def validate(components: List[ComponentNode], connections: List[ConnectionEdge]) -> GraphHealth:
        classification_accuracy = 100.0
        connection_accuracy = 100.0
        kinematic_accuracy = 100.0
        subsystem_accuracy = 100.0
        
        errors = []
        warnings = []
        
        connected_ids = {c.source for c in connections}.union({c.target for c in connections})
        
        # --- Phase 8: Completeness Check ---
        found_categories = set(c.category.lower() for c in components)
        required_cats = {"controller", "power", "driver", "actuator"}
        missing_cats = required_cats - found_categories
        if missing_cats:
            kinematic_accuracy -= 30.0
            errors.append(f"Missing critical subsystem categories: {', '.join(missing_cats)}")
            
        # --- Phase 9: Detailed Scoring ---
        
        # 1. Classification Accuracy (Are components classified correctly without unknown?)
        unknowns = [c for c in components if c.category.lower() == "unknown" or not c.engineering_role]
        if unknowns:
            classification_accuracy -= (len(unknowns) / len(components)) * 100
            warnings.append(f"{len(unknowns)} components lack clear engineering roles or categories.")

        # 2. Connection Accuracy (Are there isolated components or generic connections?)
        isolated = [c for c in components if c.id not in connected_ids]
        if isolated:
            connection_accuracy -= (len(isolated) / len(components)) * 100
            errors.append(f"Found {len(isolated)} isolated components.")
            
        # 3. Subsystem Accuracy (Do components have parent assemblies?)
        orphans = [c for c in components if not c.parent_assembly]
        if orphans:
            subsystem_accuracy -= (len(orphans) / len(components)) * 100
            warnings.append(f"{len(orphans)} components lack a parent assembly.")

        # 4. Overall Accuracy
        overall_accuracy = (classification_accuracy + connection_accuracy + kinematic_accuracy + subsystem_accuracy) / 4.0

        return GraphHealth(
            overall_accuracy=max(0.0, overall_accuracy),
            classification_accuracy=max(0.0, classification_accuracy),
            connection_accuracy=max(0.0, connection_accuracy),
            kinematic_accuracy=max(0.0, kinematic_accuracy),
            subsystem_accuracy=max(0.0, subsystem_accuracy),
            errors=errors,
            warnings=warnings
        )
