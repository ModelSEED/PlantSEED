"""TSV row construction, validation, parsing, and the apply pipeline.

This module is the canonical home of every action the CLI and dashboard
share. Both interfaces collect a payload dict and call build_tsv_rows; the
dashboard additionally calls run_apply / preview_for_enzyme to mutate the
roles JSON in-process.
"""

import copy
import hashlib
import json
import os

from . import paths
from .constants import (
    ACTION_FIELDS,
    ACTION_MIN_COLS,
    ACTION_OPTIONS,
    BOOL_FALSE,
    BOOL_TRUE,
    COMPARTMENT_IDS,
    DEFAULT_COMPARTMENT,
    DEFAULT_LOC_SOURCE,
    DEPRECATED_REASSIGN_ALIASES,
    MULTI_COL_FIELDS,
    SCALAR_TYPES,
    TYPE_MAP,
    coerce_bool_str,
)


def _canonical_action(action):
    """Map deprecated verbs onto their canonical replacements. Keeps
    validate_payload / build_tsv_rows callers happy whether they pass
    REASSIGN, ASSIGN, or CHANGE."""
    a = (action or "").upper()
    if a in DEPRECATED_REASSIGN_ALIASES:
        return "REASSIGN"
    return a
from .identity import atomic_write
from .schema import (
    IssueCollector,
    default_role_from_schema,
    ensure_schema_defaults,
    validate_dependencies,
)


