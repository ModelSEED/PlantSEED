"""PSI-refined ortholog + functional-homolog resolution.

Ports the algorithm from
    ~/Seq_Home/PlantSEED_Processing_v2/Identify_Functional_Homologs.py
    ~/Seq_Home/PlantSEED_Processing_v2/Process_Functional_Homologs.py

For a query species Q and a reference species R (typically Athaliana_TAIR10):

  1. For each orthogroup containing genes from both Q and R, compute a
     baseline PSI: the 10th percentile of the PSI values for OF-called
     ortholog pairs between Q and R in that OG.
       - If no OF orthologs exist for (Q, R) in this OG, fall back to 0.5.

  2. Walk every cross-species (q_transcript, r_transcript) pair in the OG
     and classify:
       - 'O'   OF-called ortholog — accept
       - 'PAM' paralog above the OG-species-pair baseline — accept
       - 'PAH' paralog above the fallback 0.5 (no baseline) — accept
       - 'PRM' paralog below the baseline — reject
       - 'PRH' paralog below fallback — reject
     Rejected pairs are dropped from consideration entirely. Accepted pairs
     are annotation candidates.

  3. Aggregate transcripts to genes:
       - group query transcripts by query gene (transcript_to_gene)
       - group ref transcripts by ref gene
       - PSI(q_gene, r_gene) = MAX over any (q_transcript, r_transcript)
         accepted candidate pair
       - Drop ref genes not in the curated set from PlantSEED_Roles.json

  4. Apply the per-phylum PSI threshold and the kb_orthofinder tie-break
     rules (see annotate_query_gene) to pick the top curated ortholog and
     propagate its function.

The tie-break rules are lifted verbatim from
    plantseed-v3/kb_orthofinder/lib/kb_orthofinder/kb_orthofinderImpl.py::propagate_annotation

Two-layer conservation-gradient report
---------------------------------------
`conservation_gradient_report` (bottom of this module) is a DIAGNOSTIC
addition, ported from the standalone analysis in
    kbase_refactor/REPORT_orthofunctional_conservation_gradient.md
It reports, for one query-species annotation run, split by curated
role_class (generalized vs. specialized metabolism, from
propagate.build_curated_features):

  - presence rate: does the query species have >=1 gene in the same FULL,
    unfiltered orthogroup as the curated reference gene at all? (Layer 1)
  - confidence given presence: for genes that clear Layer 1 and also land
    in a PSI-computable orthogroup, relmax = best PSI achieved against the
    ref gene / the highest PSI seen anywhere in that orthogroup's alignment,
    banded into confident / ambiguous / no_confident_match. (Layer 2)

This is reported ALONGSIDE `annotate_species`'s output, not folded into it.
`annotate_species`'s accept/reject decisions (baseline percentile, hard
floor, per-phylum threshold) are UNCHANGED by this addition.

IMPORTANT — relmax is a reporting signal here, not an acceptance rule.
kbase_refactor/SWEEP_relmax_2026-09-28.md measured relmax as a
false-positive classifier against the 27 known-bad Poplar glucosinolate
calls and found it underperforms the existing absolute-PSI hard floor
(52% catch at Y=0.85 vs. 70% for the existing machinery), and that a
union of the two doesn't beat the absolute floor alone. relmax IS,
separately, the more distance-stable of the two signals in aggregate
(median 0.92-1.00 across the whole species panel vs. absolute PSI's
0.74->0.47) and tracks the generalized-vs-specialized conservation gap
cleanly — which is exactly what makes it useful for THIS report and not
(yet, on the evidence in hand) for replacing any threshold in
`annotate_species`. See NEXT_SESSION.md §3 for the still-open question of
whether/how a per-orthogroup relative signal should ever feed the
classifier itself.
"""

from collections import Counter, defaultdict

from . import orthofinder_io as _oio
from . import propagate as _propagate


UNANNOTATED_LT_THRESHOLD = "Unannotated 1: LESS_THAN_THRESHOLD"
UNANNOTATED_AMB_HIT      = "Unannotated 3: AMB_HIT"
UNANNOTATED_NO_REF_HIT   = "Unannotated 4: NO_REF_HIT"

# Fallback baseline used when an OG has no OF-called ortholog pairs
# between the query and ref species (matches Processing_v2's PAH/PRH split).
# Rarely reached: measured over all 23 reference species, only 1-2% of the 758
# enzymatic orthogroups have no ortholog baseline, and the rate does not grow
# with taxonomic distance (Eudicot 0.9%, Monocot 2.0%, Basal 1.8%, Alga 0.6%).
DEFAULT_FALLBACK_BASELINE = 0.5

