"""Scenario tests for the end-to-end apply pipeline. These are the
'sequence of actions and assert on the resulting JSON' checks that exist
specifically so Sam doesn't have to walk through them by hand."""

import json

from plantseed_curation import actions as A
from plantseed_curation import paths


def _reload_roles():
    with open(paths.ROLES_FILE) as f:
        return json.load(f)


def _find(roles, name):
    return next((r for r in roles if r["role"] == name), None)


def test_new_with_add_cascade(tmp_db, schema):
    tsv = (
        "Delta enzyme (EC 4.4.4.4)\tNEW\n"
        "Delta enzyme (EC 4.4.4.4)\tADD\tsubsystems\tDelta_subsystem\tCofactors\n"
        "Delta enzyme (EC 4.4.4.4)\tADD\treactions\trxn00099\td\n"
        "Delta enzyme (EC 4.4.4.4)\tADD\tfeatures\tAthaliana_TAIR10||AT9G99999\tc:PPDB\n"
    )
    result = A.run_apply(tsv, "vibhav", schema)
    assert result["errors"] == []
    roles = _reload_roles()
    new_role = _find(roles, "Delta enzyme (EC 4.4.4.4)")
    assert new_role is not None
    assert new_role["subsystems"] == ["Delta_subsystem"]
    # subsystems ADD with a class cascades into classes.
    assert new_role["classes"] == {"Cofactors": {"Delta_subsystem": {}}} or \
           new_role["classes"]["Cofactors"]["Delta_subsystem"] == []
    # reaction was placed in compartment 'd'.
    assert new_role["localization"]["d"]["rxn00099"] == ["Assumed"]
    # feature was placed in compartment 'c' with the supplied source.
    assert new_role["localization"]["c"]["Athaliana_TAIR10||AT9G99999"] == ["PPDB"]
    # abstract_enzyme derived from the role name minus " (EC ...)".
    assert new_role["abstract_enzyme"] == "Delta enzyme"
    # curator was appended.
    assert "vibhav" in new_role["curators"]
    # kbase_id assigned.
    assert new_role["kbase_id"].startswith("PS_role_")


def test_add_feature_without_extra_defaults_compartment_c(tmp_db, schema):
    tsv = "Alpha enzyme (EC 1.1.1.1)\tADD\tfeatures\tAthaliana_TAIR10||ATXG00001\n"
    result = A.run_apply(tsv, "tester", schema)
    assert result["errors"] == []
    roles = _reload_roles()
    role = _find(roles, "Alpha enzyme (EC 1.1.1.1)")
    assert role["localization"]["c"]["Athaliana_TAIR10||ATXG00001"] == ["Assumed"]
    assert any("no localization" in w for w in result["warnings"])


def test_add_reaction_without_compartment_defaults_to_c(tmp_db, schema):
    tsv = "Beta enzyme (EC 2.2.2.2)\tADD\treactions\trxn00999\n"
    A.run_apply(tsv, "tester", schema)
    roles = _reload_roles()
    role = _find(roles, "Beta enzyme (EC 2.2.2.2)")
    assert role["localization"]["c"]["rxn00999"] == ["Assumed"]


def test_remove_feature_cascades_out_of_localization(tmp_db, schema):
    tsv = "Beta enzyme (EC 2.2.2.2)\tREMOVE\tfeatures\tAthaliana_TAIR10||AT2G00020\n"
    A.run_apply(tsv, "tester", schema)
    roles = _reload_roles()
    role = _find(roles, "Beta enzyme (EC 2.2.2.2)")
    assert "Athaliana_TAIR10||AT2G00020" not in role["features"]
    # Compartment 'd' only contained that feature, so it's gone too.
    assert "d" not in role["localization"]


def test_update_rename_recomputes_kbase_id(tmp_db, schema):
    tsv = "Alpha enzyme (EC 1.1.1.1)\tUPDATE\tAlpha renamed (EC 1.1.1.1)\n"
    A.run_apply(tsv, "tester", schema)
    roles = _reload_roles()
    renamed = _find(roles, "Alpha renamed (EC 1.1.1.1)")
    assert renamed is not None
    assert renamed["kbase_id"] != "PS_role_alpha1"  # was rehashed
    # Old name is gone.
    assert _find(roles, "Alpha enzyme (EC 1.1.1.1)") is None


def _reload_complexes():
    with open(paths.COMPLEXES_FILE) as f:
        return json.load(f)


