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
    if not os.path.exists(ENZYME_DAT_CACHE):
        print("Downloading enzyme.dat from Expasy...")
        try:
            urllib.request.urlretrieve(ENZYME_DAT_URL, ENZYME_DAT_CACHE)
            print("Done.")
        except Exception as e:
            print(f"Warning: could not download enzyme.dat ({e})")
            return []
    entries = []
    with open(ENZYME_DAT_CACHE, encoding="latin-1") as f:
        lines = f.read()
    for block in lines.split("\n//\n"):
        ec_id = ""
        de_lines = []
        for line in block.strip().split("\n"):
            if line.startswith("ID   "):
                ec_id = line[5:].strip()
            elif line.startswith("DE   "):
                de_lines.append(line[5:].strip())
            elif line.startswith("DE   "):
                de_lines.append(line.strip())
        if ec_id and de_lines:
            de_full = " ".join(de_lines)
            de_full = de_full[0].upper() + de_full[1:] if de_full else de_full
            de_full = de_full.rstrip(".")
            entries.append(f"{de_full} (EC {ec_id})")
    return entries

def select_existing_role(roles):
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

    # Entity
    mode = input("New enzyme (from EC database) or existing (from PlantSEED Roles)? (n/e): ").strip().lower()
    if mode in ("e", "existing"):
        entity = select_existing_role(roles)
        if entity is None:
            entity = input("Enter enzyme name manually: ").strip()
    elif mode in ("n", "new"):
        if ec_entries:
            entity = select_new_enzyme(ec_entries)
        else:
            print("EC database not available.")
            entity = input("Enter new enzyme name: ").strip()
    else:
        entity = input("Enter enzyme name: ").strip()

    # Action
    action = prompt_required("Action (ADD/UPDATE): ").upper()
    while action not in ("ADD", "UPDATE"):
        action = input("Enter ADD or UPDATE: ").upper().strip()

    # Data type
    data_type = prompt_required("Data Type (features/publications): ").lower()
    while data_type not in ("features", "publications"):
        data_type = input("Enter features or publications: ").lower().strip()

    # Values
    print("Enter value(s), one per line. Blank line to finish:")
    values = []
    while True:
        v = input().strip()
        if not v:
            break
        values.append(v)
    if not values:
        print("At least one value is required.")
        sys.exit(1)

    # Target file
    default_filename = input("Enter a filename for this curation (e.g. Updates.tsv): ").strip()
    if not default_filename:
        default_filename = "Updates.tsv"
    if not default_filename.endswith(".tsv"):
        default_filename += ".tsv"
    target_file = os.path.join(user_dir, default_filename)

    if os.path.exists(target_file):
        overwrite = input(f"File {target_file} already exists. Append to it? (y/n): ").strip().lower()
        if overwrite != "y":
            new_name = input("Enter a different filename: ").strip()
            if new_name:
                if not new_name.endswith(".tsv"):
                    new_name += ".tsv"
                target_file = os.path.join(user_dir, new_name)

    # Output
    rel_path = os.path.relpath(target_file, os.path.join(BASE_DIR, "..", "..", ".."))
    print("\n" + "=" * 60)
    print(f"{len(values)} TSV row(s) to append to {rel_path}:")
    for v in values:
        line = f"{entity}\t{action}\t{data_type}\t{v}"
        print(line)
    print("=" * 60)

if __name__ == "__main__":
    main()
