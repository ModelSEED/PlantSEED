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

from plantseed_core import runtime

from . import dispatch, paths
from .algorithms import orthofinder_io, place_query, propagate, psi, psi_refined
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
    ap.add_argument("--orthofinder-results",
        help="Path to an OrthoFinder Results_* directory (containing Orthogroups/, "
             "Orthologues/, MultipleSequenceAlignments/). Dev-mode path: the query "
             "species must already be IN this multi-species OrthoFinder run. "
             "Mutually exclusive with --bundle-dir/--query-fasta, which place a "
             "genome that was never part of any OrthoFinder run against a "
             "pre-built refdata bundle instead -- see dispatch.py.")
    ap.add_argument("--bundle-dir",
        help="Path to a plantseed-refbuild bundle (manifest.json + "
             "orthofinder_families/ + curation/). Requires --query-fasta. "
             "Mutually exclusive with --orthofinder-results.")
    ap.add_argument("--query-fasta",
        help="Query proteome FASTA, headers '<query-species>||<gene>'. Only used "
             "with --bundle-dir.")
    ap.add_argument("--query-species", required=True,
        help="Species name. With --orthofinder-results: as it appears in "
             "Orthogroups.tsv's header (e.g. 'Sbicolor_v3.1.1'). With "
             "--bundle-dir: the species prefix used in --query-fasta's headers.")
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
        help="Number of processes for PSI computation (--orthofinder-results mode) "
             "or threads for diamond/mafft (--bundle-dir mode). Default: cpu_count - 1.")
    ap.add_argument("--evalue", type=float, default=place_query.DEFAULT_EVALUE,
        help="--bundle-dir mode only: diamond blastp e-value cutoff for the "
             "placement search. Default: %s." % place_query.DEFAULT_EVALUE)
    ap.add_argument("--max-target-seqs", type=int,
        default=place_query.DEFAULT_MAX_TARGET_SEQS,
        help="--bundle-dir mode only: diamond blastp --max-target-seqs. "
             "Default: %d." % place_query.DEFAULT_MAX_TARGET_SEQS)
    ap.add_argument("--out", default="annotated_genome.json",
        help="Output annotated genome JSON path.")
    ap.add_argument("--include-unannotated", action="store_true",
        help="Emit features with functions=['Unannotated'] for query genes that had a curated ortholog but didn't clear the threshold or were ambiguous.")
    ap.add_argument("--no-admit-paralogs", action="store_true",
        help="Disable Processing_v2's paralog admission (revert to the pre-Aug-2026 naive path that only considers OF-called orthologs). Use for A/B comparison; default is to admit paralogs above the per-OG baseline.")
    ap.add_argument("--fallback-baseline", type=float, default=0.5,
        help="Fallback PSI used to classify paralogs in OGs that have no OF-called orthologs between the query and ref species. Matches Processing_v2's PAH/PRH rule. Default: 0.5.")
    ap.add_argument("--conservation-gradient-report",
        help="Optional path to also write the two-layer conservation-gradient "
             "report (presence rate + relmax confidence banding, split by "
             "generalized/specialized role_class; see "
             "REPORT_orthofunctional_conservation_gradient.md). Diagnostic "
             "only -- does not affect which genes get annotated. Omit to skip.")
    ap.add_argument("--quiet", action="store_true",
        help="Suppress progress logs.")
    return ap


