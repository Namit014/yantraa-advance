class Rule:
    def __init__(self, priority=0):
        self.priority = priority

    def evaluate(self, source_comp, target_comp, compatibility_engine, port_mapper):
        pass

class ServoRule(Rule):
    def __init__(self):
        super().__init__(priority=100)

    def evaluate(self, source_comp, target_comp, compatibility_engine, port_mapper):
        # Specific logic for Servo
        edges = []
        if source_comp.get("subcategory") == "motion_controller" and target_comp.get("subcategory") == "servo":
            # Check control port mapping
            mapped_ports = port_mapper.map_ports(source_comp, target_comp, required_type="signal_out")
            for port_mapping in mapped_ports:
                edges.append({
                    "source": source_comp["id"],
                    "target": target_comp["id"],
                    "edge_type": "CONTROL_EDGE",
                    "protocol": "PWM",
                    "confidence": 98,
                    "ports": port_mapping,
                    "why_connected": [
                        "ServoRule matched",
                        "PWM Compatibility verified",
                        "Controller dependency satisfied"
                    ]
                })
        elif source_comp.get("category") == "power" and target_comp.get("subcategory") == "servo":
            mapped_ports = port_mapper.map_ports(source_comp, target_comp, required_type="power")
            for port_mapping in mapped_ports:
                edges.append({
                    "source": source_comp["id"],
                    "target": target_comp["id"],
                    "edge_type": "POWER_EDGE",
                    "protocol": "none",
                    "confidence": 95,
                    "ports": port_mapping,
                    "why_connected": [
                        "ServoRule matched",
                        "Power delivery verified",
                        "Power dependency satisfied"
                    ]
                })
        return edges

class GenericActuatorRule(Rule):
    def __init__(self):
        super().__init__(priority=20)

    def evaluate(self, source_comp, target_comp, compatibility_engine, port_mapper):
        edges = []
        if compatibility_engine.can_connect(source_comp.get("subcategory"), target_comp.get("subcategory")):
            mapped_ports = port_mapper.map_ports(source_comp, target_comp)
            for port_mapping in mapped_ports:
                edge_type = "DATA_EDGE"
                if port_mapping.get("type") == "power": edge_type = "POWER_EDGE"
                elif port_mapping.get("type") == "signal": edge_type = "CONTROL_EDGE"
                
                edges.append({
                    "source": source_comp["id"],
                    "target": target_comp["id"],
                    "edge_type": edge_type,
                    "protocol": target_comp.get("protocol", "unknown"),
                    "confidence": 60, # Lower confidence for generic rule
                    "ports": port_mapping,
                    "why_connected": [
                        "GenericActuatorRule matched",
                        f"Port match: {port_mapping.get('type')}",
                        "Subcategory compatibility matrix matched"
                    ]
                })
        return edges

class RuleEngine:
    def __init__(self):
        self.rules = [ServoRule(), GenericActuatorRule()]
        # Sort by priority descending
        self.rules.sort(key=lambda x: x.priority, reverse=True)

    def evaluate_pair(self, source_comp, target_comp, compatibility_engine, port_mapper):
        all_edges = []
        for rule in self.rules:
            edges = rule.evaluate(source_comp, target_comp, compatibility_engine, port_mapper)
            if edges:
                all_edges.extend(edges)
                break # Apply highest priority rule that yields a result
        return all_edges
