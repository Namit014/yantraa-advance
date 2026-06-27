import hashlib
from typing import List, Dict
from .schemas import ComponentNode

class ComponentFingerprint:
    """
    Phase 3: Component Fingerprinting.
    Generates hashes based on part numbers, dimensions, voltage, etc.
    """
    @staticmethod
    def generate_hash(specs: dict) -> str:
        # Filter out empty or None values before hashing
        clean_specs = {k: v for k, v in specs.items() if v}
        if not clean_specs:
            return ""
        sorted_items = sorted(clean_specs.items())
        spec_string = "|".join(f"{k}:{v}" for k, v in sorted_items)
        return hashlib.sha256(spec_string.encode('utf-8')).hexdigest()

class EntityResolutionEngine:
    """
    Phase 4: Entity Resolution.
    Merges components only if confidence > 0.9 and fingerprints match.
    Never merge based solely on name similarity.
    """
    @staticmethod
    def resolve_entities(components: List[ComponentNode]) -> List[ComponentNode]:
        resolved: Dict[str, ComponentNode] = {}
        
        for c in components:
            if not c.fingerprint_hash:
                # If no fingerprint, we cannot merge it safely under V3 rules. Keep it separate.
                resolved[c.id] = c
                continue
                
            match_found = False
            for r_id, r_comp in resolved.items():
                if r_comp.fingerprint_hash == c.fingerprint_hash:
                    # Fingerprints match, check confidence threshold
                    if c.confidence > 0.9 and r_comp.confidence > 0.9:
                        # Merge evidence
                        r_comp.evidence.extend(c.evidence)
                        match_found = True
                        break
            
            if not match_found:
                resolved[c.id] = c
                
        return list(resolved.values())
