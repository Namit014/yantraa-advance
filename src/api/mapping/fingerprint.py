import hashlib

class ComponentFingerprint:
    """
    Generates component hashes based on physical and electrical specifications.
    Used during entity resolution; much more accurate than fuzzy matching.
    """
    @staticmethod
    def generate_hash(specs: dict) -> str:
        # Sort keys to ensure consistent hashing
        sorted_items = sorted(specs.items())
        spec_string = "|".join(f"{k}:{v}" for k, v in sorted_items)
        return hashlib.sha256(spec_string.encode('utf-8')).hexdigest()
