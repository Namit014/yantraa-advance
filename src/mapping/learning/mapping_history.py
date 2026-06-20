import os
import json
from datetime import datetime

class MappingHistory:
    def __init__(self):
        self.history_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            "../../../knowledgebase/learning"
        ))
        os.makedirs(self.history_dir, exist_ok=True)
        self.history_file = os.path.join(self.history_dir, "mapping_history.json")
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w') as f:
                json.dump({"history": []}, f)

    def record_graph(self, input_components: list[str], generated_graph: dict, user_modified: bool, accepted: bool):
        """
        Stores the accepted/modified graph in the history.
        """
        with open(self.history_file, 'r') as f:
            data = json.load(f)
            
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "input_components": input_components,
            "generated_graph": generated_graph,
            "user_modified": user_modified,
            "accepted": accepted
        }
        
        data["history"].append(record)
        
        with open(self.history_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_historical_score(self, source_id: str, target_id: str, edge_type: str) -> int:
        """
        Queries the history to see if users have frequently accepted or manually added 
        this specific connection.
        Returns a score from 0 to 10.
        """
        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
        except Exception:
            return 0
            
        score = 0
        for record in data.get("history", []):
            if not record.get("accepted"):
                continue
                
            wires = record.get("generated_graph", {}).get("wires", [])
            for wire in wires:
                from_id = wire.get("from", {}).get("nodeId")
                to_id = wire.get("to", {}).get("nodeId")
                w_type = wire.get("edge_type")
                
                if from_id == source_id and to_id == target_id and w_type == edge_type:
                    score += 5  # Increment score per historical occurrence
                    
        return min(score, 10)  # Max out at 10 as per rules
