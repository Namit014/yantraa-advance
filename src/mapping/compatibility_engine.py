class CompatibilityEngine:
    def __init__(self):
        self.matrix = {
            "servo": ["motion_controller", "power_supply"],
            "encoder": ["motion_controller", "power_supply"],
            "imu": ["motion_controller", "power_supply"],
            "dc_motor": ["motor_driver"],
            "motor_driver": ["motion_controller", "power_supply"]
        }

    def can_connect(self, source_subcategory: str, target_subcategory: str) -> bool:
        """
        Returns true if the source subcategory is allowed to connect to the target subcategory.
        Note: The graph is directed, so this might be uni-directional checks.
        Typically, targets connect to sources (e.g., servo connects to motion_controller).
        """
        # Bidirectional check for compatibility in matrix
        if source_subcategory in self.matrix and target_subcategory in self.matrix[source_subcategory]:
            return True
        if target_subcategory in self.matrix and source_subcategory in self.matrix[target_subcategory]:
            return True
        return False
