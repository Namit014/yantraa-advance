import os
import re
import json

def parse_kicad_sym(filepath):
    """Parses a .kicad_sym file and yields components."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple regex to find symbols
    # We find blocks of (symbol "Library:Name" ... )
    symbol_blocks = re.findall(r'\(symbol\s+"([^"]+)"([\s\S]*?)(?=\n\s*\(symbol|\Z)', content)
    
    for name, block in symbol_blocks:
        if name.endswith("_0_0") or name.endswith("_0_1") or name.endswith("_1_1"):
            continue # Skip sub-symbols for graphics
            
        # Clean up the name (often it's 'LibraryName:PartName', but inside the file it's just 'PartName')
        part_name = name
        
        # Extract properties
        prod_id_match = re.search(r'\(property\s+"PROD_ID"\s+"([^"]+)"', block)
        desc_match = re.search(r'\(property\s+"ki_description"\s+"([^"]+)"', block)
        footprint_match = re.search(r'\(property\s+"Footprint"\s+"([^"]+)"', block)
        
        prod_id = prod_id_match.group(1) if prod_id_match else None
        desc = desc_match.group(1) if desc_match else ""
        footprint = footprint_match.group(1) if footprint_match else None
        
        # We only really care about parts with a PROD_ID or at least a distinct footprint
        if prod_id or footprint:
            yield {
                "name": part_name,
                "description": desc,
                "prod_id": prod_id,
                "footprint": footprint
            }

def parse_kicad_mod(filepath):
    """Parses a .kicad_mod file and extracts 3D model paths."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract (model "...") paths
    model_matches = re.findall(r'\(model\s+"([^"]+\.step)"', content, re.IGNORECASE)
    
    # Replace ${SPARKFUN_KICAD_LIBRARY} or ${KICAD9_3RD_PARTY} with the relative path
    models = []
    for m in model_matches:
        m = m.replace("${SPARKFUN_KICAD_LIBRARY}", "")
        m = m.replace("${KICAD9_3RD_PARTY}", "")
        # Normalize slashes
        m = m.replace("\\", "/").lstrip("/")
        models.append(m)
        
    return models

def main():
    base_dir = os.path.join("knowledgebase", "SparkFun-KiCad-Libraries")
    if not os.path.exists(base_dir):
        print("SparkFun-KiCad-Libraries not found. Run git clone first.")
        return
        
    symbols_dir = os.path.join(base_dir, "symbols")
    footprints_dir = os.path.join(base_dir, "footprints")
    
    components = []
    footprint_model_cache = {}
    
    print("Parsing footprint models...")
    if os.path.exists(footprints_dir):
        for root, dirs, files in os.walk(footprints_dir):
            for file in files:
                if file.endswith(".kicad_mod"):
                    fp_name = file.replace(".kicad_mod", "")
                    pretty_folder = os.path.basename(root)
                    if pretty_folder.endswith(".pretty"):
                        lib_name = pretty_folder.replace(".pretty", "")
                        full_fp = f"{lib_name}:{fp_name}"
                        models = parse_kicad_mod(os.path.join(root, file))
                        if models:
                            footprint_model_cache[full_fp] = models[0]
                            
    print(f"Loaded {len(footprint_model_cache)} footprints with models.")

    print("Parsing symbols...")
    if os.path.exists(symbols_dir):
        for root, dirs, files in os.walk(symbols_dir):
            for file in files:
                if file.endswith(".kicad_sym"):
                    for comp in parse_kicad_sym(os.path.join(root, file)):
                        # Look up model from footprint
                        if comp["footprint"]:
                            model_path = footprint_model_cache.get(comp["footprint"])
                            if model_path:
                                comp["model_path"] = model_path
                        
                        components.append(comp)
                        
    print(f"Extracted {len(components)} components.")
    
    # Filter only components that have a 3D model for our React Flow visualizer
    visual_components = [c for c in components if c.get("model_path")]
    print(f"Components with 3D models: {len(visual_components)}")
    
    output_file = os.path.join("knowledgebase", "sparkfun_components.json")
    with open(output_file, 'w') as f:
        json.dump(visual_components, f, indent=2)
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    main()
