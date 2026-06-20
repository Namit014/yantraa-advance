import networkx as nx
from .learning.mapping_history import MappingHistory

class ConfidenceEngine:
    def __init__(self):
        self.history = MappingHistory()

    def calculate(self, G: nx.MultiDiGraph):
        """
        Refines the confidence scores of edges. Removes edges below threshold.
        """
        edges_to_remove = []
        for u, v, k, data in G.edges(keys=True, data=True):
            # Base score from RuleEngine
            confidence = data.get("confidence", 0)
            
            # Historical Match
            hist_score = self.history.get_historical_score(u, v, data.get("edge_type", ""))
            
            # Base confidence includes Rule(30) + Port(25) + Protocol(15) + Dep(10) + Volt(10) = 90
            # History provides the final 10 points. If the base rule gave 90, history gives it up to 100.
            if confidence > 0:
                # Assuming base rules gave out of 90, add history
                # Normalize base rule score down a bit to leave room for history
                confidence = int(confidence * 0.9) + hist_score
                
            data["confidence"] = min(confidence, 100)

            if data["confidence"] < 80:
                edges_to_remove.append((u, v, k))

        for u, v, k in edges_to_remove:
            G.remove_edge(u, v, key=k)
        
        return G
