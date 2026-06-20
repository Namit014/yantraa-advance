class ComponentNormalizer:
    def __init__(self):
        # Maps common input terms to registry keys or normalized types
        self.alias_map = {
            "mg996r": "servo_a",
            "servo": "servo_a",
            "servo motor": "servo_a",
            "high torque servo": "servo_a",
            "battery": "battery_24v",
            "power supply": "battery_24v",
            "lipo": "battery_24v",
            "raspberry pi": "motion_controller",
            "arduino": "motion_controller",
            "controller": "motion_controller",
            "motion controller": "motion_controller",
            "encoder": "encoder_a",
            "rotary encoder": "encoder_a",
            "imu": "imu_sensor",
            "gyro": "imu_sensor",
            "accelerometer": "imu_sensor",
            "motor driver": "motor_driver",
            "h-bridge": "motor_driver",
            "l298n": "motor_driver",
            "wheel motor": "wheel_motor",
            "dc motor": "wheel_motor",
            "motor": "wheel_motor"
        }

    def normalize(self, user_string: str) -> str:
        """
        Takes a user-provided component name and attempts to normalize it
        to a standard component ID present in the ComponentRegistry.
        """
        normalized_str = user_string.lower().strip()
        return self.alias_map.get(normalized_str, "unknown")
