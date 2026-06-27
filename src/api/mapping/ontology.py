class EngineeringOntology:
    """
    Defines engineering relationships to enable reasoning (e.g. Motor -> Actuator).
    """
    HIERARCHY = {
        "Motor": "Actuator",
        "Stepper": "Motor",
        "Servo": "Motor",
        "Encoder": "Sensor",
        "Lidar": "Sensor",
        "Driver": "Controller",
        "Bearing": "Mechanical Support",
        "Gearbox": "Power Transmission",
        "Battery": "Power Supply"
    }

    @staticmethod
    def get_parent_class(component_type: str) -> str:
        return EngineeringOntology.HIERARCHY.get(component_type, "Unknown")