# ----------------------------------------------------------------------------
# Validation + TSV row construction
# ----------------------------------------------------------------------------
def validate_payload(action, enzyme, payload, store):
    """Return (errors, warnings). Errors are dicts with {field, message};
    warnings are plain strings."""
    errors, warnings = [], []
    if not enzyme or not enzyme.strip():
        return [{"field": "enzyme", "message": "Enzyme name is required"}], warnings
    raw_action = action.upper()
    # Canonicalise deprecated verbs so the rest of validate_payload only has
    # to know about REASSIGN. Warn the caller so the curator sees the deprecation.
    action = _canonical_action(raw_action)
    if raw_action in DEPRECATED_REASSIGN_ALIASES:
        warnings.append(
            f"action '{raw_action}' is deprecated — use 'REASSIGN' instead "
            f"(behaviour is unchanged)"
        )
    if action not in ACTION_OPTIONS:
        return [{"field": "action", "message": f"Unknown action '{raw_action}'"}], warnings

    if action == "NEW":
        if enzyme in store.role_index:
            errors.append({"field": "enzyme",
                "message": f"'{enzyme}' already exists — choose UPDATE or pick a different name"})
        return errors, warnings

    if action == "UPDATE":
        new_name = (payload.get("new_name") or "").strip()
        if not new_name:
            errors.append({"field": "new_name", "message": "New enzyme name is required"})
        elif new_name == enzyme:
            warnings.append("UPDATE: new name is identical to current name")
        elif new_name in store.role_index:
            errors.append({"field": "new_name",
                "message": f"'{new_name}' already exists in the database"})
        if enzyme not in store.role_index:
            warnings.append(
                f"UPDATE: '{enzyme}' is not in the current database — the row will be skipped on apply"
            )
        return errors, warnings

    field = (payload.get("field") or "").strip()
    if not field:
        return [{"field": "field", "message": "Field is required"}], warnings
    if action in ACTION_FIELDS and field not in ACTION_FIELDS[action]:
        return [{"field": "field",
            "message": f"{action} field '{field}' is not valid (allowed: {', '.join(ACTION_FIELDS[action])})"}], warnings

    role_entry = store.role_index.get(enzyme)

    if action == "ADD":
        entries = payload.get("entries") or []
        if not entries:
            errors.append({"field": "entries", "message": "At least one entry is required"})
        for i, entry in enumerate(entries):
            value = (entry.get("value") or "").strip()
            extra = (entry.get("extra") or "").strip()
            if not value:
                errors.append({"field": f"entries[{i}].value", "message": "Empty entry"})
                continue
            cfg = MULTI_COL_FIELDS.get(field)
            if cfg:
                if not extra:
                    if not cfg.get("extra_optional", True):
                        errors.append({"field": f"entries[{i}].extra",
                            "message": f"Extra is required ({cfg['extra_label']})"})
                    elif cfg["extra_kind"] in ("compartment_source", "compartment_only"):
                        warnings.append(
                            f"ADD {field} '{value}': no localization given — compartment "
                            f"will be assumed '{DEFAULT_COMPARTMENT}' (cytosol) on apply"
                        )
                elif cfg["extra_kind"] == "compartment_source":
                    if ":" not in extra:
                        errors.append({"field": f"entries[{i}].extra",
                            "message": f"Expected 'compartment:source' (e.g. c:PPDB). Got '{extra}'"})
                    else:
                        cpt = extra.split(":", 1)[0]
                        if cpt not in COMPARTMENT_IDS:
                            errors.append({"field": f"entries[{i}].extra",
                                "message": f"'{cpt}' is not a known ModelSEED plant compartment"})
                elif cfg["extra_kind"] == "compartment_only":
                    if extra not in COMPARTMENT_IDS:
                        errors.append({"field": f"entries[{i}].extra",
                            "message": f"'{extra}' is not a known compartment letter"})
            if role_entry:
                existing = role_entry.get(field, [])
                if isinstance(existing, list) and value in existing:
                    warnings.append(f"ADD {field}: '{value}' is already on this role (will be a no-op)")
                elif isinstance(existing, dict) and value in existing:
                    warnings.append(f"ADD {field}: '{value}' is already on this role (will be a no-op)")
        return errors, warnings

    if action == "REMOVE":
        entries = payload.get("entries") or []
        if not entries:
            errors.append({"field": "entries", "message": "At least one entry is required"})
        for i, entry in enumerate(entries):
            value = (entry.get("value") or "").strip()
            if not value:
                errors.append({"field": f"entries[{i}].value", "message": "Empty entry"})
                continue
            if role_entry:
                existing = role_entry.get(field, [])
                present = (isinstance(existing, list) and value in existing) or \
                          (isinstance(existing, dict) and value in existing)
                if not present:
                    warnings.append(f"REMOVE {field}: '{value}' is not currently on this role")
        return errors, warnings

    if action == "RELOCATE":
        old = (payload.get("old") or "").strip()
        new = (payload.get("new") or "").strip()
        if not old:
            errors.append({"field": "old", "message": "Old key is required"})
        if not new:
            errors.append({"field": "new", "message": "New key is required"})
        if old and new and old == new:
            errors.append({"field": "new", "message": "Old and new keys are identical"})
        if role_entry and old:
            existing = role_entry.get(field, {})
            if isinstance(existing, dict) and old not in existing:
                warnings.append(f"RELOCATE {field}: '{old}' is not currently a key in this role")
        return errors, warnings

    if action == "REASSIGN":
        value = (payload.get("value") or "").strip()
        if not value:
            return [{"field": "value", "message": "Value is required"}], warnings
        if SCALAR_TYPES.get(field) == "bool":
            if coerce_bool_str(value) is None:
                errors.append({"field": "value",
                    "message": f"'{field}' must be a boolean (true/false/yes/no)"})
        return errors, warnings

    return errors, warnings


def build_tsv_rows(action, enzyme, payload, store):
    """Validate then render the canonical TSV row strings. Both interfaces
    funnel through here so they emit byte-identical text."""
    errors_struct, warnings = validate_payload(action, enzyme, payload, store)
    if errors_struct:
        return [], errors_struct, warnings
    rows = []
    # Always emit the canonical verb (REASSIGN) regardless of the alias
    # the caller used; deprecation warning is surfaced via validate_payload.
    action = _canonical_action(action)
    if action == "NEW":
        rows.append(f"{enzyme}\tNEW")
    elif action == "UPDATE":
        rows.append(f"{enzyme}\tUPDATE\t{(payload['new_name'] or '').strip()}")
    elif action == "ADD":
        field = payload["field"]
        for entry in payload["entries"]:
            value = (entry.get("value") or "").strip()
            extra = (entry.get("extra") or "").strip()
            if extra:
                rows.append(f"{enzyme}\tADD\t{field}\t{value}\t{extra}")
            else:
                rows.append(f"{enzyme}\tADD\t{field}\t{value}")
    elif action == "REMOVE":
        field = payload["field"]
        for entry in payload["entries"]:
            value = (entry.get("value") or "").strip()
            rows.append(f"{enzyme}\tREMOVE\t{field}\t{value}")
    elif action == "RELOCATE":
        field = payload["field"]
        rows.append(f"{enzyme}\tRELOCATE\t{field}\t{payload['old'].strip()}\t{payload['new'].strip()}")
    elif action == "REASSIGN":
        field = payload["field"]
        value = (payload["value"] or "").strip()
        if SCALAR_TYPES.get(field) == "bool":
            coerced = coerce_bool_str(value)
            if coerced is not None:
                value = coerced
        rows.append(f"{enzyme}\tREASSIGN\t{field}\t{value}")
    return rows, [], warnings


