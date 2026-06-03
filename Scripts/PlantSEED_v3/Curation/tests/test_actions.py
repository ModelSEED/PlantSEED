"""validate_payload, build_tsv_rows, parse_tsv_text — the core surface every
interface goes through."""

import pytest

from plantseed_curation import actions as A
from plantseed_curation.schema import IssueCollector


# ---------- validate_payload -------------------------------------------------
def test_validate_new_existing_role_errors(store):
    errs, _ = A.validate_payload(
        "NEW", "Alpha enzyme (EC 1.1.1.1)", {}, store
    )
    assert any(e["field"] == "enzyme" for e in errs)


def test_validate_new_novel_role_ok(store):
    errs, warns = A.validate_payload("NEW", "Brand new enzyme", {}, store)
    assert errs == []


def test_validate_update_requires_new_name(store):
    errs, _ = A.validate_payload(
        "UPDATE", "Alpha enzyme (EC 1.1.1.1)", {}, store
    )
    assert any(e["field"] == "new_name" for e in errs)


def test_validate_update_collision_with_existing(store):
    errs, _ = A.validate_payload(
        "UPDATE", "Alpha enzyme (EC 1.1.1.1)",
        {"new_name": "Beta enzyme (EC 2.2.2.2)"}, store,
    )
    assert any(e["field"] == "new_name" for e in errs)


def test_validate_add_features_requires_compartment_source_extra(store):
    errs, _ = A.validate_payload(
        "ADD", "Alpha enzyme (EC 1.1.1.1)",
        {"field": "features", "entries": [{"value": "F1", "extra": "no-colon"}]}, store,
    )
    assert any("compartment:source" in e["message"] for e in errs)


def test_validate_add_features_empty_extra_warns(store):
    errs, warns = A.validate_payload(
        "ADD", "Alpha enzyme (EC 1.1.1.1)",
        {"field": "features", "entries": [{"value": "F1", "extra": ""}]}, store,
    )
    assert errs == []
    assert any("cytosol" in w for w in warns)


def test_validate_add_reactions_unknown_compartment(store):
    errs, _ = A.validate_payload(
        "ADD", "Alpha enzyme (EC 1.1.1.1)",
        {"field": "reactions", "entries": [{"value": "rxn00099", "extra": "q"}]},
        store,
    )
    assert any("not a known compartment" in e["message"] for e in errs)


def test_validate_add_subsystems_requires_extra(store):
    errs, _ = A.validate_payload(
        "ADD", "Alpha enzyme (EC 1.1.1.1)",
        {"field": "subsystems", "entries": [{"value": "S1", "extra": ""}]}, store,
    )
    assert any("Extra is required" in e["message"] for e in errs)


def test_validate_add_already_present_warns(store):
    errs, warns = A.validate_payload(
        "ADD", "Alpha enzyme (EC 1.1.1.1)",
        {"field": "reactions",
         "entries": [{"value": "rxn00001", "extra": "c"}]}, store,
    )
    assert errs == []
    assert any("already on this role" in w for w in warns)


def test_validate_reassign_bool_rejects_garbage(store):
    errs, _ = A.validate_payload(
        "REASSIGN", "Alpha enzyme (EC 1.1.1.1)",
        {"field": "include", "value": "maybe"}, store,
    )
    assert any("must be a boolean" in e["message"] for e in errs)


def test_validate_reassign_field_not_in_action_fields_rejected(store):
    errs, _ = A.validate_payload(
        "REASSIGN", "Alpha enzyme (EC 1.1.1.1)",
        {"field": "features", "value": "x"}, store,
    )
    assert any("is not valid" in e["message"] for e in errs)


def test_validate_deprecated_assign_alias_routes_and_warns(store):
    errs, warns = A.validate_payload(
        "ASSIGN", "Alpha enzyme (EC 1.1.1.1)",
        {"field": "type", "value": "conditional"}, store,
    )
    assert errs == []
    assert any("'ASSIGN' is deprecated" in w for w in warns)


def test_validate_deprecated_change_alias_routes_and_warns(store):
    errs, warns = A.validate_payload(
        "CHANGE", "Alpha enzyme (EC 1.1.1.1)",
        {"field": "abstract_enzyme", "value": "Alpha"}, store,
    )
    assert errs == []
    assert any("'CHANGE' is deprecated" in w for w in warns)


def test_validate_relocate_same_keys_error(store):
    errs, _ = A.validate_payload(
        "RELOCATE", "Alpha enzyme (EC 1.1.1.1)",
        {"field": "localization", "old": "c", "new": "c"}, store,
    )
    assert any("identical" in e["message"] for e in errs)


# ---------- build_tsv_rows ---------------------------------------------------
def test_build_new_row(store):
    rows, _, _ = A.build_tsv_rows("NEW", "Brand new enzyme", {}, store)
    assert rows == ["Brand new enzyme\tNEW"]


def test_build_add_features_with_and_without_extra(store):
    rows, errs, _ = A.build_tsv_rows(
        "ADD", "Alpha enzyme (EC 1.1.1.1)",
        {"field": "features",
         "entries": [
             {"value": "Athaliana_TAIR10||AT9G99999", "extra": "c:PPDB"},
             {"value": "Athaliana_TAIR10||AT9G99998", "extra": ""},
         ]}, store,
    )
    assert errs == []
    assert rows == [
        "Alpha enzyme (EC 1.1.1.1)\tADD\tfeatures\tAthaliana_TAIR10||AT9G99999\tc:PPDB",
        "Alpha enzyme (EC 1.1.1.1)\tADD\tfeatures\tAthaliana_TAIR10||AT9G99998",
    ]