#: Quantile of an OG's ortholog-PSI distribution used as the in-paralog
#: baseline. Processing_v2 used the arithmetic mean; the 10th percentile is
#: strictly better on the benchmark of curated Arabidopsis in-paralog pairs.
#:
#: Measured on the 417 benchmark pairs where BOTH genes carry an
#: experimentally-evidenced catalytic activity in UniProt (ECO:0000269) --
#: the subset whose labels are independent of PlantSEED curation, and so of
#: the sequence-similarity reasoning that produced much of it:
#:
#:     baseline        precision   recall
#:     10th pct           85.7%     60.3%
#:     25th pct           83.6%     42.0%
#:     median             84.4%     36.0%
#:     max                83.7%     22.7%
#:
#: Precision is flat-to-worse as the baseline rises, so raising it buys
#: nothing and costs recall: mean -> max discards ~10 correct in-paralogs per
#: incorrect one avoided. On the full 1,846-pair benchmark precision instead
#: *climbs* with the baseline (92.5% -> 93.8%), but that gradient is an
#: artifact of the unevidenced pairs, whose labels were themselves assigned by
#: similarity -- exactly what a similarity score will agree with.
BASELINE_PERCENTILE = 0.10

#: Absolute PSI below which a pair is refused outright, whatever OrthoFinder
#: called it. Distinct from BASELINE_PERCENTILE (relative, per-orthogroup,
#: gates in-paralogs) and from the per-phylum thresholds (relative to phylum).
#: This one is a sanity guard against alignment artifacts, not a quality gate.
#:
#: Of 11,901 Arabidopsis<->Poplar OrthoFinder ortholog pairs, 8 score exactly
#: 0.00. None involves a curated gene, so none annotates anything; restricted to
#: the 8,185 pairs that CAN transfer an annotation the minimum is 0.02, and that
#: single case is ATCG00070 (chloroplast-encoded PsbK) called as ortholog to a
#: nuclear Poplar gene -- a NUPT artifact, already caught by the organellar
#: filter. Below ~0.20 a pair is an artifact of aligning a hugely divergent
#: family, not a functional ortholog: the genes down there carry two or three
#: mutually contradictory curated references each.
#:
#: Cost at the gene level is negligible -- 2 of 1,707 ortholog-derived
#: annotations (0.12%) at 0.20, 7 (0.41%) at 0.25. Effect on the in-paralog
#: benchmark is nil: at 0.20 the confusion matrix is bit-identical to no floor
#: (only 5 of 329 baselines move, none flips a decision). 0.25 measured
#: marginally better (MCC 0.242 -> 0.265, three fewer false positives); 0.20 is
#: the default because it provably costs nothing.
#:
#: Note when re-measuring: excluding sub-floor pairs from the BENCHMARK as well
#: as the baseline makes MCC appear to collapse (0.242 -> 0.159 at 0.25). That
#: is an artifact -- TP/FP/FN are unchanged and only TN falls, because the floor
#: removes pairs the gate already rejected correctly. MCC is not comparable
#: across different evaluation sets.
ORTHOLOG_PSI_HARD_FLOOR = 0.20


# ----------------------------------------------------------------------------
# Baseline + candidate classification (the Processing_v2 core)
# ----------------------------------------------------------------------------
def _pair_key(a, b):
    return (a, b) if a < b else (b, a)


def _percentile(sorted_values, q):
    """Nearest-rank percentile of an already-sorted, non-empty list.

    Deliberately not statistics.quantiles(): that needs n >= 2 and
    interpolates, and most orthogroups here carry only a handful of ortholog
    pairs -- an OG with a single pair must still yield that pair's PSI rather
    than raise.
    """
    idx = int(q * (len(sorted_values) - 1) + 0.5)
    return sorted_values[min(idx, len(sorted_values) - 1)]


