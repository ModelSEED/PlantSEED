"""Golden regression: the packaged engine must still reproduce the published models.

Papers/bioflux-preprint-260807/ holds the annotated genomes and the metabolic
models that went into the preprint. Reconstructing from the committed genomes
must yield the committed models. This is the single most valuable test in the
repo during the v3 refactor: it is the thing that lets the reconstruction
engine be moved, repackaged, and eventually merged with the KBase copy without
anyone having to trust that the science came through unchanged.

It also covers the conditional-spontaneous-reaction path, which the KBase copy
of this algorithm lacks entirely — Athaliana admits rxn22371_c0 through it. Any
merge that drops that logic fails here.

Skipped when Papers/ is absent, so an installed wheel does not fail.
"""

import json
import os

import pytest

from plantseed_model import ReconstructAppImpl

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, "..", "..", "..", ".."))
_PAPER = os.path.join(_REPO, "Papers", "bioflux-preprint-260807")
_TEMPLATE = os.path.join(_REPO, "Scripts", "PlantSEED_v3", "Template",
                         "PlantSEED_Biomass_Template.json")
_COMPARTMENTS = os.path.join(_REPO, "Data", "PlantSEED_v3", "Compartments",
                             "PlantSEED_Compartments.json")

SPECIES = ["Athaliana_TAIR10", "Sbicolor_v3.1.1", "Ptrichocarpa_v4.1"]

pytestmark = pytest.mark.skipif(
    not (os.path.isdir(_PAPER) and os.path.isfile(_TEMPLATE)
         and os.path.isfile(_COMPARTMENTS)),
    reason="preprint artifacts / template not present (installed wheel)",
)


def _load(path):
    with open(path) as fh:
        return json.load(fh)


def _rebuild(species):
    genome = _load(os.path.join(_PAPER, f"{species}_annotated_genome.json"))
    recon = ReconstructAppImpl()
    recon._set_objects({"genome": genome, "template": _load(_TEMPLATE)})
    return recon.reconstruct_metabolism(
        {"id": f"{species}_model", "name": f"{species}_model",
         "cpts": _load(_COMPARTMENTS)}
    )


@pytest.fixture(scope="module")
def rebuilt():
    return {sp: _rebuild(sp) for sp in SPECIES}


@pytest.fixture(scope="module")
def published():
    return {sp: _load(os.path.join(_PAPER, f"{sp}_model.json")) for sp in SPECIES}


def _ids(model, key):
    return {x["id"] for x in model.get(key, [])}


@pytest.mark.parametrize("species", SPECIES)
def test_reaction_set_is_unchanged(species, rebuilt, published):
    got, want = _ids(rebuilt[species], "modelreactions"), _ids(published[species], "modelreactions")
    assert got == want, (
        f"{species}: {len(got - want)} added, {len(want - got)} lost. "
        f"added={sorted(got - want)[:10]} lost={sorted(want - got)[:10]}"
    )


@pytest.mark.parametrize("species", SPECIES)
def test_compound_set_is_unchanged(species, rebuilt, published):
    got, want = _ids(rebuilt[species], "modelcompounds"), _ids(published[species], "modelcompounds")
    assert got == want, f"{species}: {len(got - want)} added, {len(want - got)} lost"


@pytest.mark.parametrize("species", SPECIES)
def test_structural_counts_match(species, rebuilt, published):
    for key in ("biomasses", "modelcompartments"):
        assert len(rebuilt[species].get(key, [])) == len(published[species].get(key, [])), key


def test_conditional_spontaneous_path_is_exercised(rebuilt):
    """Guards the logic the KBase copy of this algorithm does not have.

    rxn22371_c0 reaches the Athaliana model only through the conditional
    spontaneous branch — deferred because its roles are spontaneous, then
    admitted because one of its reagents is present. If a merge drops that
    branch this is the test that notices.
    """
    assert "rxn22371_c0" in _ids(rebuilt["Athaliana_TAIR10"], "modelreactions")
