import networkx as nx
from .rules.base_rule import RuleEngine

class GraphBuilder:
    def __init__(self, registry, compatibility_engine, port_mapper):
        self.registry = registry
        self.compatibility_engine = compatibility_engine
        self.port_mapper = port_mapper
        self.rule_engine = RuleEngine()

    def build_graph(self, component_ids: list[str]) -> nx.MultiDiGraph:
        """
        Builds a multi-layer directed graph.
        Using MultiDiGraph to allow multiple edges (power, control, mechanical) between the same nodes.
        """
        G = nx.MultiDiGraph()

        # Add nodes
        for cid in component_ids:
            comp_data = self.registry.get_component(cid)
            if comp_data:
                G.add_node(cid, **comp_data)

        # Build edges by evaluating all pairs
        for source_id in component_ids:
            for target_id in component_ids:
                if source_id == target_id:
                    continue
                
                source_comp = self.registry.get_component(source_id)
                target_comp = self.registry.get_component(target_id)
                
                if not source_comp or not target_comp:
                    continue

                edges = self.rule_engine.evaluate_pair(
                    source_comp, target_comp, self.compatibility_engine, self.port_mapper
                )

                for edge in edges:
                    G.add_edge(
                        edge["source"], 
                        edge["target"], 
                        edge_type=edge["edge_type"],
                        protocol=edge.get("protocol"),
                        confidence=edge.get("confidence", 0),
                        ports=edge.get("ports", {}),
                        why_connected=edge.get("why_connected", [])
                    )
                    
        return G

    def to_json(self, G: nx.MultiDiGraph) -> dict:
        nodes = []
        for n, data in G.nodes(data=True):
            nodes.append({
                "id": data.get("id", n),
                "label": data.get("name", n),
                "type": data.get("category", "other"),
                "ports": data.get("ports", [])
            })

        wires = []
        for u, v, k, data in G.edges(keys=True, data=True):
            wires.append({
                "id": f"wire-{u}-{v}-{k}",
                "from": {"nodeId": u, "portId": data.get("ports", {}).get("source_port")},
                "to": {"nodeId": v, "portId": data.get("ports", {}).get("target_port")},
                "edge_type": data.get("edge_type"),
                "protocol": data.get("protocol"),
                "confidence": data.get("confidence"),
                "why_connected": data.get("why_connected", [])
            })

        return {"nodes": nodes, "wires": wires}
