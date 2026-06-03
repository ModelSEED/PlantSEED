"""Search ranking — name / field-prefix / by-feature modes."""

from plantseed_curation import search as S


def test_parse_query_recognises_field_prefix():
    assert S.parse_query("rxn:rxn00001") == ("field", "rxn", "rxn00001")
    assert S.parse_query("alpha") == ("name", None, "alpha")
    assert S.parse_query("unknownprefix:value") == ("name", None, "unknownprefix:value")


def test_fuzzy_match_is_substring():
    assert S.fuzzy_match("AlpHa", ["Alpha enzyme", "Beta", "ALPHABET"]) == [
        "Alpha enzyme",
        "ALPHABET",
    ]


def test_find_exact_match_skips_exclude(store):
    matches = S.find_exact_match(store.roles, "reactions", "rxn00001")
    assert matches == ["Alpha enzyme (EC 1.1.1.1)"]
    assert S.find_exact_match(store.roles, "reactions", "rxn00001",
                              exclude="Alpha enzyme (EC 1.1.1.1)") == []


def test_find_substring_match_features(store):
    # "AT2G" appears on Beta only.
    out = S.find_substring_match(store.roles, "features", "AT2G")
    assert "Beta enzyme (EC 2.2.2.2)" in out
    assert "Alpha enzyme (EC 1.1.1.1)" not in out


def test_ranked_search_name_mode(store):
    res = S.ranked_search(store, "Alpha")
    assert res["mode"] == "name"
    assert "Alpha enzyme (EC 1.1.1.1)" in res["name"]


def test_ranked_search_by_feature(store):
    # Plain text query — by_feature should surface roles whose features
    # contain the substring, while name matches stay empty.
    res = S.ranked_search(store, "AT2G00020")
    assert res["name"] == []
    feature_roles = [d["role"] for d in res["by_feature"]]
    assert "Beta enzyme (EC 2.2.2.2)" in feature_roles


def test_ranked_search_field_prefix_rxn(store):
    res = S.ranked_search(store, "rxn:rxn00003")
    assert res["mode"] == "field" and res["field"] == "rxn"
    assert "Gamma transporter (EC 3.3.3.3)" in res["name"]


def test_ranked_search_short_query_returns_empty(store):
    res = S.ranked_search(store, "a")
    assert res["name"] == [] and res["expasy"] == [] and res["by_feature"] == []