def test_update_rename_syncs_default_complex_enzyme_and_roles(tmp_db, schema):
    """Regression test for a role UPDATE leaving PlantSEED_Complexes.json
    with a dangling reference to the pre-rename role name. mini_complexes.json
    has a default one-role-one-enzyme complex for 'Alpha enzyme' (enzyme ==
    role minus the EC parenthetical) -- both its `enzyme` key and its `roles`
    list must follow the rename."""
    tsv = "Alpha enzyme (EC 1.1.1.1)\tUPDATE\tAlpha renamed (EC 1.1.1.1)\n"
    result = A.run_apply(tsv, "tester", schema)
    assert result["errors"] == []
    complexes = _reload_complexes()
    entry = next(c for c in complexes if c["kbase_id"] == "PS_complex_alpha1")
    assert entry["enzyme"] == "Alpha renamed"
    assert entry["roles"] == ["Alpha renamed (EC 1.1.1.1)"]
    # No complex is left naming the pre-rename role anywhere.
    assert not any("Alpha enzyme (EC 1.1.1.1)" in c.get("roles", []) for c in complexes)
    assert not any(c.get("enzyme") == "Alpha enzyme" for c in complexes)


def test_sync_renamed_roles_into_complexes_updates_roles_list_only(tmp_db, schema):
    """Direct unit test of sync_renamed_roles_into_complexes: a complex whose
    `roles` list contains the old role name, but whose `enzyme` key is an
    unrelated grouping key (e.g. a subunit complex), gets its `roles` entry
    swapped without the `enzyme` key being touched."""
    complexes_list = [
        {
            "kbase_id": "PS_complex_grouped1",
            "enzyme": "Grouped enzyme",
            "roles": ["Alpha enzyme (EC 1.1.1.1)", "Other subunit role"],
            "compartments_reactions": {},
        },
    ]
    rename_map = {"Alpha enzyme (EC 1.1.1.1)": "Alpha renamed (EC 1.1.1.1)"}
    changed = A.sync_renamed_roles_into_complexes(complexes_list, rename_map)
    assert changed is True
    assert complexes_list[0]["enzyme"] == "Grouped enzyme"  # untouched
    assert complexes_list[0]["roles"] == [
        "Alpha renamed (EC 1.1.1.1)", "Other subunit role",
    ]


def test_sync_renamed_roles_into_complexes_noop_when_no_match(tmp_db, schema):
    complexes_list = [
        {"kbase_id": "PS_complex_x", "enzyme": "Unrelated", "roles": ["Unrelated role"]},
    ]
    changed = A.sync_renamed_roles_into_complexes(
        complexes_list, {"Alpha enzyme (EC 1.1.1.1)": "Alpha renamed (EC 1.1.1.1)"}
    )
    assert changed is False
    assert complexes_list[0]["roles"] == ["Unrelated role"]


def test_update_rename_in_grouped_complex_syncs_roles_not_enzyme(tmp_db, schema):
    """End-to-end reproduction of the production bug: 'Alpha enzyme' is
    (hypothetically) a subunit folded into a multi-role 'Photosystem X'
    complex, grouped under an abstract_enzyme that does NOT match any single
    role name. Renaming the role must update that complex's `roles` list so
    Generate_Core_ModelTemplate.py's role-type lookup doesn't KeyError on the
    stale name -- while leaving the `enzyme` grouping key untouched."""
    complexes = _reload_complexes()
    complexes.append({
        "kbase_id": "PS_complex_grouped_x",
        "enzyme": "Photosystem X",
        "roles": ["Alpha enzyme (EC 1.1.1.1)", "Beta enzyme (EC 2.2.2.2)"],
        "compartments_reactions": {
            "c": {"reactions": ["rxn00001", "rxn00002"], "reagents": "c", "exclude": False},
        },
    })
    with open(paths.COMPLEXES_FILE, "w") as f:
        json.dump(complexes, f, indent=4)

    tsv = "Alpha enzyme (EC 1.1.1.1)\tUPDATE\tAlpha renamed (EC 1.1.1.1)\n"
    result = A.run_apply(tsv, "tester", schema)
    assert result["errors"] == []

    complexes = _reload_complexes()
    grouped = next(c for c in complexes if c["kbase_id"] == "PS_complex_grouped_x")
    assert grouped["enzyme"] == "Photosystem X"  # grouping key untouched
    assert grouped["roles"] == ["Alpha renamed (EC 1.1.1.1)", "Beta enzyme (EC 2.2.2.2)"]
    assert "Alpha enzyme (EC 1.1.1.1)" not in grouped["roles"]

    # And every role every complex names actually exists in roles_list --
    # the exact invariant Generate_Core_ModelTemplate.py's type lookup needs.
    roles = _reload_roles()
    role_names = {r["role"] for r in roles}
    for c in complexes:
        for r in c.get("roles", []):
            assert r in role_names, f"dangling role reference '{r}' in complex '{c['enzyme']}'"