def compute_og_baselines(orthologues_dict, psi_by_og, sp_gene_to_og,
                          query_species, ref_species,
                          percentile=BASELINE_PERCENTILE):
    """Return {og_id: baseline_psi_or_None}.

    For each OG containing at least one OF-called ortholog pair between
    query_species and ref_species, the baseline is the `percentile` quantile
    of the PSI values over those pairs (looked up in the per-OG PSI matrix).
    OGs with no OF orthologs (for this species pair) get None so callers know
    to use the fallback.

    The baseline is deliberately RELATIVE to each orthogroup, because the
    question it answers is "is this in-paralog as close to the reference as
    this family's orthologs are?" -- which only means anything against the
    family's own scale. It is NOT usable as a check on the ortholog calls
    themselves: in a promiscuous superfamily every ortholog pair scores low,
    so the baseline sinks to meet them (0.38 in the GST orthogroup, 0.32 in
    the CYP83 one). Ortholog transfers need an absolute floor instead.

    `orthologues_dict` is the query→ref map from orthofinder_io.load_orthologues
    (transcript-level, with the '<species>||' prefix already stripped).
    """
    values = defaultdict(list)
    for q_tr, entry in orthologues_dict.items():
        og_id = entry.get("og") or sp_gene_to_og.get((query_species, q_tr))
        if not og_id:
            continue
        pair_map = psi_by_og.get(og_id)
        if not pair_map:
            continue
        for r_tr in entry.get("orthologs", []):
            p = pair_map.get(_pair_key(q_tr, r_tr))
            if p is None:
                continue
            values[og_id].append(p)
    return {og: _percentile(sorted(v), percentile) for og, v in values.items()}


def classify_og_pairs(og_id, q_transcripts, r_transcripts,
                       of_ortholog_pairs, psi_map, baseline,
                       fallback_baseline=DEFAULT_FALLBACK_BASELINE,
                       hard_floor=ORTHOLOG_PSI_HARD_FLOOR,
                       rejected_report=None):
    """Classify every cross-species (q_tr, r_tr) pair in one OG.

    Args:
      og_id: the OG identifier (used only for error reporting).
      q_transcripts: iterable of query-species transcript ids in this OG.
      r_transcripts: iterable of ref-species transcript ids in this OG.
      of_ortholog_pairs: set of frozenset({q_tr, r_tr}) pairs OF called orthologs.
      psi_map: {(g1, g2): psi} for this OG (sorted-pair keys).
      baseline: percentile of OF-ortholog PSI for (query, ref) in this OG, or
                None if no OF orthologs exist.
      fallback_baseline: threshold to use when baseline is None (default 0.5).
      hard_floor: absolute PSI below which a pair is refused whatever OF called
                  it. Applies to orthologs AND paralogs — the artifact argument
                  does not care which tag the pair carries. Pass 0.0 to disable.
      rejected_report: optional list; every floor rejection is appended as a
                  dict so the caller can report what went and why. Nothing is
                  dropped silently — see the transparency rule.

    Returns a list of tuples: (q_tr, r_tr, psi, tag)
      tag in {'O', 'PAM', 'PAH'} — only accepted pairs are returned.
    """
    out = []
    for q_tr in q_transcripts:
        for r_tr in r_transcripts:
            psi = psi_map.get(_pair_key(q_tr, r_tr))
            if psi is None:
                continue
            is_ortho = frozenset({q_tr, r_tr}) in of_ortholog_pairs
            if psi < hard_floor:
                # An OF ortholog call at this PSI is an alignment artifact, not
                # a functional ortholog. Refused BEFORE the O branch, which is
                # the whole point: O otherwise bypasses every PSI test.
                if rejected_report is not None:
                    rejected_report.append({
                        "og": og_id, "query": q_tr, "ref": r_tr, "psi": psi,
                        "tag": "O" if is_ortho else "P",
                        "reason": "below-ortholog-psi-hard-floor",
                        "floor": hard_floor,
                    })
                continue
            if is_ortho:
                out.append((q_tr, r_tr, psi, "O"))
            elif baseline is not None:
                if psi > baseline:
                    out.append((q_tr, r_tr, psi, "PAM"))
                # else PRM — reject
            else:
                if psi > fallback_baseline:
                    out.append((q_tr, r_tr, psi, "PAH"))
                # else PRH — reject
    return out


def _of_ortholog_pairs_for_og(orthologues_dict, og_id):
    """Return the set of frozenset({q_tr, r_tr}) pairs OF called orthologs
    in the given OG. Used inside classify_og_pairs."""
    pairs = set()
    for q_tr, entry in orthologues_dict.items():
        if entry.get("og") != og_id:
            continue
        for r_tr in entry.get("orthologs", []):
            pairs.add(frozenset({q_tr, r_tr}))
    return pairs


