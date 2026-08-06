"""complex_kbase_id, assign_complex_kbase_id, enzyme_index_from_complexes,
derive_new_complexes — the complex-side of the KBase-ID plumbing that
Prepare_PlantSEED_KBase.py drives."""

import hashlib
import json

import pytest

from plantseed_curation import actions as A
from plantseed_curation.schema import IssueCollector


# ---------- complex_kbase_id (pure hash) -------------------------------------
def test_complex_kbase_id_is_deterministic():
    a = A.complex_kbase_id("Enz", ["Role1"], ["rxnA_c"])
    b = A.complex_kbase_id("Enz", ["Role1"], ["rxnA_c"])
    assert a == b
    assert a.startswith("PS_complex_")
    assert len(a) == len("PS_complex_") + 6


def test_complex_kbase_id_order_sensitive():
    """Callers must sort — helper does not."""
    a = A.complex_kbase_id("Enz", ["R1", "R2"], ["rxnA_c"])
    b = A.complex_kbase_id("Enz", ["R2", "R1"], ["rxnA_c"])
    assert a != b


def test_complex_kbase_id_matches_manual_hash():
    key = "Enz / R1|R2 / rxnA_c|rxnB_d"
    expected = "PS_complex_" + hashlib.sha256(key.encode()).hexdigest()[:6]
    assert A.complex_kbase_id("Enz", ["R1", "R2"], ["rxnA_c", "rxnB_d"]) == expected


# ---------- enzyme_rxn_cpts --------------------------------------------------
def test_enzyme_rxn_cpts_from_single_compartment():
    entry = {
        "compartments_reactions": {
            "c": {"reactions": ["rxn1"], "reagents": "c", "exclude": False}
        }
    }
    assert A.enzyme_rxn_cpts(entry) == ["rxn1_c"]


def test_enzyme_rxn_cpts_sorts_and_dedupes():
    entry = {
        "compartments_reactions": {
            "d": {"reactions": ["rxnB", "rxnA"], "reagents": "d", "exclude": False},
            "c": {"reactions": ["rxnA"], "reagents": "c", "exclude": False},
        }
    }
    assert A.enzyme_rxn_cpts(entry) == ["rxnA_c", "rxnA_d", "rxnB_d"]


def test_enzyme_rxn_cpts_empty_when_no_compartments_reactions():
    assert A.enzyme_rxn_cpts({}) == []


# ---------- assign_complex_kbase_id ------------------------------------------
def test_assign_complex_kbase_id_leaves_matching_id_alone():
    entry = {
        "enzyme": "Alpha enzyme",
        "roles": ["Alpha enzyme (EC 1.1.1.1)"],
        "compartments_reactions": {
            "c": {"reactions": ["rxn00001"], "reagents": "c", "exclude": False}
        },
    }
    canonical = A.complex_kbase_id(
        "Alpha enzyme", sorted(entry["roles"]), A.enzyme_rxn_cpts(entry)
    )
    entry["kbase_id"] = canonical
    existing = {canonical}
    changed = A.assign_complex_kbase_id(entry, existing)
    assert changed is False
    assert entry["kbase_id"] == canonical


def test_assign_complex_kbase_id_rehashes_when_roles_change():
    entry = {
        "kbase_id": "PS_complex_stale1",
        "enzyme": "Enz",
        "roles": ["R1", "R2"],
        "compartments_reactions": {
            "c": {"reactions": ["rxn1"], "reagents": "c", "exclude": False}
        },
    }
    existing = {"PS_complex_stale1"}
    issues = IssueCollector()
    changed = A.assign_complex_kbase_id(entry, existing, issues=issues)
    assert changed is True
    assert entry["kbase_id"] != "PS_complex_stale1"
    assert entry["kbase_id"] in existing
    assert "PS_complex_stale1" not in existing
    assert any("kbase_id changed" in m for m in issues.info)