def test_relocate_localization_key(tmp_db, schema):
    tsv = "Alpha enzyme (EC 1.1.1.1)\tRELOCATE\tlocalization\tc\tn\n"
    A.run_apply(tsv, "tester", schema)
    roles = _reload_roles()
    role = _find(roles, "Alpha enzyme (EC 1.1.1.1)")
    assert "c" not in role["localization"]
    assert "n" in role["localization"]
    # Content preserved under the new key.
    assert role["localization"]["n"]["Athaliana_TAIR10||AT1G00010"] == ["PPDB"]


def test_reassign_bool_coerces_to_python_bool(tmp_db, schema):
    tsv = "Alpha enzyme (EC 1.1.1.1)\tREASSIGN\tinclude\tfalse\n"
    A.run_apply(tsv, "tester", schema)
    roles = _reload_roles()
    role = _find(roles, "Alpha enzyme (EC 1.1.1.1)")
    assert role["include"] is False


def test_deprecated_assign_alias_still_applies(tmp_db, schema):
    """Existing curator TSVs using ASSIGN keep working unchanged."""
    tsv = "Alpha enzyme (EC 1.1.1.1)\tASSIGN\tinclude\tfalse\n"
    result = A.run_apply(tsv, "tester", schema)
    roles = _reload_roles()
    role = _find(roles, "Alpha enzyme (EC 1.1.1.1)")
    assert role["include"] is False
    assert any("'ASSIGN' is deprecated" in w for w in result["warnings"])


def test_deprecated_change_alias_still_applies(tmp_db, schema):
    """Existing curator TSVs using CHANGE keep working unchanged."""
    tsv = "Alpha enzyme (EC 1.1.1.1)\tCHANGE\tabstract_enzyme\tAlpha2\n"
    result = A.run_apply(tsv, "tester", schema)
    roles = _reload_roles()
    role = _find(roles, "Alpha enzyme (EC 1.1.1.1)")
    assert role["abstract_enzyme"] == "Alpha2"
    assert any("'CHANGE' is deprecated" in w for w in result["warnings"])


def test_dry_run_does_not_write(tmp_db, schema):
    tsv = "Alpha enzyme (EC 1.1.1.1)\tREASSIGN\tinclude\tfalse\n"
    A.run_apply(tsv, "tester", schema, dry_run=True)
    roles = _reload_roles()
    role = _find(roles, "Alpha enzyme (EC 1.1.1.1)")
    assert role["include"] is True  # unchanged on disk


def test_action_on_unknown_role_warns_skip(tmp_db, schema):
    tsv = "Nonexistent enzyme\tADD\tfeatures\tF\tc:PPDB\n"
    result = A.run_apply(tsv, "tester", schema)
    assert any("not found in database" in w for w in result["warnings"])


def test_role_diffs_reported(tmp_db, schema):
    tsv = "Alpha enzyme (EC 1.1.1.1)\tREASSIGN\ttype\tconditional\n"
    result = A.run_apply(tsv, "tester", schema)
    assert len(result["role_diffs"]) == 1
    diff = result["role_diffs"][0]
    assert diff["role"] == "Alpha enzyme (EC 1.1.1.1)"
    assert diff["before"]["type"] == "universal"
    assert diff["after"]["type"] == "conditional"


def test_preview_does_not_mutate_store(tmp_db, schema, store):
    rows = ["Alpha enzyme (EC 1.1.1.1)\tREASSIGN\ttype\tconditional"]
    result = A.preview_for_enzyme(
        "Alpha enzyme (EC 1.1.1.1)", rows, schema, store
    )
    assert result["after"]["type"] == "conditional"
    # Store unchanged.
    assert store.role_index["Alpha enzyme (EC 1.1.1.1)"]["type"] == "universal"
