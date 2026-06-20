import json
import os

class ComponentRegistry:
    def __init__(self):
        self.registry = {}
        self.load_registry()

    def load_registry(self):
        registry_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            "../../knowledgebase/component_registry.json"
        ))
        if os.path.exists(registry_path):
            with open(registry_path, "r") as f:
                self.registry = json.load(f)
        else:
            print(f"[ComponentRegistry] Warning: Registry file not found at {registry_path}")

    def get_component(self, component_id):
        return self.registry.get(component_id)

    def get_components_by_category(self, category):
        return [c for c in self.registry.values() if c.get("category") == category]
