from .component_registry import ComponentRegistry

class DependencyEngine:
    def __init__(self, registry: ComponentRegistry):
        self.registry = registry

    def expand_dependencies(self, component_ids: list[str]) -> list[str]:
        """
        Takes a list of normalized component IDs and ensures all their
        required dependencies are included in the list.
        """
        expanded = set(component_ids)
        queue = list(component_ids)

        while queue:
            current_id = queue.pop(0)
            comp_data = self.registry.get_component(current_id)
            if not comp_data:
                continue

            requires = comp_data.get("requires", [])
            for req in requires:
                # Find if we already have a component of this category
                has_req = any(
                    self.registry.get_component(eid) and self.registry.get_component(eid).get("category") == req
                    for eid in expanded
                )
                
                if not has_req:
                    # Resolve to a default component ID for that category
                    default_mapping = {
                        "controller": "motion_controller",
                        "power_supply": "battery_24v",
                        "motor_driver": "motor_driver"
                    }
                    if req in default_mapping:
                        new_id = default_mapping[req]
                        if new_id not in expanded:
                            expanded.add(new_id)
                            queue.append(new_id)

        return list(expanded)
