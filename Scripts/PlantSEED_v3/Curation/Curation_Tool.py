#!/usr/bin/env python3
"""PlantSEED Curation Tool — interactive CLI.

Thin wrapper over `plantseed_curation`. The package owns every constant,
helper, and validator; this script only collects curator answers, packages
them into the payload dicts the library expects, and writes the resulting
TSV rows. Both this CLI and Curation_Tool_Dashboard.py route through the
same build_tsv_rows / append_curator_file so they emit byte-identical text.
"""

import os
import sys

# The package sits next to this script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plantseed_curation import (
    ACTION_DESCRIPTIONS,
    ACTION_OPTIONS,
    Console,
    COMPARTMENTS,
    COMPARTMENT_IDS,
    DEFAULT_COMPARTMENT,
    EXIT_SHORTCUT,
    ExitRequested,
    MULTI_COL_FIELDS,
    actions as A,
    append_curator_file,
    confirm_curator_registry,
    curator_dir_path,
    detect_github_username,
    expasy as _expasy,
    find_exact_match,
    find_substring_match,
    fuzzy_match,
    get_git_email,
    get_git_username,
    normalize_existing_dirname,
    required_empty_fields,
    sanitize_filename,
    sanitize_username,
    search_features,
)
from plantseed_curation.store import DataStore


# Action vocabulary surfaced in the menu. NEW is added implicitly when the
# curator picks a novel enzyme name.
CLI_ACTION_MENU = ["ADD", "REASSIGN", "RELOCATE", "REMOVE", "UPDATE"]

EXPASY_DISPLAY_LIMIT = 26   # one letter a..z; keeps selection unambiguous
FEATURE_DISPLAY_LIMIT = 9   # one digit 1..9 after the PlantSEED block


# ============================================================================
# Identity + target file
# ============================================================================
def resolve_curator(console):
    display_name = get_git_username() or console.prompt(
        "Could not detect git username. Enter your name: "
    ).strip()
    info = detect_github_username(display_name)
    detected = info["username"]
    console.print(f"\nDetected GitHub username: {detected}  (source: {info['source']})")
    entered = console.prompt(
        "Press Enter to accept, or type a different GitHub username: "
    ).strip().lower()
    gh_user = sanitize_username(entered or detected) or "user"
    gh_user = normalize_existing_dirname(gh_user)
    confirm_curator_registry(gh_user, display_name, get_git_email())
    return display_name, gh_user


def get_target_file(console, username):
    base = curator_dir_path(username)
    os.makedirs(base, exist_ok=True)
    while True:
        raw = console.prompt("Enter a filename for this curation (default: Updates.tsv): ").strip()
        if not raw:
            raw = "Updates.tsv"
        clean = sanitize_filename(raw)
        if not clean:
            console.print("Filename cannot be empty after sanitization.")
            continue
        if not clean.endswith(".tsv"):
            clean += ".tsv"
        target_file = os.path.join(base, clean)
        console.print(f"Target file: {os.path.abspath(target_file)}")
        if os.path.exists(target_file):
            console.print("This file already exists. New rows will be APPENDED to the end.")
            if console.prompt(
                "Continue with this file? (y to append / n to choose a different filename): "
            ).strip().lower() == "y":
                return target_file
        else:
            if console.prompt(
                "This file does not exist yet and will be created. Confirm? (y/n): "
            ).strip().lower() == "y":
                return target_file
        console.print("Enter a different filename.")


# ============================================================================
# Enzyme selection
# ============================================================================
def print_compartments(console):
    console.print("\n  Compartments:")
    pairs = [f"{cid}={name}" for cid, name in COMPARTMENTS]
    width = max(len(p) for p in pairs) + 4
    for i in range(0, len(pairs), 2):
        console.print("    " + "".join(p.ljust(width) for p in pairs[i:i + 2]))
    console.print()


