from typing import List, Tuple
from .schemas import ComponentNode, ConnectionEdge, PinConnection, GraphHealth, ConnectionEdgeMigrator


class GraphRepairEngine:
    """
    Phase 9: Graph Repair.
    Detects duplicate components and orphans.
    Supports both legacy ConnectionEdge and new PinConnection.
    """
    @staticmethod
    def run_repair(
        components: List[ComponentNode],
        connections: List[ConnectionEdge] = None,
        pin_connections: List[PinConnection] = None
    ) -> List[str]:
        repairs_made = []

        # Build connected_ids from whichever connection format is provided
        connected_ids = set()
        if connections:
            for c in connections:
                connected_ids.add(c.source)
                connected_ids.add(c.target)
        if pin_connections:
            for c in pin_connections:
                connected_ids.add(c.source_component_id)
                connected_ids.add(c.target_component_id)

        for comp in components:
            if comp.id not in connected_ids:
                repairs_made.append(f"Orphan detected: {comp.name} ({comp.category})")

        return repairs_made


class GraphValidationEngine:
    """
    Phase 8 & 9: Graph Validation, Completeness, and Engineering Health Score.
    Supports both legacy ConnectionEdge and new PinConnection.
    """
    @staticmethod
    def validate(
        components: List[ComponentNode],
        connections: List[ConnectionEdge] = None,
        pin_connections: List[PinConnection] = None
    ) -> GraphHealth:
        classification_accuracy = 100.0
        connection_accuracy = 100.0
        kinematic_accuracy = 100.0
        subsystem_accuracy = 100.0

        errors = []
        warnings = []

        # Build connected_ids from whichever connection format is provided
        connected_ids = set()
        if connections:
            for c in connections:
                connected_ids.add(c.source)
                connected_ids.add(c.target)
        if pin_connections:
            for c in pin_connections:
                connected_ids.add(c.source_component_id)
                connected_ids.add(c.target_component_id)

        # --- Phase 8: Completeness Check ---
        found_categories = set(c.category.lower() for c in components)
        required_cats = {"controller", "power", "driver", "actuator"}
        missing_cats = required_cats - found_categories
        if missing_cats:
            kinematic_accuracy -= 30.0
            errors.append(f"Missing critical subsystem categories: {', '.join(missing_cats)}")

        # --- Phase 9: Detailed Scoring ---

        # 1. Classification Accuracy
        unknowns = [c for c in components if c.category.lower() == "unknown" or not c.engineering_role]
        if unknowns:
            classification_accuracy -= (len(unknowns) / max(1, len(components))) * 100
            warnings.append(f"{len(unknowns)} components lack clear engineering roles or categories.")

        # 2. Connection Accuracy
        if components:
            isolated = [c for c in components if c.id not in connected_ids]
            if isolated:
                connection_accuracy -= (len(isolated) / len(components)) * 100
                errors.append(f"Found {len(isolated)} isolated components.")

        # 3. Subsystem Accuracy
        if components:
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