def _main_bundle_mode(args, log):
    """--bundle-dir + --query-fasta: dispatch.annotate against a refdata
    bundle, for a query genome that was never part of any OrthoFinder run.

    --conservation-gradient-report is NOT available in this mode: Layer 1
    (presence rate) needs the FULL, unfiltered orthogroup set to avoid the
    survivorship-bias artifact it exists to catch (see
    psi_refined.compute_presence_rates's docstring), and a bundle only ships
    the pruned curated-OG subset by design -- there is no "did this species
    have ANY gene in this OG at all" answer available here, only "did
    placement find one in a curated OG." Reported as an error rather than a
    silently wrong number.
    """
    if args.conservation_gradient_report:
        sys.exit("ERROR: --conservation-gradient-report is not available in "
                 "--bundle-dir mode -- it needs the full, unfiltered "
                 "orthogroup set (Layer 1 presence rate), which a pruned "
                 "refdata bundle does not carry. Use --orthofinder-results "
                 "mode for the gradient report.")

    bundle_dir = os.path.abspath(args.bundle_dir)
    query_fasta = os.path.abspath(args.query_fasta)
    if not os.path.isfile(query_fasta):
        sys.exit(f"ERROR: query FASTA not found: {query_fasta}")

    phyla_path = args.species_phyla_file or paths.SPECIES_PHYLA_FILE
    phyla = _load_species_phyla(phyla_path) if os.path.isfile(phyla_path) else {}
    phylum = _resolve_phylum(args.query_species, args.phylum, phyla)
    if phylum is None and args.threshold is None:
        log(f"[cfg] no phylum resolved for {args.query_species!r} and no "
            f"--threshold: applying no phylum gate")

    log(f"[cfg] mode=bundle  query_species={args.query_species}  "
        f"ref_species={args.ref_species}")
    log(f"[cfg] bundle_dir={bundle_dir}")
    log(f"[cfg] query_fasta={query_fasta}")
    log(f"[cfg] phylum={phylum!r}  threshold={args.threshold}")

    try:
        genome_obj = dispatch.annotate(
            query_fasta, bundle_dir, args.query_species, args.ref_species,
            phylum, threshold=args.threshold,
            admit_paralogs=not args.no_admit_paralogs,
            fallback_baseline=args.fallback_baseline,
            evalue=args.evalue, max_target_seqs=args.max_target_seqs,
            n_workers=args.workers, include_unannotated=args.include_unannotated,
            log=log,
        )
    except (FileNotFoundError, ValueError) as exc:
        sys.exit(f"ERROR: {exc}")

    diag = genome_obj.pop("diagnostics")
    metadata = {
        "annotator": "plantseed_annotation",
        "annotator_run_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "bundle",
        "query_species": args.query_species,
        "ref_species": args.ref_species,
        "bundle_dir": bundle_dir,
        "query_fasta": query_fasta,
        **diag,
    }
    genome_obj["metadata"] = metadata

    out_path = runtime.enforce_writable(args.out)
    with open(out_path, "w") as fh:
        json.dump(genome_obj, fh, indent=2, sort_keys=True)
    log(f"[out] wrote {out_path}  ({len(genome_obj['features'])} features)")
    return 0


def main(argv=None):
    args = _build_argparser().parse_args(argv)

    def log(msg):
        if not args.quiet:
            print(msg, file=sys.stderr, flush=True)

    # Check the destination before doing the work, not after: a reconstruction
    # or a PSI sweep that dies on the final open() has burned the whole run.
    # No-op unless an adapter has declared the mounts.
    try:
        runtime.enforce_writable(args.out)
    except PermissionError as exc:
        sys.exit(f"ERROR: {exc}")

    # --- Mode selection: a bundle + query FASTA (dispatch.annotate -- a
    # genome that was never part of any OrthoFinder run), or a full
    # multi-species OrthoFinder run (dev-mode path below, unchanged). Exactly
    # one of the two input styles may be given.
    bundle_mode = bool(args.bundle_dir or args.query_fasta)
    if bundle_mode and args.orthofinder_results:
        sys.exit("ERROR: --bundle-dir/--query-fasta and --orthofinder-results "
                 "are mutually exclusive -- pick one input mode.")
    if bundle_mode and not (args.bundle_dir and args.query_fasta):
        sys.exit("ERROR: --bundle-dir and --query-fasta must be given together.")
    if not bundle_mode and not args.orthofinder_results:
        sys.exit("ERROR: pass either --orthofinder-results, or "
                 "--bundle-dir together with --query-fasta.")

    if bundle_mode:
        return _main_bundle_mode(args, log)

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

    # --- 6b. Optional two-layer conservation-gradient report -------------------
    # Diagnostic only (see REPORT_orthofunctional_conservation_gradient.md and
    # the psi_refined module docstring): does not feed back into `annotations`
    # or `stats` above in any way. Uses the FULL, unfiltered `ogs` for Layer 1
    # (presence) specifically to avoid the survivorship-bias artifact that
    # motivated splitting the two layers in the first place -- restricting to
    # `curated_ogs` here would silently reintroduce it.
    if args.conservation_gradient_report:
        gradient = psi_refined.conservation_gradient_report(
            curated_for_ref, ogs, sp_gene_to_og, psi_by_og,
            args.query_species, args.ref_species, q_to_r,
        )
        gradient["metadata"] = {
            "query_species": args.query_species,
            "ref_species":   args.ref_species,
            "note": ("Diagnostic report; does not affect annotation "
                     "acceptance. relmax bands are explicitly arbitrary "
                     "communication bins, not fitted thresholds -- see "
                     "REPORT_orthofunctional_conservation_gradient.md."),
        }
        out_path = runtime.enforce_writable(args.conservation_gradient_report)
        with open(out_path, "w") as fh:
            json.dump(gradient, fh, indent=2, sort_keys=True)
        for role_class, bucket in sorted(gradient["summary"].items()):
            log(f"[gradient] {role_class}: presence={bucket['presence_pct']}%  "
                f"confident={bucket['confident_pct']}%  "
                f"no_confident_match={bucket['no_confident_match_pct']}%  "
                f"(n_curated={bucket['n_curated']}, n_present={bucket['n_present']})")
        log(f"[gradient] wrote {out_path}")

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