# ----------------------------------------------------------------------------
# Per-query-gene decision (unchanged tie-break rules)
# ----------------------------------------------------------------------------
def annotate_query_gene(query_gene, ref_orthologs, psi_lookup_fn, threshold,
                         curated_features_for_ref, ref_species):
    """Decide the annotation for a single query gene.

    Args:
      query_gene: the query species gene id.
      ref_orthologs: list of reference-species gene ids (already narrowed to
                     the curated set AND already filtered by whichever
                     PSI-threshold rules the caller wants applied).
      psi_lookup_fn: callable (query_gene, ref_gene) -> psi float or None.
      threshold: phylum PSI threshold; refs below this are dropped BEFORE
                 tie-break. Pass `None` to skip this floor (annotate_species
                 does the more nuanced 'O accepted / PA* threshold-gated'
                 filter itself and passes threshold=None here).
      curated_features_for_ref: {ref_gene: {'function': str, ...}}.
      ref_species: for logging.

    Returns dict with keys 'top_ortholog', 'function', 'psi', 'status'.
    """
    if not ref_orthologs:
        return {"top_ortholog": None, "function": None, "psi": None,
                "status": "NO_ORTHOLOG"}

    psi_by_ref = {}
    for ref_gene in ref_orthologs:
        psi = psi_lookup_fn(query_gene, ref_gene)
        if psi is not None:
            psi_by_ref[ref_gene] = psi

    if not psi_by_ref:
        return {"top_ortholog": None, "function": None, "psi": None,
                "status": "NO_ORTHOLOG"}

    top_psi = max(psi_by_ref.values())
    if threshold is not None and top_psi < threshold:
        return {"top_ortholog": None, "function": None, "psi": top_psi,
                "status": "LT_THRESHOLD"}

    top_refs = [ref for ref, p in psi_by_ref.items() if p == top_psi]

    # Tie-break. Replaces the composed-string comparison ported from
    # kb_orthofinderImpl.propagate_annotation, which rejected same-enzyme hits
    # that differed only in compartment. See FIX_AMBHIT_ROLE_UNION_260812.md.
    curated_top = [r for r in top_refs
                   if curated_features_for_ref.get(r, {}).get("function")]
    if not curated_top:
        return {"top_ortholog": None, "function": None, "psi": top_psi,
                "status": "NO_ORTHOLOG"}

    if len(curated_top) == 1:
        top_ref = curated_top[0]
        fn = curated_features_for_ref[top_ref]["function"]
        merged_from = None
    else:
        entries = [curated_features_for_ref[r] for r in curated_top]
        merged = _propagate.merge_functions(entries)
        if merged is None:
            return {"top_ortholog": None, "function": None, "psi": top_psi,
                    "status": "AMB_HIT"}
        top_ref = sorted(curated_top)[0]
        fn = merged[0]
        merged_from = sorted(curated_top)

    return {
        "top_ortholog": (ref_species, top_ref),
        "function":     fn,
        "psi":          top_psi,
        "status":       "ANNOTATED",
        "merged_from":  merged_from,
    }


