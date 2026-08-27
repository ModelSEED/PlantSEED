"""The read-only curation lookups.

These run against the real `Data/PlantSEED_v3/` files rather than a fixture:
the point of the tools is what the curation actually contains, and a synthetic
role set would pass while telling an agent nothing true.
"""

import pytest

from plantseed_delivery import queries


class TestOrientation:
    def test_list_subsystems_is_the_vocabulary(self):
        out = queries.list_subsystems()
        assert out["n_roles"] > 900
        assert "Calvin-Benson-Bassham_cycle" in out["subsystems"]
        assert out["types"] and out["curators"]


class TestSearch:
    def test_plain_text_finds_a_role(self):
        out = queries.search_roles("peroxidase")
        assert out["n_matched"] >= 1
        assert any("eroxidase" in r["role"] for r in out["roles"])

    def test_field_prefixes_are_honoured(self):
        """`subsystem:` and friends come from plantseed_curation.search — the
        reason to call it rather than write another matcher."""
        out = queries.search_roles("subsystem:Calvin")
        assert out["mode"] == "field"
        assert out["n_matched"] > 1

    def test_a_gene_id_matches_by_feature(self):
        """Otherwise the answer to "does PlantSEED know this gene?" is a
        misleading zero: gene ids live in features, not in role names."""
        out = queries.search_roles("AT2G41480")
        assert out["n_matched"] == 0
        assert out["matched_by_feature"][0]["feature"].endswith("AT2G41480")

    def test_limit_is_respected(self):
        assert len(queries.search_roles("a", limit=3)["roles"]) <= 3

    def test_empty_query_is_an_error_not_an_exception(self):
        assert "error" in queries.search_roles("  ")

    def test_expasy_is_never_fetched(self):
        """A tool that downloads mid-run is rejected at CTS image review, and
        makes two identical calls return different answers."""
        queries.search_roles("peroxidase")
        assert queries._store().expasy_status()["status"] == "idle"


class TestGetRole:
    def test_by_name(self):
        out = queries.get_role("Peroxidase (EC 1.11.1.7)")
        assert out["id"].startswith("PS_role_")
        assert out["n_features"] > 0

    def test_by_stable_id(self):
        """The `PS_role_*` id is the identity that survives a rename."""
        out = queries.get_role("PS_role_1cc588")
        assert out["reactions"] == ["rxn18937"]
        assert out["compartments"] == ["d"]

    def test_features_are_opt_in(self):
        name = "Peroxidase (EC 1.11.1.7)"
        assert "features" not in queries.get_role(name)
        assert queries.get_role(name, include_features=True)["features"]

    def test_missing_role_is_an_error(self):
        assert "error" in queries.get_role("no such role")


class TestSubsystemReactions:
    def test_reactions_carry_their_curated_compartments(self):
        """The compartment assignment is the guarantee — a text search over
        role names cannot reproduce it."""
        out = queries.subsystem_reactions("Calvin-Benson-Bassham_cycle")
        assert out["n_roles"] > 1
        assert out["reactions"]
        assert any(cpts for cpts in out["reactions"].values())

    def test_unknown_subsystem_points_at_the_vocabulary(self):
        out = queries.subsystem_reactions("Photosynthesis")   # plausible, absent
        assert "error" in out and "list_subsystems" in out["hint"]


class TestComplexes:
    def test_by_stable_id(self):
        out = queries.get_complex("PS_complex_be6254")
        assert out["roles"] and out["compartments_reactions"]

    def test_by_enzyme_name_case_insensitively(self):
        by_id = queries.get_complex("PS_complex_be6254")
        assert queries.get_complex(by_id["enzyme"].upper()) == by_id

    def test_missing_complex_is_an_error(self):
        assert "error" in queries.get_complex("PS_complex_nope")


def test_nothing_here_writes(tmp_path, monkeypatch):
    """A read-only tool that writes is a tool that fails on a read-only mount."""
    monkeypatch.chdir(tmp_path)
    queries.list_subsystems()
    queries.search_roles("peroxidase")
    queries.get_role("PS_role_1cc588")
    queries.get_complex("PS_complex_be6254")
    assert not list(tmp_path.iterdir())
