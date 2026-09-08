"""The v2.5 gate: does today's code still produce the v2.5 annotations?

`v2.5` is a tag — commit 212b817 — cut as the PlantSEED snapshot for the
BioFlux preprint, and `Papers/bioflux-preprint-260807/` holds what it
published. The refactor moved the annotator into a package and changed it (the
AMB_HIT role-set merge), so "the same code" is exactly the thing that needs
proving rather than assuming.

`Model/tests/test_golden_reconstruction.py` already covers the second half:
committed genome -> committed model. But those genomes are its *inputs*. This
covers the first half — proteomes and curation -> genome — which is the half
that actually changed.

Driven through `cli.main` rather than the library, because the gate was
phrased in terms of the CLI and because the CLI is what resolves defaults,
thresholds and the PSI cache. Every parameter comes from the run's own
`provenance.json`; nothing here restates a number the artifacts do not.

Cost: the first species computes PSI for ~785 orthogroups (about 25s at full
width). The other two reuse that cache, since it is keyed on the OrthoFinder
run. Marked `slow` so an ordinary `pytest` stays fast; CI runs it.
"""

import json
import os

import pytest

from plantseed_annotation import cli

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, "..", "..", "..", ".."))
_PAPER = os.path.join(_REPO, "Papers", "bioflux-preprint-260807")
_PROVENANCE = os.path.join(_PAPER, "provenance.json")


def _provenance():
    with open(_PROVENANCE) as fh:
        return json.load(fh)


def _reference_run():
    """The OrthoFinder run the published artifacts were produced from.

    Recorded in provenance rather than hardcoded: if the run moves, the
    artifacts say where to, and this skips instead of failing misleadingly.
    """
    if not os.path.isfile(_PROVENANCE):
        return None
    path = _provenance().get("orthofinder_results")
    return path if path and os.path.isdir(path) else None


REFERENCE_RUN = _reference_run()
SPECIES = sorted(_provenance()["per_genome"]) if os.path.isfile(_PROVENANCE) else []

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        REFERENCE_RUN is None,
        reason="the OrthoFinder run named in provenance.json is not on this host"),
]


@pytest.fixture(scope="module")
def annotated(tmp_path_factory):
    """Annotate every published species once, through the CLI.

    Module-scoped: the three runs share one PSI cache, so doing this per test
    would triple the cost for no extra coverage.
    """
    out_dir = tmp_path_factory.mktemp("v25")
    prov = _provenance()
    results = {}
    for species, recorded in prov["per_genome"].items():
        dest = out_dir / f"{species}.json"
        argv = [
            "--orthofinder-results", REFERENCE_RUN,
            "--query-species", species,
            "--ref-species", recorded["ref_species"],
            "--phylum", recorded["phylum"],
            "--out", str(dest),
            "--fallback-baseline", str(prov["annotator_flags"]["fallback_baseline"]),
            "--quiet",
        ]
        if not prov["annotator_flags"]["admit_paralogs"]:
            argv.append("--no-admit-paralogs")
        assert cli.main(argv) == 0, species
        with open(dest) as fh:
            results[species] = json.load(fh)
    return results


def _published(species):
    with open(os.path.join(_PAPER, f"{species}_annotated_genome.json")) as fh:
        return json.load(fh)


def _by_id(genome):
    """{feature id: sorted functions}. Order within `functions` is not part of
    the contract; membership is."""
    return {f["id"]: tuple(sorted(f["functions"])) for f in genome["features"]}


def test_every_published_species_was_annotated(annotated):
    """A rename that emptied this would make every test below vacuous."""
    assert sorted(annotated) == SPECIES and SPECIES


@pytest.mark.parametrize("species", SPECIES)
def test_the_feature_set_is_unchanged(species, annotated):
    got, want = _by_id(annotated[species]), _by_id(_published(species))
    missing, extra = sorted(set(want) - set(got)), sorted(set(got) - set(want))
    assert not missing, f"{species}: {len(missing)} lost, e.g. {missing[:5]}"
    assert not extra, f"{species}: {len(extra)} new, e.g. {extra[:5]}"


@pytest.mark.parametrize("species", SPECIES)
def test_every_function_string_is_unchanged(species, annotated):
    """The `role # compartment` string is the contract plant_fba consumes, so
    a changed compartment is a changed model even when the gene set matches."""
    got, want = _by_id(annotated[species]), _by_id(_published(species))
    differing = {k: (got[k], want[k]) for k in set(got) & set(want)
                 if got[k] != want[k]}
    assert not differing, (
        f"{species}: {len(differing)} features changed function; "
        f"first: {list(differing.items())[:2]}")


@pytest.mark.parametrize("species", SPECIES)
def test_the_status_counts_match_provenance(species, annotated):
    """ANNOTATED / NO_ORTHOLOG / AMB_HIT / MERGED_COMPARTMENTS. These move
    before the feature set does when a threshold or a tie-break shifts."""
    recorded = _provenance()["per_genome"][species]["status_counts"]
    assert annotated[species]["metadata"]["status_counts"] == recorded


@pytest.mark.parametrize("species", SPECIES)
def test_the_pair_level_tags_match_provenance(species, annotated):
    """O / PAM / PAH — the ortholog-vs-paralog classification underneath the
    annotations. The most sensitive number here: it moves if the PSI baseline
    moves at all."""
    recorded = _provenance()["per_genome"][species]["pair_stats"]
    if recorded is None:                     # self-annotation has no pairs
        pytest.skip(f"{species} is the reference species")
    assert annotated[species]["metadata"]["pair_stats"] == recorded


@pytest.mark.parametrize("species", SPECIES)
def test_the_annotated_count_matches_provenance(species, annotated):
    recorded = _provenance()["per_genome"][species]
    meta = annotated[species]["metadata"]
    assert meta["n_annotated_features"] == recorded["n_annotated_features"]
    assert meta["n_curated_ref_features"] == recorded["n_curated_ref_features"]
