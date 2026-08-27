"""Capability declarations for plantseed_model.

Metadata only — the implementations stay where they are. Importing this module
must not import cobrapy or anything else optional, because a generator building
a KBase spec or a CTS submit body needs the declaration, not the code.

Parameters mirror plantseed_annotation.reconstruct_cli's argparse exactly; the
CLI is the thing being described, not a second interface. `--quiet` and
`--log-rxn` are intentionally absent: they control local console output, which
no platform surfaces.
"""

from __future__ import annotations

from plantseed_core.registry import Artifact, FileParam, Param, Resources, capability

RECONSTRUCT_PARAMS = (
    FileParam("genome", fmt="plantseed_annotated_genome_json", required=True,
              help="Annotated genome JSON, as produced by the annotate capability."),
    FileParam("template", fmt="plantseed_template_json",
              help="PlantSEED template JSON. Defaults to the packaged "
                   "PlantSEED_Biomass_Template.json."),
    FileParam("compartments", fmt="plantseed_compartments_json",
              help="PlantSEED_Compartments.json. Defaults to the packaged copy."),
    Param("model_id", type="str",
          help="Model id and name. Defaults to <genome id>_model."),
)

RECONSTRUCT_OUTPUTS = (
    Artifact("model", "model.json", schema="KBaseFBA.FBAModel",
             help="The reconstructed metabolic model."),
    Artifact("provenance", "provenance.json", schema="Provenance",
             help="Inputs, versions and content_id for this run."),
)


@capability(
    name="reconstruct",
    summary=(
        "Reconstruct a plant primary-metabolism model from a PlantSEED-annotated "
        "genome and a curated template. Deterministic, needs no network and no "
        "reference data — the template and compartments ship with the package."
    ),
    when=(
        "Before hand-building a plant metabolic model from an annotated genome, "
        "or re-deriving PlantSEED role-to-reaction mappings from the raw data "
        "files. Also reach for it to re-run an existing model against a newer "
        "curation release, since the run is deterministic and diffable."
    ),
    guarantee=(
        "Curated subcellular compartments (a plant model is wrong without "
        "plastid / mitochondrion / peroxisome placement, and a generic "
        "gene-to-reaction mapping does not carry it), stable PS_role_* "
        "identities so two models can be diffed across curation versions, the "
        "conditional-spontaneous-reaction path the KBase copy of this algorithm "
        "lacks, and bit-identical output for the same inputs."
    ),
    params=RECONSTRUCT_PARAMS,
    outputs=RECONSTRUCT_OUTPUTS,
    # Measured, not guessed: the three preprint genomes each reconstruct in
    # well under a minute single-threaded. Kept at 1 cpu / 1 h so the CTS
    # cpu-hour budget is spent on annotation, which is the expensive half.
    resources=Resources(cpus=1, memory_gb=4, runtime_h=1.0, refdata=None),
    image="plantseed-model",
)
def reconstruct(**kwargs):
    """Thin indirection to the engine.

    Imported lazily so that reading the declaration costs nothing.
    """
    from .reconstruct import ReconstructAppImpl

    return ReconstructAppImpl
