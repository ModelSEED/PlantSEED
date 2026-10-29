"""The moving-target gate: v2.5 plus every divergence we meant to make.

`test_v25_reproduction.py` asks "is today's output identical to v2.5?". That
question stops being useful the moment a change is deliberate — it goes red and
stays red, and a red gate cannot catch the next regression. Regenerating the
v2.5 artifacts would fix the colour and destroy the baseline, which is the one
thing in this directory that must never move.

So the baseline stays frozen and the EXPECTATION becomes derived:

    expected = v2.5 artifacts + fold(baselines/divergences.jsonl)

Every intentional change appends one record to the ledger carrying the exact
feature ids it adds, removes, or rewrites, measured when the change was made.
The gate is still strict: an unrecorded change fails, because it shows up as
residual the ledger does not account for. What it no longer does is fail for
changes we already decided on.

The ledger doubles as the timeline of how far the annotator has drifted from
the published snapshot, and why.

Adding an entry: make the change, run
    tests/baselines/record_divergence.py --id <slug> --rationale "..."
and commit the appended line together with the code change. The recorder
measures the delta against the current ledger head, so entries compose in
order and each one is attributable on its own.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "baselines"))

from plantseed_annotation import cli
from ledger import (annotate_all, diff, expected_functions, load_ledger,
                    published, reference_run, species_list)


REFERENCE_RUN = reference_run()
SPECIES = species_list()

# Applied per-test rather than module-wide: test_the_ledger_is_well_formed
# needs neither the reference run nor 25s of PSI, and is most useful in the
# fast suite where it will actually be run.
needs_reference_run = [
    pytest.mark.slow,
    pytest.mark.skipif(
        REFERENCE_RUN is None,
        reason="the OrthoFinder run named in provenance.json is not on this host"),
]


def _heavy(fn):
    for mark in needs_reference_run:
        fn = mark(fn)
    return fn


@pytest.fixture(scope="module")
def annotated():
    """Annotate every published species once. Module-scoped: the three runs
    share one PSI cache, so doing this per test would triple the cost."""
    return annotate_all(REFERENCE_RUN, cli)


@_heavy
@pytest.mark.parametrize("species", SPECIES)
def test_the_feature_set_is_v25_plus_the_ledger(species, annotated):
    """Which features carry an annotation = v2.5's set, with every ledger
    entry's removals and additions applied. Residual either way is a change
    nobody recorded."""
    want = expected_functions(published(species), load_ledger(), species)
    lost, gained, _ = diff(want, annotated[species])
    assert not lost and not gained, (
        f"{species}: {len(lost)} features lost and {len(gained)} gained "
        f"beyond the ledger.\n"
        f"  lost:   {lost[:10]}\n"
        f"  gained: {gained[:10]}\n"
        f"Record the change with tests/baselines/record_divergence.py if it "
        f"was intended, otherwise it is a regression."
    )


@_heavy
@pytest.mark.parametrize("species", SPECIES)
def test_every_function_string_is_v25_plus_the_ledger(species, annotated):
    """Same for the function strings themselves."""
    want = expected_functions(published(species), load_ledger(), species)
    _, _, changed = diff(want, annotated[species])
    assert not changed, (
        f"{species}: {len(changed)} function strings differ from v2.5 + "
        f"ledger. First few: {dict(list(changed.items())[:3])}"
    )


def test_the_ledger_is_well_formed():
    """Cheap enough for the fast suite: every entry needs an id, a date, a
    rationale someone can act on, and at least one non-empty delta. An entry
    with no measured effect is a record of nothing."""
    entries = load_ledger()
    assert entries, "the ledger is empty; the v2.5 gate should be used instead"
    seen = set()
    for entry in entries:
        for field in ("id", "date", "rationale", "deltas"):
            assert entry.get(field), f"{entry.get('id', '?')}: missing {field}"
        assert entry["id"] not in seen, f"duplicate ledger id {entry['id']}"
        seen.add(entry["id"])
        assert len(entry["rationale"]) > 80, (
            f"{entry['id']}: rationale too short to explain the change to "
            f"someone who did not make it")
        assert any(d.get("lost") or d.get("gained") or d.get("changed")
                   for d in entry["deltas"].values()), \
            f"{entry['id']}: recorded no measured effect on any genome"
