import re

class DeterministicRecoveryEngine:
    """
    Implements Fix #3, #7, #8: Deterministic fallback graph generation.
    When LLM generation fails, use regex and engineering ontology to extract components 
    and infer basic connections to prevent an empty canvas.
    """

    ONTOLOGY = {
        "motor": "Actuator",
        "stepper": "Actuator",
        "servo": "Actuator",
        "gearbox": "Transmission",
        "controller": "Controller",
        "arduino": "Controller",
        "raspberry": "Controller",
        "driver": "Driver",
        "shield": "Driver",
        "power supply": "Power",
        "battery": "Power",
        "encoder": "Sensor",
        "sensor": "Sensor",
        "bearing": "Mechanical",
        "rail": "Mechanical",
        "screw": "Mechanical",
        "joint": "Mechanical"
    }

    @staticmethod
    def extract_components(query: str) -> list:
        components = []
        query_lower = query.lower()
        
        # Simple extraction based on keyword presence if the query is detailed, 
        # or just fallback components for known robot types.
        if "scara" in query_lower:
            components = [
                {"id": "comp_fallback_ctrl", "name": "Main Controller", "category": "controller"},
                {"id": "comp_fallback_psu", "name": "24V Power Supply", "category": "power"},
                {"id": "comp_fallback_j1", "name": "Base Motor (J1)", "category": "actuator"},
                {"id": "comp_fallback_j2", "name": "Arm Motor (J2)", "category": "actuator"},
                {"id": "comp_fallback_j3", "name": "Z-Axis Motor (J3)", "category": "actuator"},
                {"id": "comp_fallback_end", "name": "End Effector", "category": "mechanical"}
            ]
        elif "delta" in query_lower:
            components = [
                {"id": "comp_fallback_ctrl", "name": "Main Controller", "category": "controller"},
                {"id": "comp_fallback_psu", "name": "24V Power Supply", "category": "power"},
                {"id": "comp_fallback_m1", "name": "Arm 1 Motor", "category": "actuator"},
                {"id": "comp_fallback_m2", "name": "Arm 2 Motor", "category": "actuator"},
                {"id": "comp_fallback_m3", "name": "Arm 3 Motor", "category": "actuator"},
                {"id": "comp_fallback_end", "name": "Platform & Gripper", "category": "mechanical"}
            ]
        elif "agv" in query_lower:
            components = [
                {"id": "comp_fallback_ctrl", "name": "Navigation Controller", "category": "controller"},
                {"id": "comp_fallback_batt", "name": "Main Battery Pack", "category": "power"},
                {"id": "comp_fallback_dl", "name": "Left Drive Motor", "category": "actuator"},
                {"id": "comp_fallback_dr", "name": "Right Drive Motor", "category": "actuator"},
                {"id": "comp_fallback_lidar", "name": "LIDAR Sensor", "category": "sensor"}
            ]
        else:
            # Generic fallback
            components = [
                {"id": "comp_fallback_ctrl", "name": "System Controller", "category": "controller"},
                {"id": "comp_fallback_psu", "name": "Power Supply", "category": "power"},
                {"id": "comp_fallback_act", "name": "Primary Actuator", "category": "actuator"}
            ]

        # Add tracking metadata
        for c in components:
            c["confidence"] = "LOW"
            c["source"] = "FALLBACK"
            
        return components

    @staticmethod
    def extract_connections(components: list) -> list:
        connections = []
        
        by_cat = {}
        for c in components:
            by_cat.setdefault(c["category"], []).append(c)

        ctrls = by_cat.get("controller", [])
        pwrs = by_cat.get("power", [])
        acts = by_cat.get("actuator", [])
        sens = by_cat.get("sensor", [])
        mechs = by_cat.get("mechanical", [])

        # Power -> Controller
        for p in pwrs:
            for c in ctrls:
                connections.append({"from": p["id"], "to": c["id"], "type": "power", "source": "FALLBACK"})

        # Power -> Actuator
        for p in pwrs:
            for a in acts:
                connections.append({"from": p["id"], "to": a["id"], "type": "power", "source": "FALLBACK"})

        # Controller -> Actuator
        for c in ctrls:
            for a in acts:
                connections.append({"from": c["id"], "to": a["id"], "type": "data", "source": "FALLBACK"})

        # Sensor -> Controller
        for s in sens:
            for c in ctrls:
                connections.append({"from": s["id"], "to": c["id"], "type": "data", "source": "FALLBACK"})

        # Actuator -> Mechanical
        if acts and mechs:
            for m in mechs:
                connections.append({"from": acts[0]["id"], "to": m["id"], "type": "mechanical", "source": "FALLBACK"})

        return connections