def select_enzyme(console, store, ec_labels):
    """Combined PlantSEED / Expasy / by-feature search. Returns
    (enzyme_name, is_new_enzyme)."""
    roles = [r["role"] for r in store.roles]
    console.print("\n" + "=" * 70)
    console.print("ENZYME SEARCH  (PlantSEED name + Expasy + by-feature substring)")
    console.print("=" * 70)
    console.print("Tip: type a gene id (e.g. AT3G30775) to find roles that already carry it.")
    while True:
        partial = console.prompt(
            "Type 3+ chars (enzyme name OR gene/feature substring): "
        ).strip()
        if len(partial) < 3:
            console.print("Please enter at least 3 characters.")
            continue
        plantseed_matches = fuzzy_match(partial, roles)
        expasy_all = fuzzy_match(partial, ec_labels) if ec_labels else []
        expasy_matches = expasy_all[:EXPASY_DISPLAY_LIMIT]
        feature_all = search_features(store.roles, partial.lower(), exclude_roles=set())
        feature_matches = [
            (r, f) for r, f in feature_all if r not in plantseed_matches
        ][:FEATURE_DISPLAY_LIMIT]

        if not plantseed_matches and not expasy_matches and not feature_matches:
            retry = console.prompt("No matches. (r)etry, (n)ovel enzyme: ").strip().lower()
            if retry == "n":
                name = console.prompt("Enter full name for the new enzyme: ").strip()
                if name:
                    return name, True
            continue

        if plantseed_matches:
            console.print("\nPlantSEED enzymes (by name):")
            console.print("-" * 60)
            for i, match in enumerate(plantseed_matches):
                console.print(f"  {i+1:>2} | {match}")
        if expasy_matches:
            console.print("\nExpasy enzymes:")
            console.print("-" * 60)
            for i, match in enumerate(expasy_matches):
                console.print(f"  {chr(97+i):>2} | {match}")
            if len(expasy_all) > EXPASY_DISPLAY_LIMIT:
                console.print(
                    f"     +{len(expasy_all) - EXPASY_DISPLAY_LIMIT} more Expasy matches (refine)."
                )
        if feature_matches:
            console.print("\nRoles carrying a feature matching your query:")
            console.print("-" * 60)
            for i, (role, feat) in enumerate(feature_matches):
                console.print(f"  f{i+1} | {role}")
                console.print(f"       └── feature: {feat}")
            if len(feature_all) > FEATURE_DISPLAY_LIMIT:
                console.print(
                    f"     +{len(feature_all) - FEATURE_DISPLAY_LIMIT} more by-feature matches (refine)."
                )

        console.print("-" * 60)
        selection = console.prompt(
            "Select (#, letter, f# for by-feature, (r)etry, (n)ovel): "
        ).strip().lower()
        if selection == "r":
            continue
        if selection == "n":
            name = console.prompt("Enter full name for the new enzyme: ").strip()
            if name:
                return name, True
            continue
        if selection.startswith("f") and selection[1:].isdigit():
            idx = int(selection[1:]) - 1
            if 0 <= idx < len(feature_matches):
                selected = feature_matches[idx][0]
                console.print(f"Selected (by-feature): {selected}")
                return selected, False
            console.print("Invalid by-feature selection.")
            continue
        if selection.isdigit():
            idx = int(selection) - 1
            if 0 <= idx < len(plantseed_matches):
                selected = plantseed_matches[idx]
                console.print(f"Selected PlantSEED enzyme: {selected}")
                return selected, False
            console.print("Invalid number selection.")
        elif len(selection) == 1 and selection.isalpha():
            idx = ord(selection) - 97
            if 0 <= idx < len(expasy_matches):
                selected = expasy_matches[idx]
                already_in_plantseed = selected in plantseed_matches
                console.print(f"Selected Expasy enzyme: {selected}")
                if already_in_plantseed:
                    console.print("(This enzyme is already in PlantSEED.)")
                    return selected, False
                console.print("WARNING: not in PlantSEED — will create a new entry.")
                return selected, True
            console.print("Invalid letter selection.")
        else:
            console.print(
                "Use a number (PlantSEED), letter (Expasy), f# (by-feature), r, or n."
            )