# ----------------------------------------------------------------------------
# Whole-genome annotation
# ----------------------------------------------------------------------------
def annotate_species(query_species, ref_species, orthologues_dict,
                      ogs, psi_by_og, sp_gene_to_og,
                      curated_features_for_ref, threshold,
                      admit_paralogs=True,
                      fallback_baseline=DEFAULT_FALLBACK_BASELINE,
                      hard_floor=ORTHOLOG_PSI_HARD_FLOOR,
                      rejected_report=None):
    """Annotate every query GENE that has at least one curated-ref candidate.

    Candidates are the O + PAM + PAH pairs from Processing_v2's rule
    (see module docstring). Toggle `admit_paralogs=False` to fall back to
    the naive "OF orthologs only" path for A/B comparison.

    Args:
      query_species: e.g. 'Sbicolor_v3.1.1'.
      ref_species:   e.g. 'Athaliana_TAIR10'.
      orthologues_dict: {q_tr: {'og': og_id, 'orthologs': [r_tr, ...]}} from
                        orthofinder_io.load_orthologues.
      ogs: {og_id: {species: [transcript_id, ...]}} from
           orthofinder_io.load_orthogroups. Provides the OG membership needed
           to enumerate paralog candidates.
      psi_by_og: {og_id: {(t1, t2): psi}}.
      sp_gene_to_og: {(species, transcript): og_id}.
      curated_features_for_ref: {ref_gene: feature_data}.
      threshold: phylum PSI threshold, or None to apply no phylum gate (the
                 hard floor and the per-OG baseline / fallback still apply).
      admit_paralogs: whether to admit PAM / PAH paralogs. Default True.
      fallback_baseline: threshold for PAH when no OG baseline exists (default 0.5).
      hard_floor: absolute PSI below which a pair is refused whatever OF called
                  it (default ORTHOLOG_PSI_HARD_FLOOR). Pass 0.0 to disable.
      rejected_report: optional list collecting one dict per floor rejection.

    Returns:
      annotations: {query_gene: annotate_query_gene() result} for every
                   query gene with at least one curated candidate.
      stats:  Counter of annotation statuses across all annotated calls.
      pair_stats: Counter of pair-level tags actually kept
                  ({'O': N, 'PAM': N, 'PAH': N}), plus 'FLOOR' counting pairs
                  refused by the hard floor. FLOOR rides in pair_stats rather
                  than a fourth return value so existing callers surface it
                  without a signature change.
    """
    tg = _oio.transcript_to_gene

    # Compute per-OG baseline over OF-called ortholog pairs (query <-> ref).
    og_baselines = compute_og_baselines(
        orthologues_dict, psi_by_og, sp_gene_to_og, query_species, ref_species,
    )

    # Precompute OF ortholog pair sets per OG (used inside classify_og_pairs).
    ortholog_pairs_by_og = defaultdict(set)
    for q_tr, entry in orthologues_dict.items():
        og_id = entry.get("og") or sp_gene_to_og.get((query_species, q_tr))
        if og_id is None:
            continue
        for r_tr in entry.get("orthologs", []):
            ortholog_pairs_by_og[og_id].add(frozenset({q_tr, r_tr}))

    # Walk every OG containing both query and ref transcripts and classify.
    # Accumulate accepted (q_tr, r_tr, psi, tag) candidates keyed by query gene.
    per_query_gene = defaultdict(list)  # {q_gene: [(r_tr, psi, tag), ...]}
    pair_stats = Counter()
    for og_id, per_spp in ogs.items():
        q_transcripts = per_spp.get(query_species) or []
        r_transcripts = per_spp.get(ref_species) or []
        if not q_transcripts or not r_transcripts:
            continue
        psi_map = psi_by_og.get(og_id)
        if not psi_map:
            continue
        baseline = og_baselines.get(og_id)
        of_pairs = ortholog_pairs_by_og.get(og_id, set())

        if admit_paralogs:
            floor_rejects = []
            accepted = classify_og_pairs(
                og_id, q_transcripts, r_transcripts, of_pairs, psi_map,
                baseline, fallback_baseline,
                hard_floor=hard_floor, rejected_report=floor_rejects,
            )
            pair_stats["FLOOR"] += len(floor_rejects)
            if rejected_report is not None:
                rejected_report.extend(floor_rejects)
        else:
            # OF-orthologs-only path (the pre-Processing_v2 behavior). The hard
            # floor applies here too — this branch is exactly where an OF call
            # is trusted unconditionally, so it is where an artifact pair would
            # otherwise sail straight through.
            accepted = []
            for pair in of_pairs:
                q_tr, r_tr = sorted(pair)
                p = psi_map.get(_pair_key(q_tr, r_tr))
                if p is None:
                    continue
                # of_pairs is a set of frozenset — need to keep pair direction
                # aligned with query/ref for downstream aggregation.
                if q_tr in q_transcripts and r_tr in r_transcripts:
                    fwd = (q_tr, r_tr)
                elif r_tr in q_transcripts and q_tr in r_transcripts:
                    fwd = (r_tr, q_tr)
                else:
                    continue
                if p < hard_floor:
                    pair_stats["FLOOR"] += 1
                    if rejected_report is not None:
                        rejected_report.append({
                            "og": og_id, "query": fwd[0], "ref": fwd[1],
                            "psi": p, "tag": "O",
                            "reason": "below-ortholog-psi-hard-floor",
                            "floor": hard_floor,
                        })
                    continue
                accepted.append((fwd[0], fwd[1], p, "O"))

        for q_tr, r_tr, psi, tag in accepted:
            pair_stats[tag] += 1
            per_query_gene[tg(q_tr)].append((r_tr, psi, tag))

    # Per query gene: aggregate ref transcripts to ref genes.
    #
    # For each (query_gene, ref_gene) pair we track BOTH the max PSI seen
    # across any accepted pair AND the "best" tag: O outranks PA*. This
    # matters at the filtering step below — O-tagged candidates skip the
    # phylum threshold; PA*-tagged candidates must clear it.
    annotations = {}
    stats = Counter()
    for q_gene, cand_list in per_query_gene.items():
        ref_gene_best = {}   # {ref_gene: (max_psi, has_o_support)}
        for r_tr, psi, tag in cand_list:
            r_gene = tg(r_tr)
            if r_gene not in curated_features_for_ref:
                continue
            cur_psi, cur_has_o = ref_gene_best.get(r_gene, (-1.0, False))
            new_psi = max(cur_psi, psi)
            new_has_o = cur_has_o or (tag == "O")
            ref_gene_best[r_gene] = (new_psi, new_has_o)

        # Split-filter: O-supported candidates unconditionally, PA*-only
        # candidates only if they clear the phylum threshold.
        filtered_psi = {}
        for r_gene, (p, has_o) in ref_gene_best.items():
            if has_o or threshold is None:
                filtered_psi[r_gene] = p
            elif p >= threshold:
                filtered_psi[r_gene] = p

        if not filtered_psi:
            stats["NO_ORTHOLOG"] += 1
            annotations[q_gene] = {"top_ortholog": None, "function": None,
                                    "psi": None, "status": "NO_ORTHOLOG"}
            continue

        def _lookup(_q, ref, _m=filtered_psi):
            return _m.get(ref)

        # threshold=None: we already applied the split-filter above; don't
        # re-apply a uniform threshold that would drop the low-PSI-but-O
        # candidates we deliberately kept.
        result = annotate_query_gene(
            q_gene, list(filtered_psi.keys()), _lookup, None,
            curated_features_for_ref, ref_species,
        )
        annotations[q_gene] = result
        stats[result["status"]] += 1
        # Sub-count of ANNOTATED: how many ANNOTATED calls came from
        # merging tied same-enzyme hits (FIX_AMBHIT_ROLE_UNION_260812).
        if result.get("merged_from"):
            stats["MERGED_COMPARTMENTS"] += 1

    return annotations, stats, pair_stats


