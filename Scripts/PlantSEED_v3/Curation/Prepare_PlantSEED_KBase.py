#!/usr/bin/env python
"""Assign KBase IDs to every role and complex in the PlantSEED database.

Thin driver around plantseed_curation. All schema/IO/hashing logic lives in
the shared library; this script is a two-stage pipeline:

  1. Roles pass: for each role missing a `kbase_id`, mint one via
     `assign_kbase_id` (uses role + reactions[0] + subsystems[0] for the hash).

  2. Complexes pass: verify every existing complex's `kbase_id` still matches
     what its enzyme/roles/reactions imply (via `assign_complex_kbase_id`),
     then walk the roles JSON for any `abstract_enzyme` that isn't yet
     represented in PlantSEED_Complexes.json and append a new complex entry
     (via `derive_new_complexes`).

Warnings/logs are collected in an `IssueCollector` and printed at the end so
the run reads as a summary rather than interleaved output.
"""

import json

from plantseed_curation import (
    assign_complex_kbase_id,
    assign_kbase_id,
    derive_new_complexes,
    enzyme_index_from_complexes,
    paths,
    validate_subcomplex_pointers,
)
from plantseed_curation.schema import IssueCollector


def _load_json(path):
    with open(path) as fh:
        return json.load(fh)


def _dump_json(path, data):
    with open(path, "w") as fh:
        json.dump(data, fh, indent=4)


def prepare_roles(roles_list, issues):
    """Assign a PS_role_* id to every role that lacks one. Returns True if
    the roles list was modified."""
    existing_ids = {r["kbase_id"] for r in roles_list if "kbase_id" in r}
    changed = False
    for role in roles_list:
        if "kbase_id" in role:
            continue
        if assign_kbase_id(role, existing_ids, issues=issues):
            changed = True
    return changed


def prepare_complexes(complexes_list, roles_list, issues):
    """Verify every existing complex's id and derive a new complex entry for
    each role whose abstract_enzyme isn't yet represented. Also validate that
    every role's `subcomplex_of` (if set) points at a complex kbase_id we
    actually have on hand. Returns True if the complexes list was modified
    (existing id updated OR new entry appended)."""
    existing_ids = {c["kbase_id"] for c in complexes_list if "kbase_id" in c}
    changed = False
    for entry in complexes_list:
        if assign_complex_kbase_id(entry, existing_ids, issues=issues):
            changed = True
    enzyme_index = enzyme_index_from_complexes(complexes_list, issues=issues)
    new_entries = derive_new_complexes(
        roles_list, enzyme_index, existing_ids, issues=issues
    )
    if new_entries:
        complexes_list.extend(new_entries)
        changed = True
    # Validate AFTER new complexes are minted so a role legitimately pointing
    # at a fresh parent doesn't warn.
    all_complex_ids = {c["kbase_id"] for c in complexes_list if "kbase_id" in c}
    validate_subcomplex_pointers(roles_list, all_complex_ids, issues=issues)
    return changed


def _print_issues(issues):
    for e in issues.errors:
        print(f"ERROR: {e}")
    for w in issues.warnings:
        print(f"WARNING: {w}")
    for i in issues.info:
        print(f"INFO: {i}")


def main():
    issues = IssueCollector()

    print("+" * 30)
    print("++ Checking KBase Role IDs")
    roles_list = _load_json(paths.ROLES_FILE)
    roles_changed = prepare_roles(roles_list, issues)

    print("+" * 30)
    print("++ Checking KBase Complex IDs")
    complexes_list = _load_json(paths.COMPLEXES_FILE)
    complexes_changed = prepare_complexes(complexes_list, roles_list, issues)

    print("+" * 30)

    if roles_changed:
        _dump_json(paths.ROLES_FILE, roles_list)
        print(f"WROTE: {paths.ROLES_FILE}")
    if complexes_changed:
        _dump_json(paths.COMPLEXES_FILE, complexes_list)
        print(f"WROTE: {paths.COMPLEXES_FILE}")

    _print_issues(issues)


if __name__ == "__main__":
    main()