def test_assign_complex_kbase_id_missing_enzyme_warns_and_no_change():
    entry = {"roles": ["R"], "compartments_reactions": {}}
    existing = set()
    issues = IssueCollector()
    changed = A.assign_complex_kbase_id(entry, existing, issues=issues)
    assert changed is False
    assert "kbase_id" not in entry
    assert issues.warnings


def test_assign_complex_kbase_id_resolves_collision():
    entry = {
        "enzyme": "Enz",
        "roles": ["R1"],
        "compartments_reactions": {
            "c": {"reactions": ["rxn1"], "reagents": "c", "exclude": False}
        },
    }
    canonical = A.complex_kbase_id(
        "Enz", ["R1"], A.enzyme_rxn_cpts(entry)
    )
    # Occupy the canonical id under a different enzyme so we force a rehash.
    existing = {canonical}
    changed = A.assign_complex_kbase_id(entry, existing)
    assert changed is True
    assert entry["kbase_id"] != canonical
    assert entry["kbase_id"] in existing


# ---------- enzyme_index_from_complexes --------------------------------------
def test_enzyme_index_collects_roles_and_rxn_cpts():
    complexes = [
        {
            "kbase_id": "PS_complex_a",
            "enzyme": "Enz",
            "roles": ["R1"],
            "compartments_reactions": {
                "c": {"reactions": ["rxn1"], "reagents": "c", "exclude": False}
            },
        },
        {
            "kbase_id": "PS_complex_b",
            "enzyme": "Enz",
            "roles": ["R2"],
            "compartments_reactions": {
                "d": {"reactions": ["rxn2"], "reagents": "d", "exclude": False}
            },
        },
    ]
    idx = A.enzyme_index_from_complexes(complexes)
    assert set(idx.keys()) == {"Enz"}
    assert set(idx["Enz"]["roles"]) == {"R1", "R2"}
    assert set(idx["Enz"]["rxn_cpts"]) == {"rxn1_c", "rxn2_d"}


def test_enzyme_index_flags_duplicate_kbase_id():
    complexes = [
        {"kbase_id": "PS_complex_dup", "enzyme": "A", "roles": [], "compartments_reactions": {}},
        {"kbase_id": "PS_complex_dup", "enzyme": "B", "roles": [], "compartments_reactions": {}},
    ]
    issues = IssueCollector()
    A.enzyme_index_from_complexes(complexes, issues=issues)
    assert any("duplicate complex kbase_id" in w for w in issues.warnings)


# ---------- derive_new_complexes ---------------------------------------------
def _role(name, enz, rxns, lczs, sub="S"):
    return {
        "role":            name,
        "abstract_enzyme": enz,
        "reactions":       list(rxns),
        "subsystems":      [sub],
        "localization":    {l: {} for l in lczs},
    }


def test_derive_new_complexes_adds_missing_enzyme():
    roles = [
        _role("Delta enzyme (EC 4.4.4.4)", "Delta enzyme", ["rxn00004"], ["c"]),
    ]
    idx = {}  # nothing in complexes yet
    existing_ids = set()
    new = A.derive_new_complexes(roles, idx, existing_ids)
    assert len(new) == 1
    entry = new[0]
    assert entry["enzyme"] == "Delta enzyme"
    assert entry["roles"] == ["Delta enzyme (EC 4.4.4.4)"]
    assert entry["compartments_reactions"] == {
        "c": {"reactions": ["rxn00004"], "reagents": "c", "exclude": False}
    }
    assert entry["kbase_id"].startswith("PS_complex_")
    assert entry["kbase_id"] in existing_ids


def test_derive_new_complexes_skips_existing_enzyme():
    roles = [_role("R", "Enz", ["rxn1"], ["c"])]
    idx = {"Enz": {"roles": ["R"], "rxn_cpts": ["rxn1_c"]}}
    new = A.derive_new_complexes(roles, idx, set())
    assert new == []