# ----------------------------------------------------------------------------
# Two-layer conservation-gradient report (diagnostic; see module docstring)
# ----------------------------------------------------------------------------

#: relmax bands for Layer 2 (confidence-given-presence). Explicitly arbitrary,
#: round numbers chosen for communicability -- NOT fitted or validated
#: thresholds, and NOT used anywhere as an accept/reject rule. See
#: REPORT_orthofunctional_conservation_gradient.md "What we are and aren't
#: claiming" and the module docstring above re: SWEEP_relmax_2026-09-28.md.
CONFIDENT_RELMAX   = 0.90
AMBIGUOUS_RELMAX   = 0.70


def _relmax_band(relmax):
    if relmax >= CONFIDENT_RELMAX:
        return "confident"
    if relmax >= AMBIGUOUS_RELMAX:
        return "ambiguous"
    return "no_confident_match"


def _curated_ref_gene_index(curated_features_for_ref, sp_gene_to_og, ref_species):
    """Return (gene_ogs, gene_transcripts) for every curated ref gene.

    gene_ogs:         {ref_gene: {og_id, ...}}          -- usually one OG,
                       a set in case a gene's transcripts ever split across
                       more than one (multi-transcript genes are rare here
                       but not impossible).
    gene_transcripts: {ref_gene: [transcript_id, ...]}  -- this gene's own
                       ref-species transcript ids, so Layer 2 doesn't
                       accidentally score against some OTHER curated gene
                       sharing the same orthogroup.
    """
    tg = _oio.transcript_to_gene
    gene_ogs = defaultdict(set)
    gene_transcripts = defaultdict(list)
    for (spp, transcript), og_id in sp_gene_to_og.items():
        if spp != ref_species:
            continue
        g = tg(transcript)
        if g not in curated_features_for_ref:
            continue
        gene_ogs[g].add(og_id)
        gene_transcripts[g].append(transcript)
    return gene_ogs, gene_transcripts


def compute_presence_rates(curated_features_for_ref, gene_ogs, ogs, query_species):
    """Layer 1: does the query species have >=1 gene in the SAME FULL,
    UNFILTERED orthogroup as this curated ref gene, independent of PSI
    entirely?

    `ogs` must be the complete Orthogroups.tsv parse (orthofinder_io.
    load_orthogroups's return value) -- NOT pre-restricted to the
    PSI-computable subset the way cli.py's `curated_ogs` filter does for
    the PSI cache. That restriction is exactly the survivorship-bias trap
    this layer exists to avoid measuring around (see
    REPORT_orthofunctional_conservation_gradient.md and
    SWEEP_relmax_2026-09-28.md §6-7): a gene whose OG was never scored for
    PSI still has a well-defined presence answer here.

    Returns {ref_gene: bool}.
    """
    presence = {}
    for ref_gene in curated_features_for_ref:
        ogids = gene_ogs.get(ref_gene) or set()
        presence[ref_gene] = any(
            (ogs.get(og_id, {}).get(query_species) or []) for og_id in ogids
        )
    return presence