# ----------------------------------------------------------------------------
# TSV parsing
# ----------------------------------------------------------------------------
def parse_tsv_text(text, schema=None, issues=None):
    """Bucket TSV lines by action. Non-restrictive: bad lines are warned
    and skipped, good lines are parsed. ASSIGN/CHANGE are accepted as
    deprecated aliases of REASSIGN; a single end-of-parse warning per
    alias actually used is emitted so curators see a clear nudge."""
    actions = {"replace": {}, "new": [], "add": {}, "rem": {}, "key": {},
               "reassign": {}}
    deprecated_alias_counts = {name: 0 for name in DEPRECATED_REASSIGN_ALIASES}

    def _check_field(field, lineno):
        if schema is not None and field not in schema and issues is not None:
            issues.warn(f"line {lineno}: field '{field}' is not in the schema — proceeding anyway")

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip("\r\n")
        if line.startswith("#") or not line.strip():
            continue
        tmp_lst = line.split("\t")
        if len(tmp_lst) < 2:
            if issues is not None:
                hint = " — looks space-separated; columns must be TAB-separated" \
                    if len(line.split()) > 1 else ""
                issues.warn(f"line {lineno}: fewer than 2 columns{hint} — skipped")
            continue
        enzyme = tmp_lst[0]
        action = tmp_lst[1].upper()
        if action not in ACTION_MIN_COLS:
            if issues is not None:
                issues.warn(f"line {lineno}: unknown action '{tmp_lst[1]}' — skipped")
            continue
        if len(tmp_lst) < ACTION_MIN_COLS[action]:
            if issues is not None:
                issues.warn(f"line {lineno}: action {action} requires at least "
                            f"{ACTION_MIN_COLS[action]} columns, got {len(tmp_lst)} — skipped")
            continue
        if action == "UPDATE":
            actions["replace"][enzyme] = tmp_lst[2]
        elif action == "NEW":
            actions["new"].append(enzyme)
            if issues is not None:
                issues.log(f"NEW enzyme queued: {enzyme}")
        elif action == "ADD":
            field, entry = tmp_lst[2], tmp_lst[3]
            _check_field(field, lineno)
            actions["add"].setdefault(enzyme, {}).setdefault(field, {})
            actions["add"][enzyme][field][entry] = 1
            if len(tmp_lst) > 4:
                actions["add"][enzyme][field][tmp_lst[3]] = tmp_lst[4]
        elif action == "REMOVE":
            field, entry = tmp_lst[2], tmp_lst[3]
            _check_field(field, lineno)
            actions["rem"].setdefault(enzyme, {}).setdefault(field, []).append(entry)
        elif action == "RELOCATE":
            field, entry, new_entry = tmp_lst[2], tmp_lst[3], tmp_lst[4]
            _check_field(field, lineno)
            actions["key"].setdefault(enzyme, {}).setdefault(field, {})[entry] = new_entry
        elif action == "REASSIGN" or action in DEPRECATED_REASSIGN_ALIASES:
            field, entry = tmp_lst[2], tmp_lst[3]
            _check_field(field, lineno)
            actions["reassign"].setdefault(enzyme, {})[field] = entry
            if action in DEPRECATED_REASSIGN_ALIASES:
                deprecated_alias_counts[action] += 1

    if issues is not None:
        for old_name in DEPRECATED_REASSIGN_ALIASES:
            count = deprecated_alias_counts[old_name]
            if count:
                issues.warn(
                    f"action '{old_name}' is deprecated — please use 'REASSIGN' instead "
                    f"({count} occurrence(s) in this file; behaviour is unchanged)"
                )
    return actions


