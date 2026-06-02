"""Schema loader + default fillers + dependency validator."""

from plantseed_curation import schema as S


def test_load_schema_normalizes_types(tmp_db):
    sch = S.load_schema()
    assert sch["features"]["type"] is list
    assert sch["localization"]["type"] is dict
    assert sch["include"]["type"] is bool
    assert sch["role"]["required"] is True
    assert sch["publications"]["required"] is False


def test_default_role_from_schema_only_required(tmp_db):
    sch = S.load_schema()
    default = S.default_role_from_schema(sch)
    assert default["role"] == ""
    assert default["features"] == []
    assert default["localization"] == {}
    # Optional fields should NOT be seeded.
    assert "publications" not in default
    assert "kbase_id" not in default


def test_required_empty_fields(tmp_db):
    sch = S.load_schema()
    skeleton = S.default_role_from_schema(sch)
    skeleton["role"] = "newrole"
    empties = S.required_empty_fields(skeleton, sch)
    # role/include/type/is_transporter/curators are auto-populated;
    # the rest should be reported as empty.
    assert "features" in empties
    assert "subsystems" in empties
    assert "classes" in empties
    assert "localization" in empties
    assert "reactions" in empties
    assert "abstract_enzyme" in empties
    assert "role" not in empties


def test_ensure_schema_defaults_fills_missing(tmp_db):
    sch = S.load_schema()
    entry = {"role": "x"}
    msgs = S.ensure_schema_defaults(entry, sch)
    assert any("'include'" in m for m in msgs)
    assert entry["include"] is True
    assert entry["features"] == []


def test_issue_collector_buckets():
    ic = S.IssueCollector()
    ic.warn("w"); ic.error("e"); ic.log("l")
    assert ic.warnings == ["w"] and ic.errors == ["e"] and ic.info == ["l"]
