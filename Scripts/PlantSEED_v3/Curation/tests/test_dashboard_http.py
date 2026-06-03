"""End-to-end dashboard tests. Spin up the HTTP server in a thread and
hit it via urllib — proves the API contract matches what build_tsv_rows
and run_apply produce when called directly."""

import json


def test_status_endpoint_reports_loaded_roles(http_client):
    code, body = http_client("GET", "/api/status")
    assert code == 200
    assert body["roles"] == 3  # mini_roles.json
    assert "role" in body["schema_keys"]


def test_search_endpoint_returns_name_matches(http_client):
    code, body = http_client("GET", "/api/search?q=Alpha")
    assert code == 200
    assert "Alpha enzyme (EC 1.1.1.1)" in body["name"]


def test_role_endpoint_returns_known_role(http_client):
    code, body = http_client("GET", "/api/role?name=Alpha%20enzyme%20%28EC%201.1.1.1%29")
    assert code == 200
    assert body["exists"] is True
    assert body["entry"]["abstract_enzyme"] == "Alpha enzyme"


def test_role_endpoint_missing_role(http_client):
    code, body = http_client("GET", "/api/role?name=Not%20a%20real%20enzyme")
    assert body["exists"] is False


def test_build_endpoint_returns_rows(http_client):
    code, body = http_client("POST", "/api/build", {
        "action": "ADD",
        "enzyme": "Alpha enzyme (EC 1.1.1.1)",
        "payload": {
            "field": "features",
            "entries": [
                {"value": "Athaliana_TAIR10||ATXX1", "extra": "c:PPDB"},
            ],
        },
    })
    assert code == 200
    assert body["rows"] == [
        "Alpha enzyme (EC 1.1.1.1)\tADD\tfeatures\tAthaliana_TAIR10||ATXX1\tc:PPDB"
    ]
    assert body["errors"] == []


def test_validate_endpoint_flags_missing_extra(http_client):
    code, body = http_client("POST", "/api/validate", {
        "action": "ADD",
        "enzyme": "Alpha enzyme (EC 1.1.1.1)",
        "payload": {
            "field": "subsystems",
            "entries": [{"value": "S1", "extra": ""}],
        },
    })
    assert body["ok"] is False
    assert any("Extra is required" in e["message"] for e in body["errors"])


def test_apply_dry_run_then_real(http_client):
    tsv = (
        "Alpha enzyme (EC 1.1.1.1)\tREASSIGN\ttype\tconditional\n"
    )
    code, dry = http_client("POST", "/api/apply",
                            {"user": "tester", "tsv": tsv, "dry_run": True})
    assert dry["summary"]["dry_run"] is True
    assert any("Dry run" in i for i in dry["info"])

    code, real = http_client("POST", "/api/apply",
                             {"user": "tester", "tsv": tsv, "dry_run": False})
    assert real["summary"]["dry_run"] is False
    assert "Alpha enzyme (EC 1.1.1.1)" in real["summary"]["touched"]


def test_file_create_save_append_delete_round_trip(http_client):
    # create
    code, body = http_client("POST", "/api/file/create",
                             {"user": "vibhav", "name": "via_api"})
    assert body["name"] == "via_api.tsv"
    # save full content
    http_client("POST", "/api/file/save",
                {"user": "vibhav", "name": "via_api.tsv", "content": "header line"})
    # append rows
    http_client("POST", "/api/file/append",
                {"user": "vibhav", "name": "via_api.tsv",
                 "rows": ["E\tNEW", "E\tREASSIGN\ttype\tconditional"]})
    # read back
    code, body = http_client("GET", "/api/file?user=vibhav&name=via_api.tsv")
    assert body["content"].endswith("E\tREASSIGN\ttype\tconditional\n")
    # list
    code, body = http_client("GET", "/api/files?user=vibhav")
    names = [f["name"] for f in body["files"]]
    assert "via_api.tsv" in names
    # delete
    code, body = http_client("POST", "/api/file/delete",
                             {"user": "vibhav", "name": "via_api.tsv"})
    assert code == 200


def test_action_meta_lists_compartments(http_client):
    code, body = http_client("GET", "/api/actions")
    ids = [c["id"] for c in body["compartments"]]
    assert "c" in ids and "d" in ids
    assert body["default_compartment"] == "c"


def test_preview_endpoint_shows_before_after(http_client):
    code, body = http_client("POST", "/api/preview", {
        "enzyme": "Alpha enzyme (EC 1.1.1.1)",
        "rows": ["Alpha enzyme (EC 1.1.1.1)\tREASSIGN\ttype\tconditional"],
    })
    assert body["before"]["type"] == "universal"
    assert body["after"]["type"] == "conditional"


def test_xref_finds_other_roles_using_feature(http_client):
    code, body = http_client(
        "GET", "/api/xref?field=features&value=Athaliana_TAIR10||AT2G00020&mode=exact"
    )
    assert "Beta enzyme (EC 2.2.2.2)" in body["matches"]
