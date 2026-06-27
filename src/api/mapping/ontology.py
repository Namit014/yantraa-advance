from typing import List
from .schemas import ComponentNode, ConnectionEdge, ConnectionType

class EngineeringOntology:
    """
    Phase 5 & 8: Engineering Ontology and Reasoning Engine.
    Maps components to ontological classes and infers missing engineering chains.
    """
    CLASSES = {
        "Actuator": ["motor", "stepper", "servo", "pneumatic cylinder", "hydraulic ram"],
        "Sensor": ["encoder", "lidar", "camera", "imu", "limit switch"],
        "Controller": ["plc", "microcontroller", "arduino", "raspberry pi", "cnc controller"],
        "Driver": ["motor driver", "servo drive", "esc", "relay module"],
        "Power": ["power supply", "battery", "buck converter", "psu"],
        "Mechanical": ["bearing", "rail", "screw", "shaft", "joint", "link"],
        "Structural": ["frame", "base", "extrusion"],
        "Transmission": ["gearbox", "belt", "pulley"],
        "Safety": ["e-stop", "safety relay", "contactor"],
        "End Effector": ["gripper", "welding torch", "spindle"]
    }

    @classmethod
    def get_ontology_class(cls, component_name: str) -> str:
        name_lower = component_name.lower()
        for ontology_class, keywords in cls.CLASSES.items():
            if any(kw in name_lower for kw in keywords):
                return ontology_class
        return "Unknown"

    @classmethod
    def infer_chains(cls, components: List[ComponentNode], connections: List[ConnectionEdge]) -> List[ConnectionEdge]:
        """
        Phase 8: Robotics Reasoning.
        Infers logical chains. Example: Controller -> Driver -> Motor -> Gearbox.
        """
        new_connections = []
        by_class = {}
        for c in components:
            ont_class = cls.get_ontology_class(c.canonical_name or c.name)
            by_class.setdefault(ont_class, []).append(c)

        ctrls = by_class.get("Controller", [])
        drivers = by_class.get("Driver", [])
        acts = by_class.get("Actuator", [])
        powers = by_class.get("Power", [])
        sensors = by_class.get("Sensor", [])
        transmissions = by_class.get("Transmission", [])

        # 1. Power Chain: Power Supply -> powers -> Driver
        if powers and drivers:
            for p in powers:
                for d in drivers:
                    if not any(c.source == p.id and c.target == d.id for c in connections):
                        new_connections.append(ConnectionEdge(
                            id=f"infer-pwr-{p.id}-{d.id}",
                            source=p.id,
                            target=d.id,
                            type=ConnectionType.POWERS,
                            confidence=0.8,
                            explainability="Inferred Power Chain: Power Supply powers Driver."
                        ))
        
        # 2. Control Chain: Controller -> controls -> Driver
        if ctrls and drivers:
            for c in ctrls:
                for d in drivers:
                    if not any(conn.source == c.id and conn.target == d.id for conn in connections):
                        new_connections.append(ConnectionEdge(
                            id=f"infer-ctrl-{c.id}-{d.id}",
                            source=c.id,
                            target=d.id,
                            type=ConnectionType.CONTROLS,
                            confidence=0.8,
                            explainability="Inferred Control Chain: Controller controls Driver."
                        ))
        
        # 3. Motion Chain: Driver -> drives -> Motor -> transmits_motion_to -> Transmission
        if drivers and acts:
            for d in drivers:
                for a in acts:
                    if not any(conn.source == d.id and conn.target == a.id for conn in connections):
                        new_connections.append(ConnectionEdge(
                            id=f"infer-drv-{d.id}-{a.id}",
                            source=d.id,
                            target=a.id,
                            type=ConnectionType.DRIVES,
                            confidence=0.8,
                            explainability="Inferred Motion Chain: Driver drives Actuator."
                        ))

        if acts and transmissions:
            for a in acts:
                for t in transmissions:
                    if not any(conn.source == a.id and conn.target == t.id for conn in connections):
                        new_connections.append(ConnectionEdge(
                            id=f"infer-mech-{a.id}-{t.id}",
                            source=a.id,
                            target=t.id,
                            type=ConnectionType.TRANSMITS_MOTION_TO,
                            confidence=0.8,
                            explainability="Inferred Motion Chain: Actuator transmits_motion_to Transmission."
                        ))
                        
        # 4. Feedback Chain: Sensor -> provides_feedback_to -> Controller
        if sensors and ctrls:
            for s in sensors:
                for c in ctrls:
                    if not any(conn.source == s.id and conn.target == c.id for conn in connections):
                        new_connections.append(ConnectionEdge(
                            id=f"infer-sens-{s.id}-{c.id}",
                            source=s.id,
                            target=c.id,
                            type=ConnectionType.PROVIDES_FEEDBACK_TO,
                            confidence=0.8,
                            explainability="Inferred Feedback Chain: Sensor provides_feedback_to Controller."
                        ))

        return new_connections