# ============================================================================
# Action handlers — each returns a payload dict ready for build_tsv_rows
# ============================================================================
def select_action(console, is_new_enzyme):
    if is_new_enzyme:
        console.print("New enzyme detected. Action automatically set to NEW.")
        return "NEW"
    console.print()
    for i, opt in enumerate(CLI_ACTION_MENU, 1):
        desc = ACTION_DESCRIPTIONS.get(opt, "")
        console.print(f"  {i}. {opt:9s} ({desc})")
    while True:
        raw = console.prompt("Select action: ").strip()
        try:
            idx = int(raw) - 1
        except ValueError:
            console.print(f"Enter a number between 1 and {len(CLI_ACTION_MENU)}.")
            continue
        if 0 <= idx < len(CLI_ACTION_MENU):
            return CLI_ACTION_MENU[idx]
        console.print(f"Enter a number between 1 and {len(CLI_ACTION_MENU)}.")


def _print_cross_ref(console, value, matches, label):
    if not matches:
        return
    display = matches[:5]
    rest = len(matches) - 5
    msg = f"  Note: '{value}' {label}: {', '.join(display)}"
    if rest > 0:
        msg += f" (+{rest} more)"
    console.print(msg)


def _select_from(console, label, options):
    """List 1..N, return chosen option string."""
    console.print()
    for i, opt in enumerate(options, 1):
        console.print(f"  {i}. {opt}")
    while True:
        raw = console.prompt(f"{label} ").strip()
        try:
            idx = int(raw) - 1
        except ValueError:
            console.print(f"Enter a number between 1 and {len(options)}.")
            continue
        if 0 <= idx < len(options):
            return options[idx]
        console.print(f"Enter a number between 1 and {len(options)}.")


def collect_payload(console, store, entity, action):
    """Walk the curator through the action-specific prompts and return a
    payload dict matching the shape build_tsv_rows expects."""
    from plantseed_curation.constants import ACTION_FIELDS

    if action == "NEW":
        return {}
    if action == "UPDATE":
        return {"new_name": console.prompt_required("Enter new enzyme name: ")}

    fields = ACTION_FIELDS.get(action, [])
    field = _select_from(console, "Select field:", fields)

    if action == "ADD":
        cfg = MULTI_COL_FIELDS.get(field)
        if field in ("features", "reactions"):
            print_compartments(console)
        entries = []
        primary_label = cfg["primary_label"] if cfg else f"{field[:-1]} value"
        extra_label = cfg["extra_label"] if cfg else None
        console.print(
            f"\nAdding {field}. Enter a blank value when prompted to finish."
        )
        while True:
            value = console.prompt(f"Enter {primary_label}: ").strip()
            if not value:
                break
            extra = ""
            if cfg:
                extra = console.prompt(f"Enter {extra_label}: ").strip()
                if not extra and not cfg.get("extra_optional", True):
                    console.print(
                        f"  Warning: extra is required for {field}; skipping this entry."
                    )
                    continue
            if field == "reactions":
                xrefs = find_exact_match(store.roles, "reactions", value, exclude=entity)
                _print_cross_ref(
                    console, value, xrefs, "is already used by other role(s)"
                )
            elif field == "features":
                xrefs = find_substring_match(store.roles, "features", value, exclude=entity)
                _print_cross_ref(
                    console, value, xrefs, "matches features in other role(s)"
                )
            elif field == "publications":
                xrefs = find_exact_match(store.roles, "publications", value, exclude=entity)
                _print_cross_ref(
                    console, value, xrefs, "is already cited by other role(s)"
                )
            entries.append({"value": value, "extra": extra})
        return {"field": field, "entries": entries}

    if action == "REMOVE":
        entries = []
        console.print(f"\nRemoving {field}. Enter blank value to finish.")
        while True:
            value = console.prompt(f"Enter {field[:-1]} value to remove: ").strip()
            if not value:
                break
            entries.append({"value": value})
        return {"field": field, "entries": entries}

    if action == "RELOCATE":
        old = console.prompt_required("Enter old entry value: ")
        new = console.prompt_required("Enter new entry value: ")
        return {"field": field, "old": old, "new": new}

    if action == "REASSIGN":
        value = console.prompt_required("Enter new value: ")
        return {"field": field, "value": value}

    return {"field": field}


