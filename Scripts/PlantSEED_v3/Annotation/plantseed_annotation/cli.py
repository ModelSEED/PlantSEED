"""`plantseed-annotate` command-line entry point.

Runs the standalone annotator against an OrthoFinder results directory
plus PlantSEED_Roles.json, producing an annotated genome JSON in the
shape plantseed_model/reconstruct.py consumes.

Usage:

    plantseed-annotate \\
        --orthofinder-results /path/to/OrthoFinder/Results_MonDDD \\
        --query-species Sbicolor_v3.1.1 \\
        [--ref-species Athaliana_TAIR10] \\
        [--phylum Monocot] \\
        [--threshold 0.55] \\
        [--roles-file /alt/PlantSEED_Roles.json] \\
        [--psi-cache-dir /alt/writable/PSI_cache] \\
        [--out annotated_genome.json] \\
        [--include-unannotated] \\
        [--workers 8]

Phylum threshold defaults to the phylum's canonical value in paths.PHYLUM_THRESHOLDS_DEFAULT
(Eudicot=0.60, Monocot=0.55, Basal=0.30). Explicit `--threshold` wins over `--phylum`.

The KBase App wrapper (Phase 4) and poplar celery task (Phase 3) both shell
out to this same CLI (via `python -m plantseed_annotation.cli`) so there is
one behaviour to audit and one place to instrument.
"""

import argparse
import datetime
import json
import os
import sys

from . import paths
from .algorithms import orthofinder_io, propagate, psi, psi_refined
from .genome_io import write_annotated_genome


def _load_species_phyla(path):
    """Parse Species_Phyla.txt -> {species: phylum}."""
    out = {}
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                out[parts[0]] = parts[1]
    return out


def _resolve_phylum(query_species, explicit_phylum, phyla_table):
    """Explicit CLI arg wins; otherwise lookup by exact species match;
    then by prefix match ('Ptrichocarpa_v4.1' -> 'Ptrichocarpa_' family)."""
    if explicit_phylum:
        return explicit_phylum
    if query_species in phyla_table:
        return phyla_table[query_species]
    # Prefix match: species name up to first underscore + '_'
    prefix = query_species.split("_", 1)[0] + "_"
    hits = [phy for sp, phy in phyla_table.items() if sp.startswith(prefix)]
    if hits and len(set(hits)) == 1:
        return hits[0]
    return None


def _resolve_threshold(explicit_threshold, phylum):
    if explicit_threshold is not None:
        return float(explicit_threshold)
    if phylum in paths.PHYLUM_THRESHOLDS_DEFAULT:
        return paths.PHYLUM_THRESHOLDS_DEFAULT[phylum]
    return None


def _self_annotate(species, curated_for_ref, out_path, include_unannotated,
                    metadata_extras):
    """Round-trip: emit every curated feature as an annotation of itself.

    Used when --query-species == --ref-species. This is the identity path
    (no orthology, no PSI) — it exists so the annotator can be validated
    against the curated reference itself (PlantSEED_Roles.json → annotated
    genome should reproduce the same feature/function map)."""
    from collections import Counter
    annotations = {}
    for ref_gene, entry in curated_for_ref.items():
        annotations[ref_gene] = {
            "top_ortholog": (species, ref_gene),
            "function":     entry["function"],
            "psi":          1.0,
            "status":       "ANNOTATED",
        }
    stats = Counter(a["status"] for a in annotations.values())
    metadata = dict(metadata_extras)
    metadata.update({
        "annotator":              "plantseed_annotation",
        "annotator_run_utc":      datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "query_species":          species,
        "ref_species":            species,
        "n_annotated_features":   len(annotations),
        "n_curated_ref_features": len(curated_for_ref),
        "status_counts":          dict(stats),
        "mode":                   "self-annotation",
    })
    obj = write_annotated_genome(
        out_path, species, annotations,
        include_unannotated=include_unannotated, metadata=metadata,
    )
    return annotations, stats, obj