def test_build_reassign_bool_coerces_value(store):
    rows, errs, _ = A.build_tsv_rows(
        "REASSIGN", "Alpha enzyme (EC 1.1.1.1)",
        {"field": "include", "value": "no"}, store,
    )
    assert errs == []
    assert rows == ["Alpha enzyme (EC 1.1.1.1)\tREASSIGN\tinclude\tFalse"]


def test_build_canonicalises_deprecated_alias_to_reassign(store):
    """Old verbs sent in by old code still produce canonical REASSIGN rows."""
    rows, errs, _ = A.build_tsv_rows(
        "ASSIGN", "Alpha enzyme (EC 1.1.1.1)",
        {"field": "type", "value": "conditional"}, store,
    )
    assert errs == []
    assert rows == ["Alpha enzyme (EC 1.1.1.1)\tREASSIGN\ttype\tconditional"]


def test_build_relocate(store):
    rows, errs, _ = A.build_tsv_rows(
        "RELOCATE", "Alpha enzyme (EC 1.1.1.1)",
        {"field": "localization", "old": "c", "new": "d"}, store,
    )
    assert errs == []
    assert rows == ["Alpha enzyme (EC 1.1.1.1)\tRELOCATE\tlocalization\tc\td"]


def test_build_update_renames(store):
    rows, errs, _ = A.build_tsv_rows(
        "UPDATE", "Alpha enzyme (EC 1.1.1.1)",
        {"new_name": "Alpha enzyme renamed"}, store,
    )
    assert errs == []
    assert rows == [
        "Alpha enzyme (EC 1.1.1.1)\tUPDATE\tAlpha enzyme renamed"
    ]


def test_build_returns_no_rows_when_validation_fails(store):
    rows, errs, _ = A.build_tsv_rows(
        "REASSIGN", "Alpha enzyme (EC 1.1.1.1)",
        {"field": "include", "value": "maybe"}, store,
    )
    assert rows == []
    assert errs


# ---------- parse_tsv_text ---------------------------------------------------
def test_parse_skips_comments_and_blank_lines():
    issues = IssueCollector()
    out = A.parse_tsv_text("# comment\n\nE\tNEW\n", issues=issues)
    assert out["new"] == ["E"]
    assert issues.warnings == []


def test_parse_warns_on_space_separated_line():
    issues = IssueCollector()
    A.parse_tsv_text("Some enzyme NEW\n", issues=issues)
    assert any("TAB-separated" in w for w in issues.warnings)


def test_parse_warns_on_unknown_action():
    issues = IssueCollector()
    A.parse_tsv_text("E\tFROBNICATE\n", issues=issues)
    assert any("unknown action" in w for w in issues.warnings)


def test_parse_warns_on_too_few_columns_for_action():
    issues = IssueCollector()
    A.parse_tsv_text("E\tADD\tfeatures\n", issues=issues)
    assert any("requires at least" in w for w in issues.warnings)


def test_parse_buckets_add_with_optional_extra():
    out = A.parse_tsv_text(
        "E\tADD\tfeatures\tF1\tc:PPDB\nE\tADD\tfeatures\tF2\n"
    )
    assert out["add"]["E"]["features"]["F1"] == "c:PPDB"
    assert out["add"]["E"]["features"]["F2"] == 1


def test_parse_warns_when_field_not_in_schema(tmp_db):
    from plantseed_curation.schema import load_schema
    issues = IssueCollector()
    A.parse_tsv_text("E\tADD\tnonsense_field\tX\n",
                     schema=load_schema(), issues=issues)
    assert any("not in the schema" in w for w in issues.warnings)


def test_parse_routes_deprecated_aliases_into_reassign_bucket():
    """ASSIGN and CHANGE rows land in the same reassign bucket as REASSIGN."""
    out = A.parse_tsv_text(
        "E\tASSIGN\ttype\tconditional\n"
        "F\tCHANGE\tabstract_enzyme\tFoo\n"
        "G\tREASSIGN\tinclude\tTrue\n"
    )
    assert out["reassign"]["E"]["type"] == "conditional"
    assert out["reassign"]["F"]["abstract_enzyme"] == "Foo"
    assert out["reassign"]["G"]["include"] == "True"


def test_parse_emits_one_warning_per_deprecated_alias_with_count():
    issues = IssueCollector()
    A.parse_tsv_text(
        "E\tASSIGN\ttype\tconditional\n"
        "F\tASSIGN\tinclude\tFalse\n"
        "G\tCHANGE\tabstract_enzyme\tFoo\n",
        issues=issues,
    )
    assign_warns = [w for w in issues.warnings if "'ASSIGN' is deprecated" in w]
    change_warns = [w for w in issues.warnings if "'CHANGE' is deprecated" in w]
    assert len(assign_warns) == 1 and "2 occurrence" in assign_warns[0]
    assert len(change_warns) == 1 and "1 occurrence" in change_warns[0]


# ---------- ADD ignores cascade-only fields ---------------------------------
def test_validate_rejects_add_localization(store):
    """Bug fix #2: localization is cascade-only; the menu must reject it."""
    errs, _ = A.validate_payload(
        "ADD", "Alpha enzyme (EC 1.1.1.1)",
        {"field": "localization",
         "entries": [{"value": "c", "extra": ""}]}, store,
    )
    assert any(e["field"] == "field" and "not valid" in e["message"] for e in errs)
