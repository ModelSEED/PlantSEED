"""Tests for the function-string contract.

The round-trip tests matter more than they look: compose lives in
plantseed_core but the parse it must agree with lives in
plantseed_model.reconstruct, and the two were written years apart. These pin
the agreement so a change to either side fails here rather than silently
producing a model with missing GPRs.
"""

import json
import os

import pytest

from plantseed_core import strings
from plantseed_core.errors import ReservedDelimiterError

# The mapping the annotator actually uses, abridged to the cases under test.
CPT = {"c": "cytosol", "d": "plastid", "dy": "thylakoid", "m": "mitochondria"}


class TestCompose:
    def test_single_role_no_compartment(self):
        assert strings.compose_function_string(["Hexokinase (EC 2.7.1.1)"]) == \
            "Hexokinase (EC 2.7.1.1)"

    def test_roles_joined_with_slash(self):
        assert strings.compose_function_string(["role A", "role B"]) == "role A / role B"

    def test_compartments_appended(self):
        got = strings.compose_function_string(["role A"], ["c", "d"], mapping=CPT)
        assert got == "role A # cytosol # plastid"

    def test_compartments_as_names_when_no_mapping(self):
        assert strings.compose_function_string(["r"], ["cytosol"]) == "r # cytosol"

    def test_unknown_compartment_dropped_silently(self):
        got = strings.compose_function_string(["r"], ["c", "zzz"], mapping=CPT,
                                              on_unknown="drop")
        assert got == "r # cytosol"

    def test_unknown_compartment_can_raise(self):
        with pytest.raises(KeyError):
            strings.compose_function_string(["r"], ["zzz"], mapping=CPT,
                                            on_unknown="raise")

    def test_all_compartments_unknown_yields_bare_roles(self):
        got = strings.compose_function_string(["r"], ["zzz"], mapping=CPT,
                                              on_unknown="drop")
        assert got == "r"

    def test_reserved_delimiter_in_role_is_refused(self):
        bad = "NAD transport (of mitochondrial carrier family; TC 2.A.29.10.10)"
        with pytest.raises(ReservedDelimiterError) as exc:
            strings.compose_function_string([bad])
        assert "; " in str(exc.value)

    def test_check_can_be_disabled_for_legacy_data(self):
        bad = "a; b"
        assert strings.compose_function_string([bad], check=False) == bad


class TestGuards:
    def test_clean_role_passes_through(self):
        r = "Hexokinase (EC 2.7.1.1)"
        assert strings.assert_kbase_safe(r) is r

    @pytest.mark.parametrize("bad", ["a; b", "a / b", "a # b"])
    def test_each_reserved_delimiter_is_caught(self, bad):
        with pytest.raises(ReservedDelimiterError):
            strings.assert_kbase_safe(bad)

    def test_find_reserved_is_non_raising_and_reports_all(self):
        hits = strings.find_reserved("a; b / c")
        assert {d for d, _ in hits} == {"; ", " / "}

    def test_find_reserved_empty_for_clean(self):
        assert strings.find_reserved("Hexokinase (EC 2.7.1.1)") == []

    def test_context_appears_in_message(self):
        with pytest.raises(ReservedDelimiterError) as exc:
            strings.assert_kbase_safe("a; b", context="PS_role_41ed72")
        assert "PS_role_41ed72" in str(exc.value)

    def test_bare_slash_is_allowed(self):
        # only a whitespace-flanked slash separates roles, so cis/trans is fine
        strings.assert_kbase_safe("cis/trans isomerase")


class TestParse:
    def test_roundtrip_roles_only(self):
        roles = ["role A", "role B"]
        s = strings.compose_function_string(roles)
        assert strings.parse_function_string(s) == (roles, [])

    def test_roundtrip_with_compartments(self):
        s = strings.compose_function_string(["role A", "role B"], ["c", "dy"], mapping=CPT)
        assert strings.parse_function_string(s) == (
            ["role A", "role B"], ["cytosol", "thylakoid"])

    def test_tolerates_irregular_spacing_like_reconstruct_does(self):
        assert strings.parse_function_string("a  /  b #cytosol#plastid") == (
            ["a", "b"], ["cytosol", "plastid"])

    def test_bare_slash_survives_parse(self):
        assert strings.parse_function_string("cis/trans isomerase") == (
            ["cis/trans isomerase"], [])

    def test_unannotated_sentinel(self):
        assert strings.parse_function_string("Unannotated") == (["Unannotated"], [])

    def test_empty(self):
        assert strings.parse_function_string("") == ([], [])


_ROLES_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..", "Data", "PlantSEED_v3", "PlantSEED_Roles.json",
)


@pytest.mark.skipif(not os.path.isfile(_ROLES_JSON),
                    reason="curated roles file not present (installed wheel)")
class TestAgainstCuratedData:
    """The CI gate: no curated role may carry a reserved delimiter.

    Currently one does — PS_role_41ed72 — so this is xfail rather than fail
    until that curation decision is made. Flip to a hard assert once it is
    resolved; the point is that the next one gets caught on the way in.
    """

    @staticmethod
    def _roles():
        with open(_ROLES_JSON) as fh:
            return json.load(fh)

    def test_roles_file_parses_and_is_nonempty(self):
        assert len(self._roles()) > 500

    @pytest.mark.xfail(strict=True, reason="PS_role_41ed72 contains '; ' — pending curation")
    def test_no_curated_role_contains_a_reserved_delimiter(self):
        offenders = [
            (r.get("kbase_id"), d, r["role"])
            for r in self._roles()
            for d, _ in strings.find_reserved(r["role"])
        ]
        assert offenders == [], f"{len(offenders)} role(s) carry reserved delimiters: {offenders}"

    def test_the_only_known_offender_is_the_expected_one(self):
        """Pins the blast radius: if a second role acquires a delimiter, this fails."""
        offenders = {
            r.get("kbase_id")
            for r in self._roles()
            if strings.find_reserved(r["role"])
        }
        assert offenders == {"PS_role_41ed72"}, f"unexpected offenders: {offenders}"

    def test_every_other_role_composes_cleanly(self):
        for r in self._roles():
            if r.get("kbase_id") == "PS_role_41ed72":
                continue
            strings.compose_function_string([r["role"]])