def _build_argparser():
    ap = argparse.ArgumentParser(
        prog="plantseed-annotate",
        description="Annotate a plant genome from an OrthoFinder results directory + PlantSEED_Roles.json.",
    )
    ap.add_argument("--orthofinder-results", required=True,
        help="Path to an OrthoFinder Results_* directory (containing Orthogroups/, Orthologues/, MultipleSequenceAlignments/).")
    ap.add_argument("--query-species", required=True,
        help="Species name as it appears in Orthogroups.tsv's header (e.g. 'Sbicolor_v3.1.1').")
    ap.add_argument("--ref-species", default="Athaliana_TAIR10",
        help="Curated reference species. Default: Athaliana_TAIR10.")
    ap.add_argument("--phylum", choices=("Eudicot", "Monocot", "Basal"),
        help="Query species phylum. Sets the default PSI threshold. Auto-detected from Species_Phyla.txt if omitted.")
    ap.add_argument("--threshold", type=float,
        help="PSI threshold above which to propagate the top-ortholog function. Overrides --phylum.")
    ap.add_argument("--roles-file",
        help="Alternate PlantSEED_Roles.json path (default: %s)." % paths.ROLES_FILE)
    ap.add_argument("--species-phyla-file",
        help="Alternate Species_Phyla.txt path (default: %s)." % paths.SPECIES_PHYLA_FILE)
    ap.add_argument("--psi-cache-dir",
        help="Where to cache per-OG PSI matrices. Default: a per-run subdirectory of "
             "$PLANTSEED_SCRATCH_DIR (or the system temp dir). Any existing "
             "<orthofinder-results>/Pairwise_Sequence_Identity/ is still read, never written.")
    ap.add_argument("--workers", type=int,
        help="Number of processes for PSI computation. Default: cpu_count - 1.")
    ap.add_argument("--out", default="annotated_genome.json",
        help="Output annotated genome JSON path.")
    ap.add_argument("--include-unannotated", action="store_true",
        help="Emit features with functions=['Unannotated'] for query genes that had a curated ortholog but didn't clear the threshold or were ambiguous.")
    ap.add_argument("--no-admit-paralogs", action="store_true",
        help="Disable Processing_v2's paralog admission (revert to the pre-Aug-2026 naive path that only considers OF-called orthologs). Use for A/B comparison; default is to admit paralogs above the per-OG baseline.")
    ap.add_argument("--fallback-baseline", type=float, default=0.5,
        help="Fallback PSI used to classify paralogs in OGs that have no OF-called orthologs between the query and ref species. Matches Processing_v2's PAH/PRH rule. Default: 0.5.")
    ap.add_argument("--quiet", action="store_true",
        help="Suppress progress logs.")
    return ap


