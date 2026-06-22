import os
import re
import json
from datetime import datetime

def analyze_step_file(filepath: str) -> dict:
    """
    Parses a STEP file using regex to extract metadata and components.
    Returns a dictionary suitable for JSON serialization.
    """
    if not os.path.exists(filepath):
        return {"error": "File not found"}

    metadata = {}
    components = set()

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # --- Extract Header Metadata ---
    # FILE_NAME ('Name', 'Time', ('Author'), ('Organization'), 'Preprocessor', 'Originator', 'Authorization');
    file_name_match = re.search(r"FILE_NAME\s*\(\s*'([^']*)'\s*,\s*'([^']*)'", content, re.IGNORECASE)
    if file_name_match:
        metadata["filename"] = file_name_match.group(1)
        metadata["date_created"] = file_name_match.group(2)
        
    author_match = re.search(r"FILE_NAME\s*\(.*?\s*,\s*.*?\s*,\s*\(\s*'([^']*)'\s*\)", content, re.IGNORECASE)
    if author_match:
        metadata["author"] = author_match.group(1)

    org_match = re.search(r"FILE_NAME\s*\(.*?\s*,\s*.*?\s*,\s*.*?\s*,\s*\(\s*'([^']*)'\s*\)", content, re.IGNORECASE)
    if org_match:
        metadata["organization"] = org_match.group(1)

    # --- Extract Components ---
    # We look for PRODUCT entities: PRODUCT ( 'id', 'name', 'description', (context) )
    # This represents distinct parts and assemblies.
    product_matches = re.finditer(r"PRODUCT\s*\(\s*'[^']*'\s*,\s*'([^']+)'", content)
    for match in product_matches:
        part_name = match.group(1).strip()
        if part_name:
            components.add(part_name)

    # Convert to list and sort
    component_list = sorted(list(components))
    
    return {
        "metadata": metadata,
        "components": component_list,
        "total_components_found": len(component_list),
        "analyzed_at": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        res = analyze_step_file(sys.argv[1])
        print(json.dumps(res, indent=2))
