#!/usr/bin/env python3

import builtins
import json
import os
import re
import subprocess
import sys
import urllib.request
import tempfile
import yaml

EXIT_SHORTCUT = "!!"
_original_input = builtins.input
def _input(prompt=""):
    val = _original_input(prompt)
    if val.strip() == EXIT_SHORTCUT:
        print("\nExiting script.")
        sys.exit(0)
    return val
builtins.input = _input

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROLES_FILE = os.path.join(BASE_DIR, "..", "..", "..", "Data", "PlantSEED_v3", "PlantSEED_Roles.json")
ENZYME_DAT_URL = "https://ftp.expasy.org/databases/enzyme/enzyme.dat"
ENZYME_DAT_CACHE = os.path.join(tempfile.gettempdir(), "plantseed_enzyme.dat")
CURATORS_DIR = os.path.join(BASE_DIR, "Curators")
SCHEMA_FILE = os.path.join(BASE_DIR, "PlantSEED_Schema.yaml")

def get_git_username():
    try:
        return subprocess.run(
            ["git", "config", "user.name"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return input("Could not detect git username. Enter your name: ").strip()

def sanitize_username(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

def load_roles():
    with open(os.path.normpath(ROLES_FILE)) as f:
        return [r["role"] for r in json.load(f)]

def load_full_roles():
    with open(os.path.normpath(ROLES_FILE)) as f:
        return json.load(f)

TYPE_MAP = {'str': str, 'bool': bool, 'list': list, 'dict': dict, 'int': int}

def load_schema():
    if not os.path.exists(SCHEMA_FILE):
        return None
    with open(SCHEMA_FILE) as f:
        raw = yaml.safe_load(f)
    schema = {}
    for key, rules in raw.items():
        schema[key] = {
            'type': TYPE_MAP.get(rules.get('type'), str),
            'default': rules.get('default'),
            'required': rules.get('required', False)
        }
    return schema

def fuzzy_match(term, choices):
    t = term.lower()
    return [c for c in choices if t in c.lower()]

def fetch_enzyme_dat():
    if not os.path.exists(ENZYME_DAT_CACHE) or os.path.getsize(ENZYME_DAT_CACHE) == 0:
        print("Downloading enzyme.dat from Expasy...")
        try:
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(ENZYME_DAT_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ctx) as response, open(ENZYME_DAT_CACHE, 'wb') as out_file:
                out_file.write(response.read())
            print("Done.")
        except Exception as e:
            print(f"Warning: could not download enzyme.dat ({e})")
            if os.path.exists(ENZYME_DAT_CACHE):
                os.remove(ENZYME_DAT_CACHE)
            return []
    entries = []
    try:
        with open(ENZYME_DAT_CACHE, encoding="latin-1") as f:
            lines = f.read()
    except Exception as e:
        print(f"Error reading {ENZYME_DAT_CACHE}: {e}")
        return []
    for block in lines.split("\n//\n"):
        ec_id = ""
        de_lines = []
        for line in block.strip().split("\n"):
            if line.startswith("ID   "):
                ec_id = line[5:].strip()
            elif line.startswith("DE   "):
                de_lines.append(line[5:].strip())
        if ec_id and de_lines:
            de_full = " ".join(de_lines)
            de_full = de_full[0].upper() + de_full[1:] if de_full else de_full
            de_full = de_full.rstrip(".")
            entries.append(f"{de_full} (EC {ec_id})")
    if not entries:
        if os.path.exists(ENZYME_DAT_CACHE):
            os.remove(ENZYME_DAT_CACHE)
    return entries

def numbered_select(prompt_text, options):
    print()
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        try:
            idx = int(input(f"{prompt_text} ").strip()) - 1
            if 0 <= idx < len(options):
                return options[idx]
            print(f"Enter a number between 1 and {len(options)}.")
        except ValueError:
            print(f"Enter a number between 1 and {len(options)}.")

def select_enzyme_combined(roles, ec_entries):
    print("\n" + "="*70)
    print("ENZYME SEARCH (PlantSEED + Expasy)")
    print("="*70)
    while True:
        partial = input("Type enzyme name (at least 5 letters): ").strip()
        if len(partial) < 5:
            print("Please enter at least 5 letters for search.")
            continue
        plantseed_matches = fuzzy_match(partial, roles)
        expasy_matches = fuzzy_match(partial, ec_entries) if ec_entries else []
        if not plantseed_matches and not expasy_matches:
            retry = input("No matches found. (r)etry, (n)ovel enzyme: ").strip().lower()
            if retry == 'n':
                name = input("Enter full name for the new enzyme: ").strip()
                if name:
                    return name, True
            continue
        print("\nPlantSEED Enzymes:")
        print("-"*50)
        for i, match in enumerate(plantseed_matches):
            print(f"{i+1} | {match}")
        if expasy_matches:
            print("\nExpasy Enzymes:")
            print("-"*50)
            for i, match in enumerate(expasy_matches):
                print(f"{chr(97+i)} | {match}")
        print("-"*50)
        selection = input("Select enzyme (number/letter, (r)etry, (n)ovel enzyme): ").strip().lower()
        if selection == 'r':
            continue
        if selection == 'n':
            name = input("Enter full name for the new enzyme: ").strip()
            if name:
                return name, True
            continue
        if selection.isdigit():
            idx = int(selection) - 1
            if 0 <= idx < len(plantseed_matches):
                selected = plantseed_matches[idx]
                print(f"Selected PlantSEED enzyme: {selected}")
                return selected, False
            print("Invalid number selection.")
        elif len(selection) == 1 and selection.isalpha():
            idx = ord(selection) - 97
            if 0 <= idx < len(expasy_matches):
                selected = expasy_matches[idx]
                already_in_plantseed = selected in plantseed_matches
                print(f"Selected Expasy enzyme: {selected}")
                if already_in_plantseed:
                    print("(This enzyme is already in PlantSEED.)")
                    return selected, False
                else:
                    print("WARNING: This enzyme is not in PlantSEED and will create a new entry.")
                    return selected, True
            print("Invalid letter selection.")
        else:
            print("Please enter a number, letter, or 'n' for a novel enzyme.")

def prompt_required(prompt_text):
    while True:
        val = input(prompt_text).strip()
        if val:
            return val

def get_target_file(username):
    while True:
        default_filename = input("Enter a filename for this curation (e.g. Updates.tsv): ").strip()
        if not default_filename:
            default_filename = "Updates.tsv"
        if not default_filename.endswith(".tsv"):
            default_filename += ".tsv"
        target_file = os.path.join(CURATORS_DIR, username, default_filename)
        full_path = os.path.abspath(target_file)
        print(f"Target file: {full_path}")
        if os.path.exists(target_file):
            overwrite = input("File already exists. Append to it? (y/n): ").strip().lower()
            if overwrite == 'y':
                return target_file
            print("Enter a different filename.")
        else:
            return target_file

def handle_add(entity, full_roles):
    options = ["features", "publications", "reactions", "subsystems", "localization", "classes"]
    field = numbered_select("Select field:", options)
    lines = []
    multi_col = field in ("features", "reactions", "subsystems")
    if multi_col:
        print(f"Enter {field} value(s), one per line. Blank line to finish.")
        print(f"Format: <value> or <key>\\t<extra>")
        while True:
            v = input().strip()
            if not v:
                break
            parts = v.split("\t")
            value = parts[0]
            if field == "reactions":
                matches = find_exact_match(full_roles, "reactions", value)
                if matches:
                    display = matches[:5]
                    rest = len(matches) - 5
                    msg = f"  Note: '{value}' is already used by: {', '.join(display)}"
                    if rest > 0:
                        msg += f" (+{rest} more)"
                    print(msg)
            elif field == "publications":
                matches = find_exact_match(full_roles, "publications", value)
                if matches:
                    display = matches[:5]
                    rest = len(matches) - 5
                    msg = f"  Note: '{value}' is already used by: {', '.join(display)}"
                    if rest > 0:
                        msg += f" (+{rest} more)"
                    print(msg)
            elif field == "features":
                matches = find_substring_match(full_roles, "features", value)
                if matches:
                    display = matches[:5]
                    rest = len(matches) - 5
                    msg = f"  Note: '{value}' matches features in: {', '.join(display)}"
                    if rest > 0:
                        msg += f" (+{rest} more)"
                    print(msg)
            if len(parts) > 1:
                lines.append(f"{entity}\tADD\t{field}\t{parts[0]}\t{parts[1]}")
            else:
                lines.append(f"{entity}\tADD\t{field}\t{parts[0]}")
    else:
        print("Enter entry value(s), one per line. Blank line to finish:")
        while True:
            v = input().strip()
            if not v:
                break
            lines.append(f"{entity}\tADD\t{field}\t{v}")
    return lines

def handle_remove(entity):
    options = ["features", "publications", "reactions", "subsystems", "localization", "classes"]
    field = numbered_select("Select field:", options)
    print("Enter entry value(s) to remove, one per line. Blank line to finish:")
    lines = []
    while True:
        v = input().strip()
        if not v:
            break
        lines.append(f"{entity}\tREMOVE\t{field}\t{v}")
    return lines

def handle_relocate(entity):
    options = ["localization", "compartmentalization"]
    field = numbered_select("Select field:", options)
    old_entry = prompt_required("Enter old entry value: ")
    new_entry = prompt_required("Enter new entry value: ")
    return [f"{entity}\tRELOCATE\t{field}\t{old_entry}\t{new_entry}"]

def handle_change(entity):
    options = ["abstract_enzyme", "include"]
    field = numbered_select("Select field:", options)
    value = prompt_required("Enter new value: ")
    return [f"{entity}\tCHANGE\t{field}\t{value}"]

def handle_assign(entity):
    options = ["include", "type"]
    field = numbered_select("Select field:", options)
    value = prompt_required("Enter value: ")
    return [f"{entity}\tASSIGN\t{field}\t{value}"]

ACTION_OPTIONS = ["ADD", "ASSIGN", "CHANGE", "RELOCATE", "REMOVE", "UPDATE"]
ACTION_DESCRIPTIONS = {
    "ADD": "features, publications, reactions, subsystems, localization, classes",
    "ASSIGN": "include, type",
    "CHANGE": "abstract_enzyme, include",
    "RELOCATE": "localization, compartmentalization",
    "REMOVE": "features, publications, reactions, subsystems, localization, classes",
    "UPDATE": "rename enzyme",
}

def select_action(is_new_enzyme):
    if is_new_enzyme:
        print("New enzyme detected. Action automatically set to NEW.")
        return "NEW"
    print()
    for i, opt in enumerate(ACTION_OPTIONS, 1):
        desc = ACTION_DESCRIPTIONS[opt]
        print(f"  {i}. {opt:9s} ({desc})")
    while True:
        try:
            idx = int(input("Select action: ").strip()) - 1
            if 0 <= idx < len(ACTION_OPTIONS):
                return ACTION_OPTIONS[idx]
            print(f"Enter a number between 1 and {len(ACTION_OPTIONS)}.")
        except ValueError:
            print(f"Enter a number between 1 and {len(ACTION_OPTIONS)}.")

def check_required_fields(entity_name, full_roles, schema):
    if schema is None:
        return
    entry = None
    for r in full_roles:
        if r.get("role") == entity_name:
            entry = r
            break
    if entry is None:
        return
    warnings = []
    for field, rules in schema.items():
        if not rules['required']:
            continue
        if field in ("role", "include", "type", "is_transporter"):
            continue
        actual = entry.get(field)
        default = rules['default']
        if isinstance(default, (list, dict)) and actual == default:
            warnings.append(f"  - '{field}' is empty")
        elif isinstance(default, str) and actual == default == '':
            warnings.append(f"  - '{field}' is empty")
    if warnings:
        print()
        print("NOTE: This enzyme has some required fields that are empty or need attention:")
        for w in warnings:
            print(w)
        print("You can use the ADD action to populate these fields later.")
        input("Press Enter to skip and continue...")

def find_exact_match(full_roles, field, value):
    matches = []
    for entry in full_roles:
        items = entry.get(field, [])
        if isinstance(items, list) and value in items:
            matches.append(entry["role"])
    return matches

def find_substring_match(full_roles, field, substring):
    matches = []
    t = substring.lower()
    for entry in full_roles:
        items = entry.get(field, [])
        if isinstance(items, list):
            for item in items:
                if t in item.lower():
                    matches.append(entry["role"])
                    break
    return matches

def main():
    roles = load_roles()
    full_roles = load_full_roles()
    schema = load_schema()
    ec_entries = fetch_enzyme_dat()
    print(f"Loaded {len(roles)} roles from Roles.json")
    if schema:
        print("Loaded PlantSEED schema for field validation")
    if ec_entries:
        print(f"Loaded {len(ec_entries)} entries from Enzyme Commission database")
    print()

    display_name = get_git_username()
    dir_name = sanitize_username(display_name)
    if not dir_name:
        dir_name = "user"
    if os.path.isdir(CURATORS_DIR):
        for d in os.listdir(CURATORS_DIR):
            d_path = os.path.join(CURATORS_DIR, d)
            if os.path.isdir(d_path) and d.lower() == dir_name and d.lower() != "curators":
                dir_name = d
                break
    user_dir = os.path.join(CURATORS_DIR, dir_name)
    print(f"Detected user: {display_name}")
    print(f"GitHub username: {dir_name}")
    print(f"Your files will be saved in: {user_dir}")
    print(f"(This folder is created from your GitHub username so your work stays separate from other curators.)")
    print()
    os.makedirs(user_dir, exist_ok=True)

    target_file = get_target_file(dir_name)
    print()

    result = select_enzyme_combined(roles, ec_entries)
    if result is None:
        print("No enzyme selected. Exiting.")
        sys.exit(1)

    entity, is_new_enzyme = result
    print()

    if not is_new_enzyme:
        check_required_fields(entity, full_roles, schema)

    action = select_action(is_new_enzyme)

    if action == "UPDATE":
        new_name = prompt_required("Enter new enzyme name: ")
        lines = [f"{entity}\tUPDATE\t{new_name}"]

    elif action == "NEW":
        lines = [f"{entity}\tNEW"]

    elif action == "ADD":
        lines = handle_add(entity, full_roles)

    elif action == "REMOVE":
        lines = handle_remove(entity)

    elif action == "RELOCATE":
        lines = handle_relocate(entity)

    elif action == "CHANGE":
        lines = handle_change(entity)

    elif action == "ASSIGN":
        lines = handle_assign(entity)

    if not lines:
        print("No rows generated.")
        sys.exit(1)

    rel_path = os.path.relpath(target_file, os.path.join(BASE_DIR, "..", "..", ".."))
    print("\n" + "=" * 60)
    print(f"{len(lines)} TSV row(s) to append to {rel_path}:")
    for line in lines:
        print(line)
    print("=" * 60)

    with open(target_file, "a") as f:
        for line in lines:
            f.write(line + "\n")
    print(f"Appended {len(lines)} row(s) to {target_file}")

if __name__ == "__main__":
    main()