# ----------------------------------------------------------------------------
# Apply pipeline
# ----------------------------------------------------------------------------
def seed_new_entries(roles_list, new_list, schema, actions=None, issues=None):
    existing = {entry["role"] for entry in roles_list}
    collisions = [new for new in new_list if new in existing]
    if collisions:
        for c in collisions:
            if issues is not None:
                issues.error(f"NEW role already present in database: '{c}'")
        return False
    for new in new_list:
        new_role = default_role_from_schema(schema)
        new_role["role"] = new
        new_role["abstract_enzyme"] = new.split(" (EC")[0]
        explicit_abstract = actions is not None and (
            "abstract_enzyme" in actions.get("reassign", {}).get(new, {})
        )
        if not explicit_abstract and issues is not None:
            issues.warn(
                f"NEW role '{new}': abstract_enzyme not provided — defaulting to "
                f"'{new_role['abstract_enzyme']}'. Set it explicitly with ASSIGN if a different value is wanted."
            )
        roles_list.append(new_role)
    return True


def _empty_for_field(field, schema):
    """Bug fix #2: respect the schema-declared type when initialising a field
    that ADD touches for the first time. The old code unconditionally set it
    to `[]`, which broke dict-typed fields like `localization`."""
    rules = (schema or {}).get(field)
    if rules and rules.get("type") is dict:
        return {}
    return []


def apply_actions(roles_list, actions, curator, issues=None, schema=None):
    """Apply parsed actions to roles_list in place.
    Returns (touched_role_names, rename_map old->new)."""
    replace_dict  = actions["replace"]
    add_dict      = actions["add"]
    rem_dict      = actions["rem"]
    key_dict      = actions["key"]
    reassign_dict = actions["reassign"]
    touched, rename_map = set(), {}

    def coerce_value(field, val):
        if SCALAR_TYPES.get(field) == "bool":
            s = str(val).strip().lower()
            if s in BOOL_TRUE:
                return True
            if s in BOOL_FALSE:
                return False
        return val

    for entry in roles_list:
        updated_role = False

        if entry["role"] in replace_dict:
            old_name = entry["role"]
            entry["role"] = replace_dict[old_name]
            rename_map[old_name] = entry["role"]
            updated_role = True

        if entry["role"] in add_dict:
            for field in add_dict[entry["role"]]:
                if field not in entry:
                    entry[field] = _empty_for_field(field, schema)
                for input_value in add_dict[entry["role"]][field]:
                    if isinstance(entry[field], list) and input_value not in entry[field]:
                        entry[field].append(input_value)

                    if field == "features":
                        raw = add_dict[entry["role"]][field][input_value]
                        if raw == 1:
                            cpt, code = DEFAULT_COMPARTMENT, DEFAULT_LOC_SOURCE
                            if issues is not None:
                                issues.warn(
                                    f"feature '{input_value}' on '{entry['role']}': "
                                    f"no localization — defaulted to '{cpt}:{code}'"
                                )
                            entry.setdefault("localization", {})
                            if cpt in entry["localization"]:
                                entry["localization"][cpt][input_value] = [code]
                            else:
                                entry["localization"][cpt] = {input_value: [code]}
                        elif ":" not in str(raw):
                            if issues is not None:
                                issues.warn(
                                    f"feature '{input_value}' for role '{entry['role']}': "
                                    f"localization '{raw}' missing ':' (expected 'compartment:source-code')"
                                )
                        else:
                            cpt, code = str(raw).split(":", 1)
                            entry.setdefault("localization", {})
                            if cpt in entry["localization"]:
                                entry["localization"][cpt][input_value] = [code]
                            else:
                                entry["localization"][cpt] = {input_value: [code]}

                    if field == "subsystems":
                        sys_cls = add_dict[entry["role"]][field][input_value]
                        if sys_cls != 1:
                            entry.setdefault("classes", {})
                            entry["classes"].setdefault(sys_cls, {})[input_value] = []

                    if field == "reactions":
                        v = add_dict[entry["role"]][field][input_value]
                        if v == 1:
                            cpt = DEFAULT_COMPARTMENT
                            if issues is not None:
                                issues.warn(
                                    f"reaction '{input_value}' on '{entry['role']}': "
                                    f"no compartment — defaulted to '{cpt}'"
                                )
                        else:
                            cpt = v
                        entry.setdefault("localization", {}).setdefault(cpt, {})[input_value] = [
                            "Assumed"
                        ]
            updated_role = True

        if entry["role"] in reassign_dict:
            for field, val in reassign_dict[entry["role"]].items():
                entry[field] = coerce_value(field, val)
            updated_role = True

        if entry["role"] in key_dict:
            for field in key_dict[entry["role"]]:
                for old_entry in key_dict[entry["role"]][field]:
                    new_entry = key_dict[entry["role"]][field][old_entry]
                    if old_entry not in entry.get(field, {}):
                        if issues is not None:
                            issues.warn(
                                f"RELOCATE on '{entry['role']}': old entry '{old_entry}' "
                                f"not found in field '{field}'"
                            )
                        continue
                    entry[field][new_entry] = entry[field][old_entry]
                    del entry[field][old_entry]
                    if old_entry in entry.get("compartmentalization", {}):
                        new_hash = copy.deepcopy(entry["compartmentalization"][old_entry])
                        new_hash["reaction"] = new_entry
                        for kbid in new_hash.get("kbase_ids", {}):
                            for rxn_idx in range(len(new_hash["kbase_ids"][kbid])):
                                rxn = new_hash["kbase_ids"][kbid][rxn_idx]
                                rxn = rxn.replace("_" + old_entry, "_" + new_entry)
                                new_hash["kbase_ids"][kbid][rxn_idx] = rxn
                        entry["compartmentalization"][new_entry] = new_hash
                        del entry["compartmentalization"][old_entry]
                    updated_role = True

        if entry["role"] in rem_dict:
            for field in rem_dict[entry["role"]]:
                for input_value in rem_dict[entry["role"]][field]:
                    fv = entry.get(field)
                    if isinstance(fv, list) and input_value in fv:
                        fv.remove(input_value)
                    elif isinstance(fv, dict) and input_value in fv:
                        del fv[input_value]
                    if field == "features":
                        delete_cpts = []
                        for cpt in entry.get("localization", {}):
                            if input_value in entry["localization"][cpt]:
                                del entry["localization"][cpt][input_value]
                            if len(entry["localization"][cpt]) == 0:
                                delete_cpts.append(cpt)
                        for cpt in delete_cpts:
                            del entry["localization"][cpt]
            updated_role = True

        if updated_role:
            entry.setdefault("curators", [])
            if curator and curator not in entry["curators"]:
                entry["curators"].append(curator)
            touched.add(entry["role"])

    return touched, rename_map


