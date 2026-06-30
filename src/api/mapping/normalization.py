from typing import Dict, Any

def normalize_component(raw_name: str) -> Dict[str, Any]:
    """
    Normalizes a user-input component name into a standard component structure.
    Example: '17HS4401' -> Standard Component: Stepper Motor, Subtype: NEMA17
    """
    raw_lower = raw_name.lower()
    
    # Simple heuristic normalizations
    if any(keyword in raw_lower for keyword in ["17hs", "nema17", "nema-17"]):
        return {
            "name": "NEMA17 Stepper Motor",
            "standard_component": "Stepper Motor",
            "subtype": "NEMA17",
            "category": "actuator"
        }
    
    if any(keyword in raw_lower for keyword in ["mega2560", "atmega2560", "arduino mega"]):
        return {
            "name": "Arduino Mega 2560",
            "standard_component": "Microcontroller",
            "subtype": "Arduino Mega",
            "category": "controller"
        }
        
    if "tb6600" in raw_lower:
        return {
            "name": "TB6600 Stepper Driver",
            "standard_component": "Stepper Driver",
            "subtype": "TB6600",
            "category": "electronic"
        }

    # Fallback
    return {
        "name": raw_name,
        "standard_component": "Unknown",
        "subtype": "Generic",
        "category": "unknown"
    }

def fetch_manufacturer_data(component_dict: Dict[str, Any], manufacturer_db: dict) -> None:
    """Enhances the component with manufacturer database info."""
    subtype = component_dict.get("subtype", "")
    if subtype in manufacturer_db:
        component_dict["manufacturer"] = manufacturer_db[subtype].get("brand", "Unknown")
    else:
        component_dict["manufacturer"] = "Generic"
