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


# ---------- integration: paths + full driver bits ----------------------------
def test_complexes_file_env_override(tmp_db):
    """PLANTSEED_COMPLEXES_FILE gets picked up by the paths module and points
    at the tmp fixture, not the real database."""
    from plantseed_curation import paths as p
    assert p.COMPLEXES_FILE == tmp_db["complexes"]
    with open(p.COMPLEXES_FILE) as fh:
        data = json.load(fh)
    assert data[0]["enzyme"] == "Alpha enzyme"
