"""
Validates parts-db.json schema completeness.
Fails loudly if any pin is missing skidl_type,
or any power-category part is missing output_rails.
"""
import json
import os

def validate_parts_db(parts_db: list) -> list[str]:
    errors = []
    for part in parts_db:
        for i, pin in enumerate(part.get("pins", [])):
            if "skidl_type" not in pin:
                errors.append(f"{part['id']} pin[{i}] '{pin.get('name','?')}' missing skidl_type")
        if part.get("category") == "power" and "output_rails" not in part:
            errors.append(f"{part['id']} is category=power but missing output_rails")
    return errors

def test_parts_db_schema():
    # Construct path relative to this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
    db_path = os.path.join(project_root, "knowledgebase", "parts-db.json")
    
    with open(db_path, "r", encoding="utf-8") as f:
        db = json.load(f)
    
    errors = validate_parts_db(db)
    
    if errors:
        print("Validation Failed! Errors found:")
        for err in errors:
            print(f" - {err}")
        assert False, f"Found {len(errors)} validation errors in parts-db.json"
    else:
        print("Validation Passed: parts-db.json is structurally sound.")

if __name__ == "__main__":
    test_parts_db_schema()
