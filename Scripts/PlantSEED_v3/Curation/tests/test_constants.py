"""Sanity checks on the constants table — invariants that, if broken, would
silently corrupt TSV rows."""

from plantseed_curation import constants as C


def test_action_options_match_descriptions_and_fields():
    for action in C.ACTION_OPTIONS:
        assert action in C.ACTION_DESCRIPTIONS
        # NEW, UPDATE and DELETE operate on the whole entry, not one field.
        if action not in ("NEW", "UPDATE", "DELETE"):
            assert action in C.ACTION_FIELDS
            assert C.ACTION_FIELDS[action], f"{action} has no fields"


def test_action_min_cols_covers_every_action():
    for action in C.ACTION_OPTIONS:
        assert action in C.ACTION_MIN_COLS


def test_compartment_letters_unique():
    letters = [c for c, _ in C.COMPARTMENTS]
    assert len(letters) == len(set(letters))
    assert all(len(c) == 1 for c in letters)


def test_default_compartment_is_in_set():
    assert C.DEFAULT_COMPARTMENT in C.COMPARTMENT_IDS


def test_localization_classes_not_in_add_fields():
    """Bug fix #2: ADD on dict-typed cascaded fields was breaking initialisation."""
    assert "localization" not in C.ACTION_FIELDS["ADD"]
    assert "classes" not in C.ACTION_FIELDS["ADD"]


def test_coerce_bool_str_round_trip():
    assert C.coerce_bool_str("true") == "True"
    assert C.coerce_bool_str("YES") == "True"
    assert C.coerce_bool_str("0") == "False"
    assert C.coerce_bool_str("nope") is None


def test_delete_actions_registered():
    assert "DELETE" in C.ACTION_OPTIONS
    assert "CPX_DELETE" in C.CPX_ACTION_OPTIONS
    assert C.ACTION_MIN_COLS["DELETE"] == 2
    assert C.CPX_ACTION_MIN_COLS["CPX_DELETE"] == 2
    assert "DELETE" in C.ACTION_DESCRIPTIONS
    assert "CPX_DELETE" in C.CPX_ACTION_DESCRIPTIONS