def compute_relmax_confidence(curated_features_for_ref, gene_ogs, gene_transcripts,
                              ogs, psi_by_og, query_species, ref_species,
                              orthologues_dict):
    """Layer 2: for curated genes with a PSI-computable orthogroup, relmax =
    (best PSI over THIS ref gene's own OrthoFinder-CALLED ortholog pair(s)
    with query_species) / (the highest PSI achieved by ANY OrthoFinder-
    CALLED ortholog pair between query_species and ref_species anywhere in
    that same orthogroup) -- matching
    REPORT_orthofunctional_conservation_gradient.md's definition ("its best
    PSI divided by the highest PSI seen among any ortholog in that same
    orthogroup") and SWEEP_relmax_2026-09-28.md's DIST[]/best[] construction:
    numerator and denominator are BOTH restricted to OF-called pairs; they
    differ only in scope (this gene's own OF pairs vs. every OF pair in the
    OG). Both come from `compute_og_baselines`, which already exists for
    exactly this "OF-ortholog PSI ceiling of an OG" computation -- the
    denominator at percentile=1.0 over the whole OG, the numerator at
    percentile=1.0 scoped to a single ref gene's transcripts.

    Three real bugs lived here before this restriction was applied
    uniformly, all found by mismatching SWEEP_relmax_2026-09-28.md's
    numbers on Poplar (which should be reproducible from this function):

    1. denominator = max(psi_map.values()) over the WHOLE per-OG matrix,
       i.e. all 23 reference-build species -- an unrelated high-identity
       pair (two near-identical grass cultivars sharing the OG) silently
       deflated relmax for every OTHER species pair sharing that OG (3%
       "confident" for Poplar instead of the validated 82%).
    2. denominator = best over every query<->ref pair regardless of OF's
       call -- a paralog with higher raw PSI than the true ortholog would
       inflate the ceiling and make the real ortholog call look worse than
       it is.
    3. numerator = best over every query transcript against this ref gene's
       transcripts, again regardless of OF's call -- lets an unrelated
       same-OG paralog (never linked to this ref gene by OrthoFinder) stand
       in for "this gene's own best hit," which can push relmax over 1.0 (a
       nonsensical result for a communication band built to top out at 1.0).

    `orthologues_dict` is the query->ref OrthoFinder call map (same shape
    orthofinder_io.load_orthologues returns and annotate_species consumes).

    Only reachable for ref genes whose OG is a key in `psi_by_og` -- callers
    normally pass the PSI cache already restricted to curated OGs (cli.py's
    `curated_ogs` filter), which is fine for THIS layer (it only cares about
    curated genes to begin with), unlike compute_presence_rates.

    Returns {ref_gene: {'psi': float_or_None, 'relmax': float_or_None,
                        'band': 'confident'|'ambiguous'|'no_confident_match'|'no_psi'}}.
    'no_psi' covers: no OF-called ortholog pair exists for this ref gene
    with this query species (no numerator), or none exists anywhere else in
    the OG either (no denominator) -- either way there is nothing valid to
    report, so it is flagged rather than silently miscounted or divided by
    a wrong number.
    """
    # Denominator: OG-wide ceiling over every OF-called (query, ref) pair.
    og_ceiling = compute_og_baselines(
        orthologues_dict, psi_by_og, {}, query_species, ref_species,
        percentile=1.0,
    )
    # Numerator: same computation, but scoped one ref-transcript-set at a
    # time by filtering orthologues_dict down to entries whose ortholog list
    # touches THIS ref gene's transcripts before calling the same helper --
    # reuses compute_og_baselines rather than re-deriving its OF-pair-PSI
    # lookup logic a second time.
    out = {}
    for ref_gene in curated_features_for_ref:
        ogids = gene_ogs.get(ref_gene) or set()
        r_transcripts_here = set(gene_transcripts.get(ref_gene, []))
        scoped_orth = {
            q_tr: {"og": entry.get("og"),
                   "orthologs": [r for r in entry.get("orthologs", [])
                                 if r in r_transcripts_here]}
            for q_tr, entry in orthologues_dict.items()
            if any(r in r_transcripts_here for r in entry.get("orthologs", []))
        }
        gene_ceiling = compute_og_baselines(
            scoped_orth, psi_by_og, {}, query_species, ref_species,
            percentile=1.0,
        )
        best_psi = None
        denom = None
        for og_id in ogids:
            num = gene_ceiling.get(og_id)
            if num is not None:
                best_psi = num if best_psi is None else max(best_psi, num)
            den = og_ceiling.get(og_id)
            if den is not None:
                denom = den if denom is None else max(denom, den)
        if best_psi is None or not denom:
            out[ref_gene] = {"psi": best_psi, "relmax": None, "band": "no_psi"}
            continue
        relmax = best_psi / denom
        out[ref_gene] = {"psi": best_psi, "relmax": relmax, "band": _relmax_band(relmax)}
    return out


