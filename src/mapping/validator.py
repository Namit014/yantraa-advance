import networkx as nx

class Validator:
    def __init__(self):
        pass

    def validate(self, G: nx.MultiDiGraph, registry) -> list[dict]:
        """
        Runs validation checks on the graph. Returns a list of warnings or errors.
        """
        issues = []
        
        for n, data in G.nodes(data=True):
            category = data.get("category")
            if category in ["actuator", "sensor", "controller"]:
                # Check for power
                in_power_edges = [u for u, v, k, d in G.in_edges(n, data=True, keys=True) if d.get("edge_type") == "POWER_EDGE"]
                out_power_edges = [v for u, v, k, d in G.out_edges(n, data=True, keys=True) if d.get("edge_type") == "POWER_EDGE"]
                if not in_power_edges and category != "power" and not out_power_edges:
                    issues.append({"node": n, "type": "warning", "message": f"{data.get('name')} is missing a power connection."})

                # Check for control on actuators/sensors
                if category in ["actuator", "sensor"]:
                    control_edges = [u for u, v, k, d in G.in_edges(n, data=True, keys=True) if d.get("edge_type") in ["CONTROL_EDGE", "DATA_EDGE"]]
                    out_control_edges = [v for u, v, k, d in G.out_edges(n, data=True, keys=True) if d.get("edge_type") in ["CONTROL_EDGE", "DATA_EDGE"]]
                    if not control_edges and not out_control_edges:
                        issues.append({"node": n, "type": "warning", "message": f"{data.get('name')} is missing a control/data connection."})

        # Future: Voltage matching, protocol validation (if not already handled by PortMapper)
        return issues
