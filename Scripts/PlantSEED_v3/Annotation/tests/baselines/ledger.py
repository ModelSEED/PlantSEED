"""Reading the divergence ledger and folding it over the frozen v2.5 baseline.

Deliberately free of pytest and of anything else the test harness needs, so
`record_divergence.py` can be run as an ordinary script by whoever is making a
change, without a test environment. `test_divergence_ledger.py` imports the
same functions, so the gate and the recorder can never disagree about what the
expected state is.

The baseline itself is `Papers/bioflux-preprint-260807/` and is immutable.
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_TESTS = os.path.dirname(_HERE)
REPO = os.path.normpath(os.path.join(_TESTS, "..", "..", "..", ".."))
PAPER = os.path.join(REPO, "Papers", "bioflux-preprint-260807")
PROVENANCE = os.path.join(PAPER, "provenance.json")
LEDGER = os.path.join(_HERE, "divergences.jsonl")


def provenance():
    with open(PROVENANCE) as fh:
        return json.load(fh)


def reference_run():
    """Path to the OrthoFinder run the published artifacts came from, or None
    if this host does not have it."""
    if not os.path.isfile(PROVENANCE):
        return None
    path = provenance().get("orthofinder_results")
    return path if path and os.path.isdir(path) else None


def species_list():
    return sorted(provenance()["per_genome"]) if os.path.isfile(PROVENANCE) else []


def by_id(genome):
    """{feature id: function string}, skipping unannotated features.

    Functions are sorted and joined because order within a feature's
    `functions` list is not part of the contract.
    """
    return {f["id"]: " | ".join(sorted(f.get("functions") or []))
            for f in genome["features"] if f.get("functions")}


def published(species):
    with open(os.path.join(PAPER, f"{species}_annotated_genome.json")) as fh:
        return by_id(json.load(fh))


def load_ledger(path=LEDGER):
    """The divergence records, in the order they were applied."""
    if not os.path.isfile(path):
        return []
    with open(path) as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def expected_functions(base, entries, species):
    """Fold the ledger over one species' published annotations.

    `base` and the return are both {feature_id: function_string}. Entries
    apply in file order, so a later record can legitimately restore something
    an earlier one removed.

    An id recorded only as `gained` maps to None: the ledger pins that the
    feature should now be annotated, not what its text should say. Pinning the
    text would make every unrelated curation edit fail the gate.
    """
    state = dict(base)
    for entry in entries:
        delta = entry.get("deltas", {}).get(species)
        if not delta:
            continue
        for fid in delta.get("lost", ()):
            state.pop(fid, None)
        for fid, fn in (delta.get("changed") or {}).items():
            state[fid] = fn
        for fid in delta.get("gained", ()):
            state.setdefault(fid, None)
    return state


def annotate_all(run, cli):
    """Annotate every published species through the CLI, exactly as the v2.5
    gate does — every parameter comes from the run's own provenance.json, so a
    difference between gates is never a difference in invocation.

    `cli` is passed in rather than imported so this module stays import-light.
    Returns {species: {feature id: function string}}.
    """
    import tempfile
    prov = provenance()
    out = {}
    with tempfile.TemporaryDirectory() as td:
        for species, rec in sorted(prov["per_genome"].items()):
            dest = os.path.join(td, species + ".json")
            argv = ["--orthofinder-results", run,
                    "--query-species", species,
                    "--ref-species", rec["ref_species"],
                    "--phylum", rec["phylum"],
                    "--out", dest,
                    "--fallback-baseline",
                    str(prov["annotator_flags"]["fallback_baseline"]),
                    "--quiet"]
            if not prov["annotator_flags"]["admit_paralogs"]:
                argv.append("--no-admit-paralogs")
            if cli.main(argv) != 0:
                raise RuntimeError(f"annotation failed for {species}")
            with open(dest) as fh:
                out[species] = by_id(json.load(fh))
    return out


def diff(want, observed):
    """(lost, gained, changed) between an expected and an observed
    {id: function} map. `changed` carries the observed strings, and skips ids
    the ledger pinned by membership only (value None)."""
    lost = sorted(set(want) - set(observed))
    gained = sorted(set(observed) - set(want))
    changed = {f: observed[f] for f in sorted(set(want) & set(observed))
               if want[f] is not None and want[f] != observed[f]}
    return lost, gained, changed
