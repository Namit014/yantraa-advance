class AGVTemplate:
    @property
    def name(self):
        return "AGV"

    def score_match(self, component_ids: list[str], registry) -> int:
        score = 0
        categories = [registry.get_component(c).get("subcategory") for c in component_ids if registry.get_component(c)]
        if "dc_motor" in categories or "wheel_motor" in categories:
            score += 50
        if "motor_driver" in categories:
            score += 30
        return score

    def apply(self, component_ids: list[str], registry) -> list[str]:
        # Pre-process components if needed, or define specific structured sub-graphs.
        # For now, just return the list. The rule engine will map it.
        return component_ids
