#!/usr/bin/env python3
"""
Interactive curation tool for PlantSEED.
Generates a TSV line formatted for the curation workflow.
"""

import json
import os
import sys

ROLES_FILE = os.path.join(os.path.dirname(__file__),
    "..", "..", "Data", "PlantSEED_v3", "PlantSEED_Roles.json")

def load_roles():
    with open(os.path.normpath(ROLES_FILE)) as f:
        return [r["role"] for r in json.load(f)]

def fuzzy_match(term, choices):
    term = term.lower()
    return [c for c in choices if term in c.lower()]

def select_role(roles):
    while True:
        mode = input("New enzyme or existing? (n/e): ").strip().lower()
        if mode in ("e", "existing"):
            break
        elif mode in ("n", "new"):
            return input("Enter new enzyme name: ").strip()
        print("Enter 'n' for new or 'e' for existing.")

    while True:
        partial = input("Type enzyme name (partial OK): ").strip()
        matches = fuzzy_match(partial, roles)
        if not matches:
            retry = input("No matches found. Enter a new name instead? (y/n): ").strip().lower()
            if retry == "y":
                return input("Enter new enzyme name: ").strip()
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

def prompt_required(prompt_text):
    while True:
        val = input(prompt_text).strip()
        if val:
            return val

def main():
    roles = load_roles()
    print(f"Loaded {len(roles)} roles from PlantSEED_Roles.json\n")

    entity = select_role(roles)
    action = prompt_required("Action (ADD/UPDATE): ").upper()
    while action not in ("ADD", "UPDATE"):
        action = input("Enter ADD or UPDATE: ").upper().strip()

    data_type = prompt_required("Data Type (features/publications): ").lower()
    while data_type not in ("features", "publications"):
        data_type = input("Enter features or publications: ").lower().strip()

    value = prompt_required("Value: ")
    target = prompt_required("Target file path (e.g. Scripts/PlantSEED_v3/Curation/<user>/<path>/<file>.tsv): ")

    line = f"{entity}\t{action}\t{data_type}\t{value}"
    print("\n" + "=" * 60)
    print("TSV line to append:")
    print(line)
    print(f"\nTarget file: {target}")
    print("=" * 60)

if __name__ == "__main__":
    main()