def main(argv=None):
    args = _build_argparser().parse_args(argv)

    def log(msg):
        if not args.quiet:
            print(msg, file=sys.stderr, flush=True)

    # --- 1. Resolve inputs ----------------------------------------------------
    results_dir = os.path.abspath(args.orthofinder_results)
    ogs_tsv = os.path.join(results_dir, "Orthogroups", "Orthogroups.tsv")
    if not os.path.isfile(ogs_tsv):
        sys.exit(f"ERROR: no Orthogroups.tsv under {results_dir}")

    roles_path  = args.roles_file          or paths.ROLES_FILE
    phyla_path  = args.species_phyla_file  or paths.SPECIES_PHYLA_FILE

    phyla = _load_species_phyla(phyla_path) if os.path.isfile(phyla_path) else {}
    phylum = _resolve_phylum(args.query_species, args.phylum, phyla)
    threshold = _resolve_threshold(args.threshold, phylum)
    if threshold is None:
        sys.exit(
            f"ERROR: could not resolve PSI threshold. Pass --threshold explicitly "
            f"or ensure {args.query_species!r} is in {phyla_path!r} with a known phylum."
        )

    log(f"[cfg] query_species={args.query_species}  ref_species={args.ref_species}")
    log(f"[cfg] phylum={phylum!r}  threshold={threshold}")
    log(f"[cfg] roles_file={roles_path}")
    log(f"[cfg] orthofinder_results={results_dir}")

    # --- 2. Load curated features (from PlantSEED_Roles) ---------------------
    with open(roles_path) as fh:
        roles_data = json.load(fh)
    curated = propagate.build_curated_features(roles_data)
    curated_by_spp = propagate.curated_features_by_source_species(curated)
    curated_for_ref = curated_by_spp.get(args.ref_species, {})
    if not curated_for_ref:
        sys.exit(
            f"ERROR: no curated features for ref-species {args.ref_species!r} in {roles_path}. "
            f"Species with curated features: {sorted(curated_by_spp)}."
        )
    log(f"[curation] {len(curated_for_ref)} curated features for {args.ref_species}")

    # --- 3. Load orthogroups + orthologues -----------------------------------
    ogs, species_in_run = orthofinder_io.load_orthogroups(ogs_tsv)
    log(f"[of] {len(ogs)} orthogroups; species in run: {species_in_run}")
    if args.query_species not in species_in_run:
        sys.exit(
            f"ERROR: --query-species {args.query_species!r} not in Orthogroups.tsv header. "
            f"Present: {species_in_run}"
        )
    if args.ref_species not in species_in_run:
        sys.exit(
            f"ERROR: --ref-species {args.ref_species!r} not in Orthogroups.tsv header. "
            f"Present: {species_in_run}"
        )

    if args.query_species == args.ref_species:
        # Self-annotation: no Orthologues/X__v__X.tsv exists. Emit every
        # curated feature as an annotation of itself — this is the round-trip
        # validation path (the annotator should reproduce PlantSEED_Roles.json's
        # own curation 1:1 on the reference species).
        log(f"[of] self-annotation on {args.query_species} — emitting curated features directly")
        annotations, stats, obj = _self_annotate(
            args.query_species, curated_for_ref, args.out,
            include_unannotated=args.include_unannotated,
            metadata_extras={"phylum": phylum, "psi_threshold": None,
                             "roles_file": roles_path,
                             "orthofinder_results": results_dir},
        )
        log(f"[annot] status counts: {dict(stats)}")
        log(f"[out] wrote {args.out}  ({len(obj['features'])} features)")
        return 0

    orth_tsv = orthofinder_io.orthologues_path(
        results_dir, args.query_species, args.ref_species,
    )
    if not orth_tsv:
        sys.exit(
            f"ERROR: no Orthologues/{args.query_species}__v__{args.ref_species}.tsv "
            f"under {results_dir}."
        )
    q_to_r, _r_to_q = orthofinder_io.load_orthologues(orth_tsv)
    log(f"[of] {len(q_to_r)} query genes with orthologs in {args.ref_species}")

    # --- 4. Restrict to OGs that touch curated ref genes ---------------------
    #    (skip PSI computation on ~90% of OGs that have no curated ref genes).
    #    sp_gene_to_og is transcript-level (Orthogroups.tsv cells are transcripts);
    #    curated_for_ref is gene-level (PlantSEED_Roles.json). Walk the reverse
    #    index once and keep OGs whose transcript-level ref genes normalize to
    #    a curated gene id.
    sp_gene_to_og = orthofinder_io.species_gene_to_og_index(ogs)
    tg = orthofinder_io.transcript_to_gene
    curated_ogs = set()
    for (spp, transcript_id), og_id in sp_gene_to_og.items():
        if spp != args.ref_species:
            continue
        if tg(transcript_id) in curated_for_ref:
            curated_ogs.add(og_id)
    log(f"[of] {len(curated_ogs)} OGs touch curated {args.ref_species} genes")

    # --- 5. Ensure PSI cache for those OGs -----------------------------------
    cache_dir, _stats = psi.ensure_psi_cache(
        results_dir, cache_dir=args.psi_cache_dir,
        ogs=curated_ogs, n_workers=args.workers, log=log,
    )
    # Read from the full search path, not just where we wrote: a prebuilt
    # cache beside the OrthoFinder results is legitimate and is not copied.
    _write_dir, psi_dirs = psi.cache_search_path(results_dir, args.psi_cache_dir)
    psi_by_og = psi.load_psi_for_ogs(psi_dirs, curated_ogs)
    log(f"[psi] loaded PSI for {len(psi_by_og)} OGs")

    # --- 6. Annotate ----------------------------------------------------------
    annotations, stats, pair_stats = psi_refined.annotate_species(
        args.query_species, args.ref_species,
        q_to_r, ogs, psi_by_og, sp_gene_to_og,
        curated_for_ref, threshold,
        admit_paralogs=not args.no_admit_paralogs,
        fallback_baseline=args.fallback_baseline,
    )
    log(f"[annot] status counts: {dict(stats)}")
    log(f"[annot] pair-level tags kept: {dict(pair_stats)}   "
        f"(O=OF ortholog, PAM=paralog above OG mean, PAH=paralog above fallback {args.fallback_baseline})")

    n_annotated = sum(1 for a in annotations.values() if a["status"] == "ANNOTATED")
    log(f"[annot] annotated {n_annotated} query gene(s) out of {len(annotations)} that had a curated candidate")

    # --- 7. Write annotated genome JSON --------------------------------------
    metadata = {
        "annotator": "plantseed_annotation",
        "annotator_run_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "query_species": args.query_species,
        "ref_species":   args.ref_species,
        "phylum":        phylum,
        "psi_threshold": threshold,
        "admit_paralogs": not args.no_admit_paralogs,
        "fallback_baseline": args.fallback_baseline,
        "orthofinder_results": results_dir,
        "roles_file":    roles_path,
        "psi_cache_dir": cache_dir,
        "psi_cache_read_dirs": list(psi_dirs),
        "status_counts": dict(stats),
        "pair_stats":    dict(pair_stats),
        "n_annotated_features": n_annotated,
        "n_curated_ref_features": len(curated_for_ref),
    }
    obj = write_annotated_genome(
        args.out, args.query_species, annotations,
        include_unannotated=args.include_unannotated, metadata=metadata,
    )
    log(f"[out] wrote {args.out}  ({len(obj['features'])} features)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
