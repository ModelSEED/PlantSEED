#!/usr/bin/env python3
"""
Interactive curation tool for PlantSEED.
Detects git username, auto-creates user folder, fuzzy-matches
enzymes from Roles.json or enzyme.dat, and outputs TSV rows.
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
import tempfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROLES_FILE = os.path.join(BASE_DIR, "..", "..", "..", "Data", "PlantSEED_v3", "PlantSEED_Roles.json")
ENZYME_DAT_URL = "https://ftp.expasy.org/databases/enzyme/enzyme.dat"
ENZYME_DAT_CACHE = os.path.join(tempfile.gettempdir(), "plantseed_enzyme.dat")
CURATORS_DIR = os.path.join(BASE_DIR, "Curators")

def get_git_username():
    try:
        return subprocess.run(
            ["git", "config", "user.name"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return input("Could not detect git username. Enter your name: ").strip()

def load_roles():
    with open(os.path.normpath(ROLES_FILE)) as f:
        return [r["role"] for r in json.load(f)]

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

def select_enzyme_combined(roles, ec_entries):
    """Select enzyme with combined PlantSEED and Expasy search in two-column format"""
    print("\n" + "="*70)
    print("ENZYME SEARCH (PlantSEED | Expasy)")
    print("="*70)
    
    while True:
        partial = input("Type enzyme name (at least 5 letters): ").strip()
        if len(partial) < 5:
            print("Please enter at least 5 letters for search.")
            continue
            
        # Find matches in both databases
        plantseed_matches = fuzzy_match(partial, roles)
        expasy_matches = fuzzy_match(partial, ec_entries) if ec_entries else []
        
        if not plantseed_matches and not expasy_matches:
            retry = input("No matches found in either database. Try again? (y/n): ").strip().lower()
            if retry != "y":
                return None
            continue
            
        # Display results in two-column format
        print(f"\n{'PlantSEED Enzymes':<35} | {'Expasy Enzymes':<35}")
        print("-"*70)
        
        max_rows = max(len(plantseed_matches), len(expasy_matches))
        for i in range(max_rows):
            # PlantSEED column (numbered)
            if i < len(plantseed_matches):
                plantseed_entry = f"{i+1}. {plantseed_matches[i]}"
            else:
                plantseed_entry = ""
                
            # Expasy column (lettered)
            if i < len(expasy_matches):
                expasy_entry = f"{chr(97+i)}. {expasy_matches[i]}"  # a, b, c, ...
            else:
                expasy_entry = ""
                
            print(f"{plantseed_entry:<35} | {expasy_entry:<35}")
        
        print("-"*70)
        
        # Get user selection
        selection = input("\nSelect enzyme (number for PlantSEED, letter for Expasy, or 'r' to retry): ").strip().lower()
        
        if selection == 'r':
            continue
            
        # Check if it's a number (PlantSEED selection)
        if selection.isdigit():
            idx = int(selection) - 1
            if 0 <= idx < len(plantseed_matches):
                selected = plantseed_matches[idx]
                print(f"Selected PlantSEED enzyme: {selected}")
                return selected, False  # False indicates not new
            else:
                print("Invalid number selection.")
                
        # Check if it's a single letter (Expasy selection)
        elif len(selection) == 1 and selection.isalpha():
            idx = ord(selection) - 97  # Convert 'a' to 0, 'b' to 1, etc.
            if 0 <= idx < len(expasy_matches):
                selected = expasy_matches[idx]
                print(f"Selected Expasy enzyme: {selected}")
                print("WARNING: This enzyme is not in PlantSEED and will create a new entry.")
                return selected, True   # True indicates it's new
            else:
                print("Invalid letter selection.")
                
        else:
            print("Please enter a number (for PlantSEED) or letter (for Expasy).")

def select_existing_role(roles):
    """Legacy function for backward compatibility"""
    while True:
        partial = input("Type enzyme name (partial OK): ").strip()
        matches = fuzzy_match(partial, roles)
        if not matches:
            retry = input("No matches found. Try again? (y/n): ").strip().lower()
            if retry != "y":
                return None
            continue
        if len(matches) == 1:
            print(f"Selected: {matches[0]}")
            return matches[0]
        print(f"{len(matches)} matches:")
        for i, m in enumerate(matches, 1):
            print(f"  {i}. {m}")
        try:
            idx = int(input("Enter number to select (0 to retry): "))
            if 1 <= idx <= len(matches):
                return matches[idx - 1]
        except ValueError:
            pass

def select_new_enzyme(ec_entries):
    """Legacy function for backward compatibility"""
    print("\nSearching Enzyme Commission database for new enzyme...")
    while True:
        partial = input("Type enzyme name or EC number (partial OK): ").strip()
        matches = fuzzy_match(partial, ec_entries)
        if not matches:
            retry = input("No matches in EC database. Use a custom name? (y/n): ").strip().lower()
            if retry == "y":
                return input("Enter custom enzyme name: ").strip()
            continue
        if len(matches) == 1:
            print(f"Selected: {matches[0]}")
            return matches[0]
        print(f"{len(matches)} matches:")
        for i, m in enumerate(matches[:50], 1):
            print(f"  {i}. {m}")
        if len(matches) > 50:
            print(f"  ... and {len(matches) - 50} more (refine your search)")
        try:
            idx = int(input("Enter number to select (0 to retry, -1 for custom): "))
            if idx == -1:
                return input("Enter custom enzyme name: ").strip()
            if 1 <= idx <= len(matches):
                return matches[idx - 1]
        except ValueError:
            pass

def prompt_required(prompt_text):
    while True:
        val = input(prompt_text).strip()
        if val:
            return val

def get_target_file(username):
    default_filename = input("Enter a filename for this curation (e.g. Updates.tsv): ").strip()
    if not default_filename:
        default_filename = "Updates.tsv"
    if not default_filename.endswith(".tsv"):
        default_filename += ".tsv"
    target_file = os.path.join(CURATORS_DIR, username, default_filename)
    if os.path.exists(target_file):
        overwrite = input(f"File {target_file} already exists. Append to it? (y/n): ").strip().lower()
        if overwrite != "y":
            new_name = input("Enter a different filename: ").strip()
            if new_name:
                if not new_name.endswith(".tsv"):
                    new_name += ".tsv"
                target_file = os.path.join(CURATORS_DIR, username, new_name)
    return target_file

def handle_add(entity):
    field = prompt_required("Enter field (features/publications/reactions/subsystems/curators/localization/classes): ").lower()
    lines = []
    multi_col = (field in ("features", "reactions"))
    if multi_col:
        print(f"Enter {field} value(s), one per line. Blank line to finish.")
        print(f"Format: <value> or <key>\\t<extra>")
        while True:
            v = input().strip()
            if not v:
                break
            parts = v.split("\t")
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
    field = prompt_required("Enter field (features/publications/reactions/subsystems/curators/localization/classes): ").lower()
    print("Enter entry value(s) to remove, one per line. Blank line to finish:")
    lines = []
    while True:
        v = input().strip()
        if not v:
            break
        lines.append(f"{entity}\tREMOVE\t{field}\t{v}")
    return lines

def handle_relocate(entity):
    field = prompt_required("Enter field (localization/compartmentalization): ").lower()
    old_entry = prompt_required("Enter old entry value: ")
    new_entry = prompt_required("Enter new entry value: ")
    return [f"{entity}\tRELOCATE\t{field}\t{old_entry}\t{new_entry}"]

def handle_change(entity):
    field = prompt_required("Enter field (abstract_enzyme/include): ").lower()
    value = prompt_required("Enter new value: ")
    return [f"{entity}\tCHANGE\t{field}\t{value}"]

def handle_assign(entity):
    field = prompt_required("Enter field (include/type): ").lower()
    value = prompt_required("Enter value: ")
    return [f"{entity}\tASSIGN\t{field}\t{value}"]

def main():
    roles = load_roles()
    ec_entries = fetch_enzyme_dat()
    print(f"Loaded {len(roles)} roles from Roles.json")
    if ec_entries:
        print(f"Loaded {len(ec_entries)} entries from Enzyme Commission database")
    print()

    # Detect git username
    username = get_git_username()
    user_dir = os.path.join(CURATORS_DIR, username)
    print(f"Detected user: {username}")
    print(f"Target directory: {user_dir}")
    print()

    # Create user directory
    os.makedirs(user_dir, exist_ok=True)

    # Entity - NEW COMBINED SEARCH
    result = select_enzyme_combined(roles, ec_entries)
    if result is None:
        print("No enzyme selected. Exiting.")
        sys.exit(1)
        
    entity, is_new_enzyme = result

    if is_new_enzyme:
        print("This enzyme will be created as a new entry in PlantSEED.")

    # Action
    action = prompt_required("Action (UPDATE/NEW/ADD/REMOVE/RELOCATE/CHANGE/ASSIGN): ").upper()
    while action not in ("UPDATE", "NEW", "ADD", "REMOVE", "RELOCATE", "CHANGE", "ASSIGN"):
        action = input("Enter UPDATE, NEW, ADD, REMOVE, RELOCATE, CHANGE, or ASSIGN: ").upper().strip()

    # Handle each action with correct TSV format
    if action == "UPDATE":
        new_name = prompt_required("Enter new enzyme name: ")
        lines = [f"{entity}\tUPDATE\t{new_name}"]

    elif action == "NEW":
        lines = [f"{entity}\tNEW"]

    elif action == "ADD":
        lines = handle_add(entity)

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

    # Target file
    target_file = get_target_file(username)

    # Output
    rel_path = os.path.relpath(target_file, os.path.join(BASE_DIR, "..", "..", ".."))
    print("\n" + "=" * 60)
    print(f"{len(lines)} TSV row(s) to append to {rel_path}:")
    for line in lines:
        print(line)
    print("=" * 60)

if __name__ == "__main__":
    main()