def test_derive_new_complexes_skips_role_without_reactions_or_localization():
    roles = [
        _role("no-rxn", "Enz1", [], ["c"]),
        _role("no-lcz", "Enz2", ["rxn1"], []),
    ]
    new = A.derive_new_complexes(roles, {}, set())
    assert new == []


def test_derive_new_complexes_disambiguates_spontaneous_reaction():
    """Two 'Spontaneous Reaction' roles with different reactions should produce
    two distinct complex entries."""
    roles = [
        _role("Sp1", "Spontaneous Reaction", ["rxn0001"], ["c"]),
        _role("Sp2", "Spontaneous Reaction", ["rxn0002"], ["c"]),
    ]
    new = A.derive_new_complexes(roles, {}, set())
    assert len(new) == 2
    enzymes = {e["enzyme"] for e in new}
    assert enzymes == {"Spontaneous Reaction||rxn0001", "Spontaneous Reaction||rxn0002"}


def test_derive_new_complexes_2letter_localization_uses_second_letter_key():
    """A 'cv' transport role should produce a complex with cpt key 'v' and
    reagents 'cv' — matching how every hand-authored transport complex is
    structured today."""
    roles = [_role("T", "Transporter", ["rxnT"], ["cv"])]
    new = A.derive_new_complexes(roles, {}, set())
    assert len(new) == 1
    cr = new[0]["compartments_reactions"]
    assert list(cr.keys()) == ["v"]
    assert cr["v"]["reagents"] == "cv"
    assert cr["v"]["reactions"] == ["rxnT"]


# ---------- _lcz_to_cpt_id transport-rule cases ------------------------------
@pytest.mark.parametrize("lcz, expected", [
    # 1-letter codes pass through
    ("c", "c"), ("d", "d"), ("m", "m"), ("x", "x"), ("v", "v"),
    # 2-letter cases from Transport_Compartment_Rules.yaml
    ("cv", "v"),  # non-cytosolic wins
    ("cd", "d"),
    ("cm", "m"),
    ("cx", "x"),
    ("ce", "c"),  # non-extracellular wins (rule 2 overrides rule 1)
    ("de", "d"),  # non-extracellular wins
    ("dy", "y"),  # thylakoid lumen wins over plastid stroma
    ("mj", "j"),  # intermembrane wins over matrix
])
def test_lcz_to_cpt_id_matches_transport_rules_yaml(lcz, expected):
    assert A._lcz_to_cpt_id(lcz) == expected


def test_lcz_to_cpt_id_falls_back_to_first_letter_for_unknown_pair():
    """A 2-letter code with no rule triggers uses the first letter."""
    assert A._lcz_to_cpt_id("ab") == "a"


def test_transport_rules_stay_in_sync_with_yaml():
    """If Transport_Compartment_Rules.yaml is edited, the hardcoded
    _TRANSPORT_RULES tuple in actions.py must be edited too. This test
    fails when they drift."""
    import os
    import yaml
    # actions.py lives at Scripts/PlantSEED_v3/Curation/plantseed_curation/actions.py.
    # The yaml lives at   Scripts/PlantSEED_v3/Template/Transport_Compartment_Rules.yaml.
    # So: two `..` back to PlantSEED_v3, then into Template/.
    yaml_path = os.path.normpath(os.path.join(
        os.path.dirname(A.__file__), "..", "..",
        "Template", "Transport_Compartment_Rules.yaml",
    ))
    if not os.path.isfile(yaml_path):
        pytest.skip(f"yaml source-of-truth not present at {yaml_path}")
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    yaml_rules = [(r["if_contains"], r["result"]) for r in data["rules"]]
    assert list(A._TRANSPORT_RULES) == yaml_rules, (
        f"_TRANSPORT_RULES ({A._TRANSPORT_RULES}) drifted from "
        f"Transport_Compartment_Rules.yaml ({yaml_rules}). Edit both."
    )