def assign_kbase_id(entry, existing_ids, renamed_from=None, issues=None):
    """Compute PS_role_<sha256[:6]> from role + reactions[0] + subsystems[0].

    Bug-fix-#4 note: this hash is order-sensitive on `reactions` and
    `subsystems`. ADD-append semantics preserve insertion order today; do
    not let a future "sort alphabetically" cleanup land without recomputing
    every kbase_id and warning downstream KBase consumers.
    """
    role_name = entry.get("role", "<unnamed>")
    if not entry.get("role") or not entry.get("reactions") or not entry.get("subsystems"):
        if renamed_from is not None or "kbase_id" not in entry:
            if issues is not None:
                issues.warn(
                    f"Missing role/reactions/subsystems for '{role_name}' — cannot create unique KBase Role ID"
                )
        return False
    if "kbase_id" in entry and renamed_from is None:
        return False
    old_id = entry.get("kbase_id")
    role_str = entry["role"] + entry["reactions"][0] + entry["subsystems"][0]
    entry_id = "PS_role_" + hashlib.sha256(role_str.encode("utf-8")).hexdigest()[:6]
    pool = set(existing_ids)
    if old_id in pool:
        pool.discard(old_id)
    while entry_id in pool:
        entry_id = "PS_role_" + hashlib.sha256(entry_id.encode("utf-8")).hexdigest()[:6]
    if entry_id == old_id:
        return False
    entry["kbase_id"] = entry_id
    if old_id:
        existing_ids.discard(old_id)
    existing_ids.add(entry_id)
    if renamed_from is not None and old_id is not None and issues is not None:
        issues.warn(
            f"kbase_id changed for renamed role '{role_name}' (was {old_id}, now {entry_id})"
        )
    return True


