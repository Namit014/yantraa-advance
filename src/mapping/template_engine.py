class TemplateEngine:
    def __init__(self):
        from .templates.agv_template import AGVTemplate
        from .templates.robot_arm_template import RobotArmTemplate
        self.templates = [AGVTemplate(), RobotArmTemplate()]

    def detect_architecture(self, component_ids: list[str], registry) -> str:
        """
        Analyzes the components and returns the name of the best matching architecture template.
        """
        scores = {}
        for template in self.templates:
            score = template.score_match(component_ids, registry)
            scores[template.name] = score

        best_match = max(scores.items(), key=lambda x: x[1])
        if best_match[1] > 0:
            return best_match[0]
        return "Generic"

    def apply_template(self, architecture_name: str, component_ids: list[str], registry):
        for template in self.templates:
            if template.name == architecture_name:
                return template.apply(component_ids, registry)
        return component_ids  # Return as is if no specific template