def check_required_fields(console, entity_name, store):
    if not store.schema_normalized:
        return
    entry = store.role_index.get(entity_name)
    if entry is None:
        return
    empties = required_empty_fields(entry, store.schema_normalized)
    if not empties:
        return
    console.print()
    console.print(
        "NOTE: This enzyme has some required fields that are empty or need attention:"
    )
    for e in empties:
        console.print(f"  - '{e}' is empty")
    console.print("You can use the ADD action to populate these fields later.")
    console.prompt("Press Enter to skip and continue...")


def append_rows(console, target_file, username, lines, base_dir):
    if not lines:
        return 0
    rel = os.path.relpath(target_file, base_dir)
    console.print("\n" + "=" * 60)
    console.print(f"{len(lines)} TSV row(s) to append to {rel}:")
    for line in lines:
        console.print(line)
    console.print("=" * 60)
    fp, n = append_curator_file(
        username, os.path.basename(target_file), lines
    )
    console.print(f"Appended {n} row(s) to {fp}")
    return n


# ============================================================================
# Main loop
# ============================================================================
def run(console=None, store=None, skip_expasy=False):
    """Entry point that's reusable from tests. Tests pass a console with a
    scripted input_fn and a DataStore pre-populated with a fixture roles
    list — they should NOT touch the real PlantSEED_Roles.json."""
    if console is None:
        console = Console()
    if store is None:
        store = DataStore()
        store.load_roles()
        store.load_schema()

    if not skip_expasy and not store.ec_entries:
        # Run the fetch synchronously here so the labels are ready by the
        # time the first prompt appears; gracefully fall back if offline.
        try:
            store.set_expasy_entries(_expasy.fetch_enzyme_dat())
        except Exception as e:
            console.print(f"Warning: could not load Expasy enzyme.dat ({e})")

    ec_labels = [e["label"] for e in store.ec_entries]

    console.print(f"Loaded {len(store.roles)} roles from PlantSEED_Roles.json")
    if store.schema_normalized:
        console.print("Loaded PlantSEED schema for field validation")
    if ec_labels:
        console.print(f"Loaded {len(ec_labels)} entries from Enzyme Commission database")
    console.print()
    console.print(f"Tip: type '{EXIT_SHORTCUT}' at any prompt to exit cleanly.")
    console.print()

    display_name, username = resolve_curator(console)
    user_dir = curator_dir_path(username)
    console.print(f"Detected user: {display_name}")
    console.print(f"GitHub username: {username}")
    console.print(f"Your files will be saved in: {user_dir}")
    console.print()
    target_file = get_target_file(console, username)
    console.print()

    # base_dir used for the relative-path log line; falls back to the curator dir.
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(user_dir)))

    total_actions = 0
    while True:
        result = select_enzyme(console, store, ec_labels)
        if result is None:
            console.print("No enzyme selected.")
            break
        entity, is_new_enzyme = result
        console.print()
        if not is_new_enzyme:
            check_required_fields(console, entity, store)

        while True:
            console.print(f"\n--- Working on enzyme: {entity} ---")
            action = select_action(console, is_new_enzyme)
            payload = collect_payload(console, store, entity, action)
            rows, errors, warnings = A.build_tsv_rows(action, entity, payload, store)
            for w in warnings:
                console.print(f"  [WARN] {w}")
            if errors:
                for e in errors:
                    console.print(f"  [ERROR] {e['field']}: {e['message']}")
                console.print("No rows generated for this action.")
            else:
                appended = append_rows(console, target_file, username, rows, base_dir)
                if appended:
                    total_actions += 1
            is_new_enzyme = False
            next_step = _select_from(console, "What next?", [
                f"Another action on '{entity[:50] + ('...' if len(entity) > 50 else '')}'",
                "Switch to a different enzyme",
                "Done — exit",
            ])
            if next_step.startswith("Switch"):
                break
            if next_step.startswith("Done"):
                if total_actions == 0:
                    console.print("No actions recorded.")
                    return 1
                console.print(f"\nDone. Recorded {total_actions} action(s) into {target_file}")
                return 0

    if total_actions == 0:
        console.print("No actions recorded.")
        return 1
    console.print(f"\nDone. Recorded {total_actions} action(s) into {target_file}")
    return 0


def main():
    try:
        rc = run()
    except ExitRequested:
        rc = 0
    sys.exit(rc)


if __name__ == "__main__":
    main()
