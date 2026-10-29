"""Capability declaration for plantseed_annotation.

Metadata only, mirroring plantseed_model/capabilities.py's pattern exactly:
the implementations stay where they are, and importing this module must not
import diamond, mafft, or anything else the annotator shells out to --
a generator building a KBase spec or a CTS submit body needs the
declaration, not a working toolchain.

Parameters mirror `dispatch.annotate`'s signature, which is what cli.py's
--bundle-dir mode and the MCP tool both call -- see cli.py's module
docstring ("one behaviour to audit and one place to instrument") for why
that function, not this declaration, is the thing actually describing the
call.

`bundle_dir` is deliberately NOT a parameter here. Every other platform-
specific path in this package (template, compartments, roles file) is an
optional override with a packaged default; the refdata bundle is not --
it is multi-gigabyte reference data that ships with the image/mount, not
something a caller supplies per call. `reference.bundle_dir()` resolves it
from PLANTSEED_ANNOT_BUNDLE_DIR / PLANTSEED_ANNOT_BUNDLE_ROOT, same as every
other delivery surface.
"""

from __future__ import annotations

from plantseed_core.registry import Artifact, FileParam, Param, Resources, capability

ANNOTATE_PARAMS = (
    FileParam("genome", fmt="protein_fasta", required=True,
              help="Query proteome FASTA. Headers must be "
                   "'<query_species>||<gene_id>' (prefix with query_species "
                   "first if the source FASTA has bare headers)."),
    Param("query_species", type="str", required=True,
          help="Species name -- the prefix used in genome's FASTA headers, "
               "and the id the output genome is written under."),
    Param("ref_species", type="str", default="Athaliana_TAIR10",
          help="Curated reference species to annotate against."),
    Param("phylum", type="str",
          help="Optional query species phylum. Sets a PSI threshold from the "
               "bundle's own phylum_thresholds.json. Omit both phylum and "
               "threshold to apply no phylum gate (interim, while "
               "per-orthogroup thresholds replace the per-phylum ones)."),
    Param("threshold", type="float",
          help="PSI threshold above which to propagate the top-ortholog "
               "function. Overrides phylum."),
)

ANNOTATE_OUTPUTS = (
    Artifact("genome", "annotated_genome.json", schema="plantseed_annotated_genome_json",
             help="The annotated genome, in the shape the reconstruct "
                  "capability's `genome` input expects."),
)


@capability(
    name="annotate",
    summary=(
        "Annotate a plant proteome against curated PlantSEED reference genes, "
        "by DIAMOND-placing each query protein into a curated orthogroup and "
        "resolving the top ortholog with per-orthogroup PSI scoring. Produces "
        "an annotated genome JSON ready for the reconstruct capability."
    ),
    when=(
        "Before reconstructing a metabolic model for a genome that has no "
        "existing PlantSEED annotation -- this is the first step for any "
        "species not already carrying a 'role # compartment' functional "
        "annotation. Not a substitute for a full multi-species OrthoFinder "
        "run when one already exists and includes the query species; that "
        "dev-mode path (plantseed-annotate --orthofinder-results) gives a "
        "true OrthoFinder ortholog call where this gives a DIAMOND best-hit "
        "placement -- see place_query.py's module docstring for the "
        "distinction and why this capability uses the latter."
    ),
    guarantee=(
        "The query genome never needs to have been part of any OrthoFinder "
        "run -- placement happens at call time against the bundle's existing "
        "curated orthogroups via DIAMOND + mafft --add, which is seconds to "
        "low minutes rather than re-running OrthoFinder's full multi-species "
        "pipeline. Downstream, the same psi_refined.annotate_species logic "
        "(per-orthogroup baseline, hard floor, per-phylum threshold) that "
        "the dev-mode CLI path and every measured benchmark in this "
        "repository already runs -- placement method differs, acceptance "
        "logic does not."
    ),
    params=ANNOTATE_PARAMS,
    outputs=ANNOTATE_OUTPUTS,
    # Measured on the Sep09 reference bundle (759 curated orthogroups, 1.65 GB):
    # a 500-protein test query placed, realigned and scored in ~22-56s
    # single-pass on an 8-core allocation (dominated by mafft --add on the
    # two largest orthogroups, ~2,300-3,200 members each). A full genome
    # (~30-50k proteins) scales with the number that DIAMOND actually places
    # in a curated OG (a small fraction -- ~13% measured for Poplar), not
    # with total proteome size, so this is a conservative ceiling, not a
    # linear extrapolation.
    resources=Resources(cpus=8, memory_gb=8, runtime_h=0.5, refdata="plantseed_annotation"),
    image="plantseed-annotation",
)
def annotate(**kwargs):
    """Thin indirection to the engine.

    Imported lazily so that reading the declaration costs nothing -- same
    pattern as plantseed_model.capabilities.reconstruct.
    """
    from . import dispatch

    return dispatch.annotate