def test_derive_new_complexes_merges_multiple_roles_for_same_enzyme():
    roles = [
        _role("R1", "Enz", ["rxn1"], ["c"]),
        _role("R2", "Enz", ["rxn2"], ["c"]),
    ]
    new = A.derive_new_complexes(roles, {}, set())
    assert len(new) == 1
    entry = new[0]
    assert entry["enzyme"] == "Enz"
    assert entry["roles"] == ["R1", "R2"]  # sorted
    assert set(entry["compartments_reactions"]["c"]["reactions"]) == {"rxn1", "rxn2"}


def test_derive_new_complexes_kbase_id_matches_pure_hash():
    roles = [_role("Solo (EC 5.5.5.5)", "Solo", ["rxnX"], ["c"])]
    new = A.derive_new_complexes(roles, {}, set())
    expected = A.complex_kbase_id("Solo", ["Solo (EC 5.5.5.5)"], ["rxnX_c"])
    assert new[0]["kbase_id"] == expected


# ---------- validate_subcomplex_pointers -------------------------------------
def test_validate_subcomplex_pointers_empty_target_is_ok():
    """Roles with no subcomplex_of (or an empty string) never warn."""
    roles = [
        {"role": "R1"},                       # field absent
        {"role": "R2", "subcomplex_of": ""},  # field empty
    ]
    issues = IssueCollector()
    bad = A.validate_subcomplex_pointers(roles, set(), issues=issues)
    assert bad == []
    assert issues.warnings == []


def test_validate_subcomplex_pointers_present_target_is_ok():
    roles = [{"role": "R1", "subcomplex_of": "PS_complex_parent"}]
    issues = IssueCollector()
    bad = A.validate_subcomplex_pointers(roles, {"PS_complex_parent"}, issues=issues)
    assert bad == []
    assert issues.warnings == []


def test_validate_subcomplex_pointers_missing_target_warns():
    roles = [
        {"role": "R1", "subcomplex_of": "PS_complex_ghost"},
        {"role": "R2", "subcomplex_of": "PS_complex_also_missing"},
    ]
    issues = IssueCollector()
    bad = A.validate_subcomplex_pointers(roles, {"PS_complex_parent"}, issues=issues)
    assert bad == [
        ("R1", "PS_complex_ghost"),
        ("R2", "PS_complex_also_missing"),
    ]
    assert len(issues.warnings) == 2
    assert any("PS_complex_ghost" in w for w in issues.warnings)


def test_validate_subcomplex_pointers_accepts_freshly_derived_parent():
    """The validation must run AFTER derive_new_complexes so a role pointing
    at a parent that was just minted this run doesn't warn."""
    roles = [
        _role("Parent role", "ParentEnz", ["rxn1"], ["c"]),
        {"role":            "Child role",
         "subcomplex_of":   None,  # placeholder, filled in below
         "abstract_enzyme": "ChildEnz",
         "reactions":       ["rxn2"],
         "subsystems":      ["S"],
         "localization":    {"c": {}}},
    ]
    existing_ids = set()
    new = A.derive_new_complexes(roles, {}, existing_ids)
    parent_id = next(c["kbase_id"] for c in new if c["enzyme"] == "ParentEnz")
    roles[1]["subcomplex_of"] = parent_id  # now legitimately points at the fresh parent
    all_ids = {c["kbase_id"] for c in new}
    issues = IssueCollector()
    bad = A.validate_subcomplex_pointers(roles, all_ids, issues=issues)
    assert bad == []
    assert issues.warnings == []


# ---------- integration: paths + full driver bits ----------------------------
def test_complexes_file_env_override(tmp_db):
    """PLANTSEED_COMPLEXES_FILE gets picked up by the paths module and points
    at the tmp fixture, not the real database."""
    from plantseed_curation import paths as p
    assert p.COMPLEXES_FILE == tmp_db["complexes"]
    with open(p.COMPLEXES_FILE) as fh:
        data = json.load(fh)
    assert data[0]["enzyme"] == "Alpha enzyme"