def _empty_gradient_bucket():
    return {
        "n_curated": 0, "n_present": 0, "presence_pct": None,
        "n_confidence_scored": 0, "no_psi": 0,
        "confident": 0, "ambiguous": 0, "no_confident_match": 0,
        "confident_pct": None, "no_confident_match_pct": None,
    }


def conservation_gradient_report(curated_features_for_ref, ogs, sp_gene_to_og,
                                 psi_by_og, query_species, ref_species,
                                 orthologues_dict):
    """Build the two-layer report from
    REPORT_orthofunctional_conservation_gradient.md for one query/ref
    species pair, split by curated role_class ('generalized' vs.
    'specialized', from propagate.build_curated_features).

    This is purely descriptive: it does not accept, reject, or reweight any
    annotation, and its output has no effect on `annotate_species`. Run it
    alongside annotate_species on the same inputs to get a distance-aware
    honesty check on the run just performed -- NOT a replacement for the
    threshold/floor/baseline logic that decides what gets annotated.

    `ogs` must be the FULL, unfiltered orthogroup parse (see
    compute_presence_rates); `psi_by_og` may be restricted to curated OGs
    (the usual cli.py shape) since Layer 2 never looks outside them anyway.
    `orthologues_dict` is the query->ref OrthoFinder call map (same shape
    cli.py already loads via orthofinder_io.load_orthologues, and the same
    argument annotate_species takes) -- Layer 2's relmax denominator needs
    it to know which pairs OrthoFinder actually called orthologs; see
    compute_relmax_confidence's docstring for why that restriction matters.

    Returns:
        {
          "query_species": ..., "ref_species": ...,
          "summary": {"generalized": {...}, "specialized": {...}},
          "presence":   {ref_gene: bool},
          "confidence": {ref_gene: {'psi', 'relmax', 'band'}},
        }
    """
    gene_ogs, gene_transcripts = _curated_ref_gene_index(
        curated_features_for_ref, sp_gene_to_og, ref_species,
    )
    presence = compute_presence_rates(curated_features_for_ref, gene_ogs, ogs, query_species)
    confidence = compute_relmax_confidence(
        curated_features_for_ref, gene_ogs, gene_transcripts,
        ogs, psi_by_og, query_species, ref_species, orthologues_dict,
    )

    summary = {"generalized": _empty_gradient_bucket(),
               "specialized": _empty_gradient_bucket()}
    for ref_gene, entry in curated_features_for_ref.items():
        role_class = entry.get("role_class", "generalized")
        bucket = summary.setdefault(role_class, _empty_gradient_bucket())
        bucket["n_curated"] += 1
        if not presence.get(ref_gene):
            continue
        bucket["n_present"] += 1
        band = confidence.get(ref_gene, {}).get("band", "no_psi")
        if band == "no_psi":
            bucket["no_psi"] += 1
        else:
            bucket["n_confidence_scored"] += 1
            bucket[band] += 1

    for bucket in summary.values():
        if bucket["n_curated"]:
            bucket["presence_pct"] = 100.0 * bucket["n_present"] / bucket["n_curated"]
        if bucket["n_confidence_scored"]:
            bucket["confident_pct"] = 100.0 * bucket["confident"] / bucket["n_confidence_scored"]
            bucket["no_confident_match_pct"] = (
                100.0 * bucket["no_confident_match"] / bucket["n_confidence_scored"]
            )

    return {
        "query_species": query_species,
        "ref_species":   ref_species,
        "summary":       summary,
        "presence":      presence,
        "confidence":    confidence,
    }
