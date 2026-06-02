"""Drive the CLI with a scripted input iterator. Asserts that the same
sequence of curator actions produces the same TSV rows the dashboard's
/api/build endpoint would produce — that's the cross-interface guarantee
that motivated extracting the library."""

import os

import pytest

import Curation_Tool as CT
from plantseed_curation.cli_io import Console, ExitRequested


class ScriptedInput:
    """Pop one answer per prompt; raise if the script runs out (means the
    test forgot an answer)."""

    def __init__(self, answers):
        self._iter = iter(answers)

    def __call__(self, prompt=""):
        try:
            return next(self._iter)
        except StopIteration:
            raise AssertionError(f"Scripted input exhausted at prompt: {prompt!r}")


def _make_console(answers, output_log):
    return Console(
        input_fn=ScriptedInput(answers),
        output_fn=output_log.append,
        exit_action=lambda: (_ for _ in ()).throw(ExitRequested()),
    )


def _run_cli(answers, store):
    output_log = []
    console = _make_console(answers, output_log)
    try:
        CT.run(console=console, store=store, skip_expasy=True)
    except ExitRequested:
        pass
    return output_log


# Each test overrides the detected GitHub username at the resolve-curator
# prompt so the per-curator directory is predictable regardless of the local
# git remote.
USER = "ciuser"


def test_cli_add_features_produces_expected_tsv(tmp_db, store):
    answers = [
        # resolve_curator
        USER,              # override detected GitHub username
        # get_target_file
        "out",             # filename (will become out.tsv)
        "y",               # confirm new file
        # outer enzyme loop -> select_enzyme
        "Alpha",           # search query
        "1",               # pick first PlantSEED match (Alpha enzyme...)
        # action loop
        "1",               # ADD (CLI_ACTION_MENU index 1 = ADD)
        "1",               # field menu: features
        "Athaliana_TAIR10||ATXX1",  # first entry value
        "c:PPDB",          # extra
        "",                # blank to finish entries
        # next-step menu
        "3",               # Done — exit
    ]
    _run_cli(answers, store)
    tsv_path = os.path.join(tmp_db["curators"], USER, "out.tsv")
    content = open(tsv_path).read()
    assert content == (
        "Alpha enzyme (EC 1.1.1.1)\tADD\tfeatures\tAthaliana_TAIR10||ATXX1\tc:PPDB\n"
    )


def test_cli_assign_bool_coerces(tmp_db, store):
    answers = [
        USER,              # override GH username
        "include_off",     # filename
        "y",
        "Alpha",           # search
        "1",               # pick Alpha
        "2",               # ASSIGN (CLI_ACTION_MENU index 2)
        "1",               # field include
        "no",              # value
        "3",               # Done
    ]
    _run_cli(answers, store)
    tsv_path = os.path.join(tmp_db["curators"], USER, "include_off.tsv")
    assert open(tsv_path).read() == "Alpha enzyme (EC 1.1.1.1)\tASSIGN\tinclude\tFalse\n"


def test_cli_new_enzyme_and_add_subsystem(tmp_db, store):
    answers = [
        USER,                # override GH user
        "novel_run",         # filename
        "y",
        "Brand new enzyme",  # search query (3+ chars; no matches expected)
        "n",                 # novel
        "Brand new enzyme",  # full novel name
        # The first action on a NEW enzyme is automatically NEW (no menu prompt)
        # Next-step menu after NEW:
        "1",                 # Another action on same enzyme
        "1",                 # ADD
        "4",                 # field subsystems (index 4 in ACTION_FIELDS["ADD"])
        "Novel_subsystem",   # value
        "Cofactors",         # extra (class) — required
        "",                  # blank to finish
        "3",                 # Done
    ]
    _run_cli(answers, store)
    tsv_path = os.path.join(tmp_db["curators"], USER, "novel_run.tsv")
    content = open(tsv_path).read()
    assert "Brand new enzyme\tNEW\n" in content
    assert "Brand new enzyme\tADD\tsubsystems\tNovel_subsystem\tCofactors\n" in content


def test_cli_exit_shortcut_aborts_cleanly(tmp_db, store):
    """!! at any prompt exits the CLI (raises ExitRequested via exit_action)."""
    answers = ["!!"]
    output_log = []
    console = _make_console(answers, output_log)
    with pytest.raises(ExitRequested):
        CT.run(console=console, store=store, skip_expasy=True)


def test_cli_and_dashboard_produce_identical_tsv(tmp_db, store, http_client):
    """The whole point of the refactor: same payload -> same row bytes."""
    # CLI path
    answers = [
        USER, "parity", "y",
        "Alpha", "1",
        "1", "1",                       # ADD features
        "Athaliana_TAIR10||ATXX9", "c:PPDB", "",
        "3",                            # Done
    ]
    _run_cli(answers, store)
    cli_tsv = open(os.path.join(tmp_db["curators"], USER, "parity.tsv")).read()

    # HTTP path - same payload, same enzyme.
    code, body = http_client("POST", "/api/build", {
        "action": "ADD",
        "enzyme": "Alpha enzyme (EC 1.1.1.1)",
        "payload": {
            "field": "features",
            "entries": [{"value": "Athaliana_TAIR10||ATXX9", "extra": "c:PPDB"}],
        },
    })
    http_tsv = body["rows"][0] + "\n"
    assert cli_tsv == http_tsv
