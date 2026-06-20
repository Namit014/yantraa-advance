class PortMapper:
    def __init__(self):
        pass

    def map_ports(self, source_comp: dict, target_comp: dict, required_type: str = None) -> list[dict]:
        """
        Attempts to match compatible ports between two components.
        Returns a list of dicts: [{"source_port": "A", "target_port": "B", "type": "signal"}]
        """
        connections = []
        source_ports = source_comp.get("ports", [])
        target_ports = target_comp.get("ports", [])

        # Typical matching rules:
        # signal_out -> signal_in or signal
        # power_out -> power_in or power
        # ground -> ground
        # data -> data
        
        for p1 in source_ports:
            for p2 in target_ports:
                if required_type and p1.get("type") != required_type and p2.get("type") != required_type:
                    continue

                if p1.get("type") == "signal_out" and p2.get("type") in ["signal_in", "signal"]:
                    connections.append({"source_port": p1["name"], "target_port": p2["name"], "type": "signal"})
                elif p1.get("type") == "power_out" and p2.get("type") in ["power_in", "power", "vcc"]:
                    connections.append({"source_port": p1["name"], "target_port": p2["name"], "type": "power"})
                elif p1.get("type") == "ground" and p2.get("type") == "ground":
                    connections.append({"source_port": p1["name"], "target_port": p2["name"], "type": "ground"})
                elif p1.get("type") == "data" and p2.get("type") == "data" and p1.get("name") == p2.get("name"): # e.g. SDA to SDA
                    connections.append({"source_port": p1["name"], "target_port": p2["name"], "type": "data"})
                elif p1.get("type") == "power" and p2.get("type") == "power":
                    connections.append({"source_port": p1["name"], "target_port": p2["name"], "type": "power"})
        
        # Deduplicate to avoid connecting a single port multiple times if not intended (simplification)
        return connections