# ----------------------------------------------------------------------------
# Complex kbase_id assignment + derivation of new complexes from roles
# ----------------------------------------------------------------------------
def complex_kbase_id(enzyme, roles, rxn_cpts):
    """PS_complex_<sha256[:6]> from enzyme name + sorted roles + sorted rxn+'_'+cpt_id keys.

    Note: like `assign_kbase_id`, the hash is order-sensitive on `roles` and
    `rxn_cpts`. Callers must sort before hashing (this helper does not sort
    for you) so callers can be explicit about the ordering contract.
    """
    key = " / ".join([enzyme, "|".join(roles), "|".join(rxn_cpts)])
    return "PS_complex_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:6]


def enzyme_rxn_cpts(complex_entry):
    """Return the sorted list of `rxn+'_'+cpt_id` strings used for hashing this
    complex entry. Iterates `compartments_reactions[cpt_id].reactions` and
    joins each reaction id to its (single-letter) compartment key."""
    seen = []
    for cpt_id, cpt in complex_entry.get("compartments_reactions", {}).items():
        for rxn in cpt.get("reactions", []):
            key = f"{rxn}_{cpt_id}"
            if key not in seen:
                seen.append(key)
    return sorted(seen)


def assign_complex_kbase_id(entry, existing_ids, issues=None):
    """Compute the canonical PS_complex_* id for a complex entry and set it on
    the entry. `existing_ids` is a mutable set kept in sync as we assign IDs.

    Returns True if the entry's kbase_id changed (or was set for the first
    time), False otherwise.
    """
    enzyme = entry.get("enzyme")
    if not enzyme:
        if issues is not None:
            issues.warn("complex entry missing 'enzyme' — cannot mint kbase_id")
        return False
    roles = sorted(entry.get("roles", []))
    rxn_cpts = enzyme_rxn_cpts(entry)
    old_id = entry.get("kbase_id")
    new_id = complex_kbase_id(enzyme, roles, rxn_cpts)
    pool = set(existing_ids)
    if old_id in pool:
        pool.discard(old_id)
    while new_id in pool:
        new_id = "PS_complex_" + hashlib.sha256(new_id.encode("utf-8")).hexdigest()[:6]
    if new_id == old_id:
        return False
    entry["kbase_id"] = new_id
    if old_id:
        existing_ids.discard(old_id)
    existing_ids.add(new_id)
    if issues is not None and old_id:
        issues.log(
            f"complex kbase_id changed for enzyme '{enzyme}' (was {old_id}, now {new_id})"
        )
    return True


def enzyme_index_from_complexes(complexes_list, issues=None):
    """Build `{enzyme: {'roles': [...], 'rxn_cpts': [...]}}` lookup from an
    existing complexes list. Warns via `issues` on duplicate kbase_ids."""
    index = {}
    seen_ids = set()
    for entry in complexes_list:
        kid = entry.get("kbase_id")
        if kid:
            if kid in seen_ids and issues is not None:
                issues.warn(
                    f"duplicate complex kbase_id: {kid} for enzyme: {entry.get('enzyme')}"
                )
            seen_ids.add(kid)
        enz = entry.get("enzyme")
        if not enz:
            continue
        bucket = index.setdefault(enz, {"roles": [], "rxn_cpts": []})
        for role in entry.get("roles", []):
            if role not in bucket["roles"]:
                bucket["roles"].append(role)
        for rxn_cpt in enzyme_rxn_cpts(entry):
            if rxn_cpt not in bucket["rxn_cpts"]:
                bucket["rxn_cpts"].append(rxn_cpt)
    return index


def _abstract_enzyme_key(role_entry):
    """Return the abstract enzyme name for grouping, applying the
    spontaneous-reaction disambiguation. Returns None if the role has no
    abstract_enzyme set."""
    enz = role_entry.get("abstract_enzyme")
    if not enz:
        return None
    if enz.strip().lower() == "spontaneous reaction":
        rxns = role_entry.get("reactions", [])
        if rxns:
            enz = f"{enz}||{rxns[0]}"
    return enz


def _lcz_to_cpt_id(lcz):
    """Map a role's localization key to the single-letter compartment id used
    inside a complex's compartments_reactions dict. Transport (2-letter) keys
    collapse to their second letter, e.g. 'cv' -> 'v'. Matches the convention
    used by every hand-authored complex in the current database."""
    return lcz[-1] if len(lcz) > 1 else lcz


