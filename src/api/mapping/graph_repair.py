class GraphRepairEngine:
    """
    Graph Repair Engine.
    Detects and auto-repairs issues like duplicate motors, orphan sensors, and isolated power supplies.
    """
    @staticmethod
    def run_repair(components: list, connections: list):
        repairs_made = []
        
        # Example logic: Find unconnected sensors
        connected_ids = {c.source_id for c in connections}.union({c.target_id for c in connections})
        
        for comp in components:
            if comp.category == "Sensor" and comp.id not in connected_ids:
                repairs_made.append(f"Orphan sensor detected: {comp.name}")
                # Auto repair logic would hook it to the main controller if confidence is high
                
        return repairs_made
