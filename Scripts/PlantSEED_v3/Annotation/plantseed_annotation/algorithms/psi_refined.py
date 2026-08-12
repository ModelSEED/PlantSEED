"""PSI-refined ortholog + functional-homolog resolution.

Ports the algorithm from
    ~/Seq_Home/PlantSEED_Processing_v2/Identify_Functional_Homologs.py
    ~/Seq_Home/PlantSEED_Processing_v2/Process_Functional_Homologs.py

For a query species Q and a reference species R (typically Athaliana_TAIR10):

  1. For each orthogroup containing genes from both Q and R, compute a
     baseline PSI: the arithmetic mean over PSI values for OF-called
     ortholog pairs between Q and R in that OG.
       - If no OF orthologs exist for (Q, R) in this OG, fall back to 0.5.

  2. Walk every cross-species (q_transcript, r_transcript) pair in the OG
     and classify:
       - 'O'   OF-called ortholog — accept
       - 'PAM' paralog above the OG-species-pair mean — accept
       - 'PAH' paralog above the fallback 0.5 (no baseline) — accept
       - 'PRM' paralog below mean — reject
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
"""

from collections import Counter, defaultdict

from . import orthofinder_io as _oio
from . import propagate as _propagate


UNANNOTATED_LT_THRESHOLD = "Unannotated 1: LESS_THAN_THRESHOLD"
UNANNOTATED_AMB_HIT      = "Unannotated 3: AMB_HIT"
UNANNOTATED_NO_REF_HIT   = "Unannotated 4: NO_REF_HIT"

# Fallback baseline used when an OG has no OF-called ortholog pairs
# between the query and ref species (matches Processing_v2's PAH/PRH split).
DEFAULT_FALLBACK_BASELINE = 0.5


# ----------------------------------------------------------------------------
# Baseline + candidate classification (the Processing_v2 core)
# ----------------------------------------------------------------------------
def _pair_key(a, b):
    return (a, b) if a < b else (b, a)


def compute_og_baselines(orthologues_dict, psi_by_og, sp_gene_to_og,
                          query_species, ref_species):
    """Return {og_id: baseline_psi_or_None}.

    For each OG containing at least one OF-called ortholog pair between
    query_species and ref_species, the baseline is the mean PSI over those
    pairs (looked up in the per-OG PSI matrix). OGs with no OF orthologs
    (for this species pair) get None so callers know to use the fallback.

    `orthologues_dict` is the query→ref map from orthofinder_io.load_orthologues
    (transcript-level, with the '<species>||' prefix already stripped).
    """
    sums = defaultdict(float)
    counts = defaultdict(int)
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
            sums[og_id] += p
            counts[og_id] += 1
    return {og: (sums[og] / counts[og]) for og in counts}


def classify_og_pairs(og_id, q_transcripts, r_transcripts,
                       of_ortholog_pairs, psi_map, baseline,
                       fallback_baseline=DEFAULT_FALLBACK_BASELINE):
    """Classify every cross-species (q_tr, r_tr) pair in one OG.

    Args:
      og_id: the OG identifier (used only for error reporting).
      q_transcripts: iterable of query-species transcript ids in this OG.
      r_transcripts: iterable of ref-species transcript ids in this OG.
      of_ortholog_pairs: set of frozenset({q_tr, r_tr}) pairs OF called orthologs.
      psi_map: {(g1, g2): psi} for this OG (sorted-pair keys).
      baseline: mean PSI over OF orthologs for (query, ref) in this OG, or
                None if no OF orthologs exist.
      fallback_baseline: threshold to use when baseline is None (default 0.5).

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
                      fallback_baseline=DEFAULT_FALLBACK_BASELINE):
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
      threshold: phylum PSI threshold.
      admit_paralogs: whether to admit PAM / PAH paralogs. Default True.
      fallback_baseline: threshold for PAH when no OG mean exists (default 0.5).

    Returns:
      annotations: {query_gene: annotate_query_gene() result} for every
                   query gene with at least one curated candidate.
      stats:  Counter of annotation statuses across all annotated calls.
      pair_stats: Counter of pair-level tags actually kept
                  ({'O': N, 'PAM': N, 'PAH': N}). Useful for reporting how
                  much coverage the paralog admission added.
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
            accepted = classify_og_pairs(
                og_id, q_transcripts, r_transcripts, of_pairs, psi_map,
                baseline, fallback_baseline,
            )
        else:
            # OF-orthologs-only path (the pre-Processing_v2 behavior).
            accepted = []
            for pair in of_pairs:
                q_tr, r_tr = sorted(pair)
                p = psi_map.get(_pair_key(q_tr, r_tr))
                if p is None:
                    continue
                # of_pairs is a set of frozenset — need to keep pair direction
                # aligned with query/ref for downstream aggregation.
                if q_tr in q_transcripts and r_tr in r_transcripts:
                    accepted.append((q_tr, r_tr, p, "O"))
                elif r_tr in q_transcripts and q_tr in r_transcripts:
                    accepted.append((r_tr, q_tr, p, "O"))

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
            if has_o:
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
