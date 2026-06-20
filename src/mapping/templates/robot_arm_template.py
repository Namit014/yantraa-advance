class RobotArmTemplate:
    @property
    def name(self):
        return "Robot Arm"

    def score_match(self, component_ids: list[str], registry) -> int:
        score = 0
        categories = [registry.get_component(c).get("subcategory") for c in component_ids if registry.get_component(c)]
        if "servo" in categories:
            score += 50
        if "encoder" in categories:
            score += 20
        return score

    def apply(self, component_ids: list[str], registry) -> list[str]:
        return component_ids
