"""Choose and run the algorithm chain for annotating one query genome
against a refdata bundle.

Primary path (every tier today -- the kmer fast path below is unimplemented):

    place_query.place(...)  -- DIAMOND placement + mafft --add realignment,
                                NOT full OrthoFinder -b insert mode (see
                                place_query.py's module docstring for why) --
      -> psi_refined.annotate_species(...)  -- unchanged; this is the exact
                                function cli.py's dev-mode path already runs,
                                it does not know or care that its inputs came
                                from DIAMOND placement rather than a full
                                OrthoFinder run
      -> genome_io.build_annotated_genome(...)

Fast path (kbase tier only, once a bundle grows past the 10 GB refdata cap):
  kmer.annotate(...) as a pre-filter, escalate to the primary path only for
  proteins the kmer index couldn't confidently call. Not implemented --
  kmer.py is still a stub, and no bundle has needed it yet (the Sep09 bundle
  is 1.65 GB).

Per-phylum thresholds come from the bundle's own curation/phylum_thresholds.json
(propagate.build_curated_features + refbuild.build_curation wrote them there
at build time from Scripts/PlantSEED_v3/KBase/Annotate_Single_Genome_in_KBase.pl's
constants) -- NOT from paths.PHYLUM_THRESHOLDS_DEFAULT, so an annotation is
reproducible against the exact curation vintage its bundle was built from,
even if the defaults in this checkout later change.
"""

from __future__ import annotations

import os

from . import genome_io, reference
from .algorithms import place_query, propagate, psi_refined

__all__ = ["load_bundle_curation", "resolve_threshold", "annotate"]


def load_bundle_curation(bundle_dir):
    """Read a bundle's curation payload: curated features by species, and
    the per-phylum PSI thresholds it was built with.

    Returns (curated_by_species, phylum_thresholds).
    """
    from .refbuild import bundle as _bundle
    from .refbuild import build_curation

    curation_dir = os.path.join(bundle_dir, _bundle.CURATION_DIR)
    features_path = os.path.join(curation_dir, build_curation.CURATED_FEATURES)
    thresholds_path = os.path.join(curation_dir, build_curation.PHYLUM_THRESHOLDS)

    if not os.path.isfile(features_path):
        raise FileNotFoundError(
            f"no {build_curation.CURATED_FEATURES} under {curation_dir} -- "
            f"is {bundle_dir} a plantseed-refbuild bundle?")

    curated_by_species = _bundle.read_json(features_path)
    phylum_thresholds = (_bundle.read_json(thresholds_path)
                        if os.path.isfile(thresholds_path) else {})
    return curated_by_species, phylum_thresholds


def resolve_threshold(phylum, phylum_thresholds, explicit_threshold=None):
    """Explicit argument wins; otherwise the bundle's own phylum table."""
    if explicit_threshold is not None:
        return float(explicit_threshold)
    if phylum in phylum_thresholds:
        return phylum_thresholds[phylum]
    raise ValueError(
        f"no PSI threshold for phylum {phylum!r} -- pass --threshold explicitly, "
        f"or known phyla in this bundle are {sorted(phylum_thresholds)}")


def annotate(query_fasta, bundle_dir, query_species, ref_species, phylum, *,
            threshold=None, admit_paralogs=True,
            fallback_baseline=psi_refined.DEFAULT_FALLBACK_BASELINE,
            evalue=place_query.DEFAULT_EVALUE,
            max_target_seqs=place_query.DEFAULT_MAX_TARGET_SEQS,
            n_workers=None, include_unannotated=False, log=print):
    """Annotate one query proteome FASTA against a refdata bundle.

    This is the function `annotate_fasta` (the new CLI entry point) and the
    `annotate` capability both call -- the only place the
    place_query -> psi_refined -> genome_io chain is assembled, so there is
    one behaviour to test and one place to change it.

    `query_fasta`: headers `<query_species>||<gene>` (orthofinder_io's
    convention throughout this package). A bare-header FASTA should be
    prefixed by the caller before this is called -- dispatch does not guess
    a species from a filename.

    Returns a dict shaped like genome_io.build_annotated_genome's output,
    plus a `diagnostics` key carrying placement/annotation counts a caller
    (the CLI, the MCP tool) can log or report without re-deriving them.
    """
    ok, issues = reference.verify(bundle_dir, check_hashes=False)
    if not ok:
        raise ValueError(
            f"bundle at {bundle_dir} failed a fast verify: {'; '.join(issues[:5])}")

    curated_by_species, phylum_thresholds = load_bundle_curation(bundle_dir)
    curated_for_ref = curated_by_species.get(ref_species, {})
    if not curated_for_ref:
        raise ValueError(
            f"no curated features for ref-species {ref_species!r} in this "
            f"bundle. Species with curated features: "
            f"{sorted(curated_by_species)}")

    resolved_threshold = resolve_threshold(phylum, phylum_thresholds, threshold)

    log(f"[dispatch] placing {query_species} proteins against {bundle_dir}")
    placement = place_query.place(
        query_fasta, bundle_dir, query_species,
        evalue=evalue, max_target_seqs=max_target_seqs,
        n_workers=n_workers, log=log)

    log(f"[dispatch] annotating with threshold={resolved_threshold} "
        f"(phylum={phylum})")
    annotations, stats, pair_stats = psi_refined.annotate_species(
        query_species, ref_species,
        placement["orthologues_dict"], placement["ogs"],
        placement["psi_by_og"], placement["sp_gene_to_og"],
        curated_for_ref, resolved_threshold,
        admit_paralogs=admit_paralogs, fallback_baseline=fallback_baseline,
    )
    n_annotated = sum(1 for a in annotations.values() if a["status"] == "ANNOTATED")
    log(f"[dispatch] annotated {n_annotated} query gene(s) out of "
        f"{len(annotations)} that had a curated candidate")

    genome_obj = genome_io.build_annotated_genome(
        query_species, annotations, include_unannotated=include_unannotated)

    genome_obj["diagnostics"] = {
        "n_query_genes_searched": placement["n_query_genes_searched"],
        "n_query_genes_placed": placement["n_query_genes_placed"],
        "n_query_genes_scored": placement["n_query_genes_scored"],
        "n_curated_ref_features": len(curated_for_ref),
        "status_counts": dict(stats),
        "pair_stats": dict(pair_stats),
        "n_annotated_features": n_annotated,
        "phylum": phylum,
        "psi_threshold": resolved_threshold,
    }
    return genome_obj
