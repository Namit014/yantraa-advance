import re
import math
from typing import List, Tuple, Dict, Any, Optional
from collections import defaultdict
import uuid

# 15 Fine-grained engineering subcategories
SUBCATEGORIES = [
    "Fastener", "Bearing", "Motor", "Encoder", "Sensor", 
    "Gearbox", "Bracket", "Housing", "PCB", "Connector", 
    "Wheel", "Actuator", "Valve", "Cylinder", "Frame", "Other"
]

# 16 Typed Engineering Relations
RELATION_TYPES = [
    "mounted_to", "bolted_to", "welded_to", "contains", "houses", 
    "supports", "drives", "transmits_torque_to", "rotates_about", 
    "slides_on", "limits_motion_of", "electrically_connected", 
    "pneumatically_connected", "hydraulically_connected", 
    "senses", "controls", "generic_connection"
]

class CanonicalComponent:
    def __init__(self, canonical_id: str, name: str, category: str, subcategory: str, aliases: List[str]):
        self.canonical_id = canonical_id
        self.name = name
        self.category = category
        self.subcategory = subcategory
        self.aliases = aliases

def canonicalize(name: str, aliases: List[str] = None) -> CanonicalComponent:
    """Normalizes part names and generates a canonical ID."""
    if aliases is None:
        aliases = []
    
    # Strip leading quantities like "4x ", "12 x "
    clean_name = re.sub(r'^\d+\s*[xX]\s*', '', name).strip()
    
    # Simple ID generation for now
    clean_id = f"COMP_{uuid.uuid4().hex[:8].upper()}"
    
    category, subcategory = classify(clean_name)
    
    return CanonicalComponent(clean_id, clean_name, category, subcategory, aliases)

def classify(component_name: str) -> Tuple[str, str]:
    """Maps a component name to a category and subcategory."""
    name_lower = component_name.lower()
    
    # Very basic classification heuristic
    if any(k in name_lower for k in ["motor", "servo", "actuator"]):
        return "actuator", "Motor" if "motor" in name_lower else "Actuator"
    if any(k in name_lower for k in ["sensor", "encoder", "imu", "camera"]):
        return "sensor", "Encoder" if "encoder" in name_lower else "Sensor"
    if any(k in name_lower for k in ["board", "pcb", "controller", "arduino", "raspberry"]):
        return "controller", "PCB"
    if any(k in name_lower for k in ["bracket", "frame", "housing", "gearbox", "bearing", "fastener", "screw", "bolt", "nut", "wheel"]):
        subcat = "Bracket" if "bracket" in name_lower else \
                 "Frame" if "frame" in name_lower else \
                 "Housing" if "housing" in name_lower else \
                 "Gearbox" if "gearbox" in name_lower else \
                 "Bearing" if "bearing" in name_lower else \
                 "Fastener" if any(x in name_lower for x in ["fastener", "screw", "bolt", "nut"]) else \
                 "Wheel" if "wheel" in name_lower else "Other"
        return "mechanical", subcat
    if any(k in name_lower for k in ["battery", "power", "supply"]):
        return "power", "Other"
    if any(k in name_lower for k in ["connector", "cable", "wire"]):
        return "electronic", "Connector"
        
    return "electronic", "Other"

def compute_confidence(geo_score: float, bom_score: float, drawing_score: float, metadata_score: float, llm_score: float) -> float:
    """Weighted 5-source score per edge."""
    return (0.35 * geo_score) + (0.20 * bom_score) + (0.15 * drawing_score) + (0.15 * metadata_score) + (0.15 * llm_score)

def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]

def detect_duplicates(components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merges duplicate components based on string similarity."""
    merged = []
    processed_indices = set()
    
    for i, c1 in enumerate(components):
        if i in processed_indices:
            continue
            
        current_group = [c1]
        processed_indices.add(i)
        
        name1 = c1.get("name", "").lower()
        
        for j in range(i + 1, len(components)):
            if j in processed_indices:
                continue
                
            c2 = components[j]
            name2 = c2.get("name", "").lower()
            
            # Simple threshold for similarity
            max_len = max(len(name1), len(name2))
            if max_len > 0 and levenshtein_distance(name1, name2) / max_len < 0.2:
                current_group.append(c2)
                processed_indices.add(j)
                
        # Merge the group
        base = current_group[0]
        if len(current_group) > 1:
            base["quantity"] = sum(c.get("quantity", 1) for c in current_group)
            
            all_connects = []
            for c in current_group:
                all_connects.extend(c.get("connects_to", []))
            base["connects_to"] = list(set(all_connects))
            
            # Combine aliases
            aliases = set(base.get("aliases", []))
            for c in current_group[1:]:
                aliases.add(c.get("name", ""))
                aliases.update(c.get("aliases", []))
            base["aliases"] = list(aliases)
            
        merged.append(base)
        
    return merged

def infer_relationship_type(source_cat: str, target_cat: str, source_name: str = "", target_name: str = "") -> str:
    """Infers engineering relation type."""
    pair = f"{source_cat}-{target_cat}"
    
    if pair == "mechanical-mechanical":
        if "bracket" in source_name.lower() or "bracket" in target_name.lower():
            return "mounted_to"
        return "bolted_to"
    if pair in ["actuator-mechanical", "mechanical-actuator"]:
        if "gearbox" in source_name.lower() or "gearbox" in target_name.lower():
            return "transmits_torque_to"
        return "drives"
    if pair in ["controller-actuator", "actuator-controller"]:
        return "controls"
    if pair in ["sensor-controller", "controller-sensor"]:
        return "senses"
    if "power" in pair:
        return "electrically_connected"
    if "electronic" in pair:
        return "electrically_connected"
        
    return "generic_connection"