def derive_new_complexes(roles_list, enzyme_index, existing_ids, issues=None):
    """For every role whose `abstract_enzyme` (with spontaneous-reaction
    disambiguation) is NOT already in `enzyme_index`, build a new complex
    entry with a fresh PS_complex_* kbase_id.

    Returns the list of new complex dicts (each ready to append to
    PlantSEED_Complexes.json). `existing_ids` is mutated as new ids are
    minted so duplicates are avoided across successive calls.

    Roles missing `reactions` or `localization` are skipped (they cannot
    contribute a well-formed complex).
    """
    per_enzyme = {}  # enzyme -> {'roles': [], 'rxn_cpts': [], 'cpts': {}}
    for role in roles_list:
        enz = _abstract_enzyme_key(role)
        if not enz or enz in enzyme_index:
            continue
        if not role.get("reactions") or not role.get("localization"):
            continue
        bucket = per_enzyme.setdefault(enz, {"roles": [], "rxn_cpts": [], "cpts": {}})
        if role["role"] not in bucket["roles"]:
            bucket["roles"].append(role["role"])
        for rxn in role["reactions"]:
            for lcz in role["localization"]:
                cpt_id = _lcz_to_cpt_id(lcz)
                rxn_cpt = f"{rxn}_{cpt_id}"
                if rxn_cpt not in bucket["rxn_cpts"]:
                    bucket["rxn_cpts"].append(rxn_cpt)
                cpt_bucket = bucket["cpts"].setdefault(
                    cpt_id,
                    {"reactions": [], "reagents": lcz, "exclude": False},
                )
                if rxn not in cpt_bucket["reactions"]:
                    cpt_bucket["reactions"].append(rxn)
    new_complexes = []
    for enz, bucket in per_enzyme.items():
        roles = sorted(bucket["roles"])
        rxn_cpts = sorted(bucket["rxn_cpts"])
        kid = complex_kbase_id(enz, roles, rxn_cpts)
        pool = set(existing_ids)
        while kid in pool:
            kid = "PS_complex_" + hashlib.sha256(kid.encode("utf-8")).hexdigest()[:6]
        existing_ids.add(kid)
        new_complexes.append({
            "kbase_id": kid,
            "enzyme": enz,
            "roles": roles,
            "compartments_reactions": bucket["cpts"],
        })
        if issues is not None:
            issues.log(f"new complex minted for enzyme '{enz}' as {kid}")
    return new_complexes


def validate_subcomplex_pointers(roles_list, complex_ids, issues=None):
    """Walk `roles_list` and warn (via `issues`) for every role whose
    `subcomplex_of` value is non-empty AND does not appear in `complex_ids`.

    Runs AFTER all complex kbase_ids are settled (existing verified + new
    derived) so a role that legitimately points at a freshly-minted parent
    doesn't produce a false-positive warning.

    Returns the list of (role_name, bad_pointer) tuples the caller may want
    to surface separately from the issue stream.
    """
    complex_ids = set(complex_ids)
    bad = []
    for role in roles_list:
        target = role.get("subcomplex_of")
        if not target:
            continue
        if target not in complex_ids:
            bad.append((role.get("role", "<unnamed>"), target))
            if issues is not None:
                issues.warn(
                    f"role '{role.get('role', '<unnamed>')}' has "
                    f"subcomplex_of={target!r} pointing at a complex "
                    f"kbase_id not present in PlantSEED_Complexes.json"
                )
    return bad


def _known_roles_for_actions(actions):
    roles = set()
    for bucket in ("replace", "add", "rem", "key", "reassign"):
        roles.update(actions[bucket].keys())
    roles.update(actions["new"])
    roles.update(actions["replace"].keys())
    return roles


def _issue_dict(issues, summary, role_diffs):
    return {"warnings": issues.warnings, "errors": issues.errors,
            "info": issues.info, "summary": summary, "role_diffs": role_diffs}


