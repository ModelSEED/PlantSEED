#!/usr/bin/env python
import json
import yaml
import sys
from pathlib import Path

# Map string type names from the YAML back to Python built-in types
TYPE_MAP = {
    'str': str,
    'bool': bool,
    'list': list,
    'dict': dict,
    'int': int,
    'float': float
}

def load_schema(yaml_path):
    """Loads the schema from a YAML file and converts type strings to Python types."""
    if not yaml_path.exists():
        print(f"Error: Schema YAML file not found at {yaml_path}")
        print("Please ensure PlantSEED_Schema.yaml exists in the same directory as this script.")
        sys.exit(1)
        
    with open(yaml_path, 'r', encoding='utf-8') as f:
        raw_schema = yaml.safe_load(f)
        
    # Reconstruct the schema with actual Python types for validation
    schema = {}
    for key, rules in raw_schema.items():
        type_str = rules.get('type')
        if type_str not in TYPE_MAP:
            print(f"Error: Unknown type '{type_str}' in schema for key '{key}'")
            sys.exit(1)
            
        schema[key] = {
            'type': TYPE_MAP[type_str],
            'default': rules.get('default'),
            'required': rules.get('required', False)  # Defaults to False if missing
        }
    return schema

def validate_database(db_path, schema):
    """Iterates through the JSON database to ensure adherence to the loaded schema."""
    with open(db_path, 'r', encoding='utf-8') as f:
        db = json.load(f)

    errors_found = 0

    for idx, entry in enumerate(db):
        role_name = entry.get("role", f"Entry Index {idx}")

        # 1. Check for missing keys and correct data types
        for key, rules in schema.items():
            expected_type = rules["type"]
            is_required = rules["required"]

            if key not in entry:
                if is_required:
                    print(f"[MISSING KEY] '{key}' is REQUIRED but missing in role: '{role_name}'")
                    errors_found += 1
                # If it's missing but NOT required, we just move on
                continue
            
            elif not isinstance(entry[key], expected_type):
                actual_type = type(entry[key]).__name__
                print(f"[TYPE ERROR] '{key}' in '{role_name}' should be {expected_type.__name__}, but got {actual_type}")
                errors_found += 1

        # 2. Check for unexpected rogue keys
        for key in entry.keys():
            if key not in schema:
                print(f"[EXTRA KEY] Unrecognized key '{key}' found in role: '{role_name}'")
                errors_found += 1

    print("-" * 40)
    if errors_found == 0:
        print(f"Success! All {len(db)} entries perfectly match the schema.")
    else:
        print(f"Validation failed with {errors_found} formatting errors. See output above.")

if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent
    db_path = (script_dir / "../../../Data/PlantSEED_v3/PlantSEED_Roles.json").resolve()
    yaml_path = (script_dir / "PlantSEED_Schema.yaml").resolve()

    if not db_path.exists():
        print(f"Error: Could not find database at {db_path}")
    else:
        print("Loading PlantSEED_Schema.yaml...")
        schema_dict = load_schema(yaml_path)
        
        print("Starting PlantSEED database validation...")
        validate_database(db_path, schema_dict)