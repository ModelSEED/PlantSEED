"""Curation-time rejection of role names carrying reserved delimiters.

The failure this prevents is invisible: a role containing " / ", " # " or "; "
raises nothing downstream, it just splits into fragments that match no template
role, and the reaction associations vanish. Nothing in the annotator, the
reconstructor or KBase complains. So the check has to live where a human is
still in the loop — validate_payload, which both Curation_Tool.py and the
dashboard funnel through.
"""

import pytest

from plantseed_curation.actions import validate_payload


class _Store:
    """Minimal DataStore stand-in — validate_payload only reads role_index."""

    def __init__(self, roles=()):
        self.role_index = {r: {} for r in roles}


def _errors_for(action, enzyme, payload=None, roles=()):
    errors, _ = validate_payload(action, enzyme, payload or {}, _Store(roles))
    return errors


def _fields(errors):
    return {e["field"] for e in errors}


class TestNew:
    def test_clean_name_accepted(self):
        assert _errors_for("NEW", "Hexokinase (EC 2.7.1.1)") == []

    def test_semicolon_space_rejected(self):
        errs = _errors_for(
            "NEW", "NAD transport (of mitochondrial carrier family; TC 2.A.29.10.10)")
        assert _fields(errs) == {"enzyme"}
        assert "; " in errs[0]["message"]

    def test_role_separator_rejected(self):
        assert _fields(_errors_for("NEW", "alpha / beta subunit")) == {"enzyme"}

    def test_compartment_separator_rejected(self):
        assert _fields(_errors_for("NEW", "kinase # cytosol")) == {"enzyme"}

    def test_message_suggests_a_fix(self):
        errs = _errors_for("NEW", "a; b")
        assert "comma" in errs[0]["message"]

    def test_bare_semicolon_without_space_is_allowed(self):
        # GenomeInterface splits on the literal "; " — "a;b" is not affected
        assert _errors_for("NEW", "carrier family;TC 2.A.29") == []

    def test_bare_slash_is_allowed(self):
        assert _errors_for("NEW", "cis/trans isomerase") == []

    def test_hash_without_spaces_is_allowed(self):
        assert _errors_for("NEW", "protein#3") == []

    def test_multiple_delimiters_all_reported(self):
        errs = _errors_for("NEW", "a; b / c")
        assert len(errs) == 2

    def test_delimiter_error_coexists_with_duplicate_error(self):
        errs = _errors_for("NEW", "a; b", roles=["a; b"])
        assert len(errs) == 2
        assert any("already exists" in e["message"] for e in errs)


class TestUpdate:
    def test_clean_rename_accepted(self):
        assert _errors_for("UPDATE", "old", {"new_name": "new"}, roles=["old"]) == []

    def test_rename_into_a_delimiter_rejected(self):
        errs = _errors_for("UPDATE", "old", {"new_name": "a; b"}, roles=["old"])
        assert _fields(errs) == {"new_name"}

    def test_empty_new_name_still_reports_the_original_error(self):
        errs = _errors_for("UPDATE", "old", {"new_name": ""}, roles=["old"])
        assert _fields(errs) == {"new_name"}
        assert "required" in errs[0]["message"]

    def test_delimiter_check_precedes_the_identical_name_warning(self):
        # a dirty new_name is an error, not merely a no-op rename
        errs = _errors_for("UPDATE", "a; b", {"new_name": "a; b"}, roles=["a; b"])
        assert _fields(errs) == {"new_name"}


class TestRegressionAgainstTheKnownOffender:
    def test_ps_role_41ed72_text_would_be_rejected_today(self):
        """The one existing offender could not be entered under the new check.

        Its presence in the curated file predates this validation; this pins
        that the door is now shut behind it.
        """
        text = ("NAD and other nucleotides transport "
                "(of mitochondrial carrier family; TC 2.A.29.10.10)")
        assert _errors_for("NEW", text) != []

    def test_the_comma_form_is_accepted(self):
        """The suggested remediation actually passes."""
        text = ("NAD and other nucleotides transport "
                "(of mitochondrial carrier family, TC 2.A.29.10.10)")
        assert _errors_for("NEW", text) == []
