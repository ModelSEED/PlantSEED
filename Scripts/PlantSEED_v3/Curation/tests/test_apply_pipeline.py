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