def run_apply(tsv_text, curator, schema, dry_run=False, store=None, roles_path=None):
    """Parse `tsv_text` and apply it against the roles JSON at `roles_path`
    (defaults to paths.ROLES_FILE). Mirrors Update_Enzymes_in_PlantSEED.py's
    behaviour but takes the TSV as text and returns a structured dict."""
    issues = IssueCollector()
    actions = parse_tsv_text(tsv_text, schema=schema, issues=issues)
    target_roles_path = roles_path or paths.ROLES_FILE
    if not os.path.isfile(target_roles_path):
        issues.error(f"PlantSEED_Roles.json not found at {target_roles_path}")
        return _issue_dict(issues, summary={}, role_diffs=[])

    with open(target_roles_path) as f:
        roles_list = json.load(f)

    known_roles = {entry["role"] for entry in roles_list} | set(actions["new"])
    bucket_to_action = {"replace": "UPDATE", "add": "ADD", "rem": "REMOVE",
                        "key": "RELOCATE", "reassign": "REASSIGN"}
    for bucket, action_name in bucket_to_action.items():
        for role_name in actions[bucket]:
            if role_name not in known_roles:
                issues.warn(
                    f"role '{role_name}' not found in database — its {action_name} action(s) will be ignored"
                )

    affected = set(_known_roles_for_actions(actions))
    before_snapshot = {r["role"]: copy.deepcopy(r)
                       for r in roles_list if r["role"] in affected}

    if not seed_new_entries(roles_list, actions["new"], schema, actions=actions, issues=issues):
        return _issue_dict(issues, summary={}, role_diffs=[])

    touched, rename_map = apply_actions(
        roles_list, actions, curator, issues=issues, schema=schema
    )
    touched.update(actions["new"])

    reverse_rename = {new: old for old, new in rename_map.items()}
    existing_ids = {entry["kbase_id"] for entry in roles_list if "kbase_id" in entry}
    for entry in roles_list:
        if entry["role"] not in touched:
            continue
        for w in ensure_schema_defaults(entry, schema):
            issues.warn(w)
        for w in validate_dependencies(entry, schema):
            issues.warn(w)
        assign_kbase_id(
            entry, existing_ids,
            renamed_from=reverse_rename.get(entry["role"]), issues=issues,
        )

    role_diffs = []
    for entry in roles_list:
        if entry["role"] not in touched:
            continue
        old_name = reverse_rename.get(entry["role"], entry["role"])
        role_diffs.append({
            "role":         entry["role"],
            "renamed_from": old_name if old_name != entry["role"] else None,
            "before":       before_snapshot.get(old_name),
            "after":        copy.deepcopy(entry),
            "is_new":       entry["role"] in actions["new"],
        })

    summary = {"touched": sorted(touched), "renamed": rename_map,
               "new": actions["new"], "dry_run": dry_run}
    if not dry_run and touched and not issues.errors:
        atomic_write(target_roles_path, json.dumps(roles_list, indent=4))
        issues.log(f"Wrote {len(roles_list)} roles to {target_roles_path}")
        if store is not None:
            store.load_roles(force=True)
    elif dry_run:
        issues.log(f"Dry run — no file written. {len(touched)} role(s) would be touched.")
    elif not touched:
        issues.log("No roles touched — nothing to write.")
    elif issues.errors:
        issues.log("Errors present — refusing to write database.")
    return _issue_dict(issues, summary=summary, role_diffs=role_diffs)


def preview_for_enzyme(enzyme, rows, schema, store):
    """Dry-apply `rows` against an in-memory copy of `store.roles` and
    return (before, after, errors, warnings, touched, renamed_to) for the
    specific enzyme."""
    issues = IssueCollector()
    text = "\n".join(rows)
    actions = parse_tsv_text(text, schema=schema, issues=issues)
    roles_copy = copy.deepcopy(store.roles)
    before = next((copy.deepcopy(r) for r in roles_copy if r["role"] == enzyme), None)
    if enzyme in actions["new"]:
        before = None
    if not seed_new_entries(roles_copy, actions["new"], schema, actions=actions, issues=issues):
        return {"before": before, "after": None,
                "errors": issues.errors, "warnings": issues.warnings}
    touched, rename_map = apply_actions(
        roles_copy, actions, curator="(preview)", issues=issues, schema=schema
    )
    final_name = rename_map.get(enzyme, enzyme)
    after = next((r for r in roles_copy if r["role"] == final_name), None)
    return {
        "before":     before,
        "after":      after,
        "renamed_to": final_name if final_name != enzyme else None,
        "errors":     issues.errors,
        "warnings":   issues.warnings,
        "touched":    sorted(touched),
    }
