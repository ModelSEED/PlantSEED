"""psi_refined — ortholog resolution + tie-break rules ported from
kb_orthofinderImpl.propagate_annotation."""

import pytest

from plantseed_annotation.algorithms import psi_refined as pr


CURATED = {
    "AT1": {"function":     "Alpha (EC 1.1.1.1) # cytosol",
            "roles":        ["Alpha (EC 1.1.1.1)"],
            "compartments": ["c"]},
    "AT2": {"function":     "Beta (EC 2.2.2.2) # plastid",
            "roles":        ["Beta (EC 2.2.2.2)"],
            "compartments": ["d"]},
    # AT3: same role/compartment as AT1 (identical role sets → merge cleanly)
    "AT3": {"function":     "Alpha (EC 1.1.1.1) # cytosol",
            "roles":        ["Alpha (EC 1.1.1.1)"],
            "compartments": ["c"]},
    # AT4: same role as AT1 but extra compartment (identical role sets →
    # merge with unioned compartments per FIX_AMBHIT_ROLE_UNION_260812)
    "AT4": {"function":     "Alpha (EC 1.1.1.1) # cytosol # plastid",
            "roles":        ["Alpha (EC 1.1.1.1)"],
            "compartments": ["c", "d"]},
    # AT_UNANN represents a ref gene that isn't in the curated set —
    # function is empty, so annotate_query_gene's curated_top filter drops it.
    "AT_UNANN": {"function": ""},
}


def _psi_of(mapping):
    """Turn a dict of {ref_gene: psi} into the psi_lookup_fn shape used
    by annotate_query_gene."""
    def _lookup(query, ref, _m=mapping):
        return _m.get(ref)
    return _lookup


def test_annotate_no_orthologs():
    r = pr.annotate_query_gene(
        "Q1", [], _psi_of({}), 0.5, CURATED, "Athaliana_TAIR10",
    )
    assert r["status"] == "NO_ORTHOLOG"
    assert r["function"] is None


def test_annotate_all_below_threshold():
    r = pr.annotate_query_gene(
        "Q1", ["AT1", "AT2"], _psi_of({"AT1": 0.30, "AT2": 0.40}),
        threshold=0.60, curated_features_for_ref=CURATED, ref_species="Athaliana_TAIR10",
    )
    assert r["status"] == "LT_THRESHOLD"
    assert r["psi"] == 0.40
    assert r["function"] is None


def test_annotate_unique_top_ref():
    r = pr.annotate_query_gene(
        "Q1", ["AT1", "AT2"], _psi_of({"AT1": 0.85, "AT2": 0.70}),
        threshold=0.60, curated_features_for_ref=CURATED, ref_species="Athaliana_TAIR10",
    )
    assert r["status"] == "ANNOTATED"
    assert r["top_ortholog"] == ("Athaliana_TAIR10", "AT1")
    assert r["function"] == "Alpha (EC 1.1.1.1) # cytosol"
    assert r["psi"] == 0.85


def test_tie_break_same_function_arbitrary_pick():
    """Two refs tied at top PSI with the same role set → merge cleanly.
    top_ortholog names the alphabetically-first of the merged set;
    merged_from lists both."""
    r = pr.annotate_query_gene(
        "Q1", ["AT1", "AT3"], _psi_of({"AT1": 0.80, "AT3": 0.80}),
        threshold=0.60, curated_features_for_ref=CURATED, ref_species="Athaliana_TAIR10",
    )
    assert r["status"] == "ANNOTATED"
    assert r["function"] == "Alpha (EC 1.1.1.1) # cytosol"
    assert r["top_ortholog"] == ("Athaliana_TAIR10", "AT1")
    assert r["merged_from"] == ["AT1", "AT3"]


def test_tie_break_unannotated_vs_annotated_picks_annotated():
    """AT_UNANN represents an uncurated ref (function=''), which
    curated_top filters out before merge. Only AT1 remains → ANNOTATED.
    No merge, so merged_from is None."""
    r = pr.annotate_query_gene(
        "Q1", ["AT_UNANN", "AT1"], _psi_of({"AT_UNANN": 0.80, "AT1": 0.80}),
        threshold=0.60, curated_features_for_ref=CURATED, ref_species="Athaliana_TAIR10",
    )
    assert r["status"] == "ANNOTATED"
    assert r["top_ortholog"] == ("Athaliana_TAIR10", "AT1")
    assert r["function"] == "Alpha (EC 1.1.1.1) # cytosol"
    assert r["merged_from"] is None


def test_tie_break_same_role_different_compartments_merges_with_union():
    """AT1 (roles=[Alpha], compartments=[c]) and AT4 (roles=[Alpha],
    compartments=[c, d]) have identical role sets but differ on compartments.
    Under FIX_AMBHIT_ROLE_UNION_260812 they merge; compartments are the
    union so the propagated function keeps both."""
    r = pr.annotate_query_gene(
        "Q1", ["AT1", "AT4"], _psi_of({"AT1": 0.80, "AT4": 0.80}),
        threshold=0.60, curated_features_for_ref=CURATED, ref_species="Athaliana_TAIR10",
    )
    assert r["status"] == "ANNOTATED"
    assert r["function"] == "Alpha (EC 1.1.1.1) # cytosol # plastid"
    assert r["merged_from"] == ["AT1", "AT4"]


def test_tie_break_two_distinct_functions_ambiguous():
    """Two refs tied at top PSI with two DIFFERENT non-substring functions
    → status AMB_HIT, no propagation."""
    r = pr.annotate_query_gene(
        "Q1", ["AT1", "AT2"], _psi_of({"AT1": 0.80, "AT2": 0.80}),
        threshold=0.60, curated_features_for_ref=CURATED, ref_species="Athaliana_TAIR10",
    )
    assert r["status"] == "AMB_HIT"
    assert r["function"] is None


def test_tie_break_three_distinct_functions_ambiguous():
    """More than two distinct role sets that are neither identical nor
    nested → still AMB_HIT after the merge-based tie-break."""
    curated = dict(CURATED)
    curated["AT5"] = {"function":     "Gamma (EC 3.3.3.3)",
                      "roles":        ["Gamma (EC 3.3.3.3)"],
                      "compartments": ["c"]}
    r = pr.annotate_query_gene(
        "Q1", ["AT1", "AT2", "AT5"],
        _psi_of({"AT1": 0.80, "AT2": 0.80, "AT5": 0.80}),
        threshold=0.60, curated_features_for_ref=curated,
        ref_species="Athaliana_TAIR10",
    )
    assert r["status"] == "AMB_HIT"


def test_annotate_species_end_to_end_shape():
    """annotate_species walks OGs, classifies pairs, and emits one entry per
    query GENE (aggregating transcripts) with a curated candidate."""
    orth = {
        "Q1.1": {"og": "OG0000001", "orthologs": ["AT1"]},   # OF ortholog
        "Q3.1": {"og": "OG0000003", "orthologs": ["AT1", "AT3"]},   # same fn → OK
    }
    ogs = {
        "OG0000001": {"Sbicolor_v3.1.1": ["Q1.1"],
                      "Athaliana_TAIR10": ["AT1", "AT2"]},
        "OG0000002": {"Sbicolor_v3.1.1": ["Q2.1"],
                      "Athaliana_TAIR10": ["AT_UNCURATED"]},
        "OG0000003": {"Sbicolor_v3.1.1": ["Q3.1"],
                      "Athaliana_TAIR10": ["AT1", "AT3"]},
    }
    psi_by_og = {
        "OG0000001": {("AT1", "Q1.1"): 0.80, ("AT2", "Q1.1"): 0.65},
        "OG0000002": {("AT_UNCURATED", "Q2.1"): 0.70},
        "OG0000003": {("AT1", "Q3.1"): 0.75, ("AT3", "Q3.1"): 0.75},
    }
    sp_to_og = {("Sbicolor_v3.1.1", "Q1.1"): "OG0000001",
                ("Sbicolor_v3.1.1", "Q2.1"): "OG0000002",
                ("Sbicolor_v3.1.1", "Q3.1"): "OG0000003",
                ("Athaliana_TAIR10", "AT1"): "OG0000001",
                ("Athaliana_TAIR10", "AT2"): "OG0000001",
                ("Athaliana_TAIR10", "AT_UNCURATED"): "OG0000002",
                ("Athaliana_TAIR10", "AT3"): "OG0000003"}
    annotations, stats, pair_stats = pr.annotate_species(
        "Sbicolor_v3.1.1", "Athaliana_TAIR10", orth,
        ogs, psi_by_og, sp_to_og, CURATED, threshold=0.60,
    )
    # Q1, Q2, Q3 all appear as candidates in ogs. Q2's AT_UNCURATED
    # ortholog is filtered out at the curation gate, so Q2 gets status
    # NO_ORTHOLOG (candidate seen but no curated ref survives).
    assert set(annotations) == {"Q1", "Q2", "Q3"}
    assert annotations["Q1"]["status"] == "ANNOTATED"
    assert annotations["Q1"]["top_ortholog"] == ("Athaliana_TAIR10", "AT1")
    assert annotations["Q3"]["status"] == "ANNOTATED"
    assert annotations["Q2"]["status"] == "NO_ORTHOLOG"
    assert stats["ANNOTATED"] == 2
    assert stats["NO_ORTHOLOG"] == 1


def test_annotate_species_admits_paralog_above_baseline():
    """The Processing_v2 core: a paralog (not called ortholog by OF) whose
    PSI exceeds the per-OG baseline is admitted as an annotation candidate.
    This is precisely what the naive OF-orthologs-only path misses."""
    # OG has two Ath curated genes (AT1, AT2) and one query gene (Q1)
    # OF only calls AT1↔Q1 as ortholog. AT2 is a paralog in the same OG.
    #   Baseline PSI = mean over OF orthologs = PSI(AT1, Q1.1) = 0.80
    #   PSI(AT2, Q1.1) = 0.85 > 0.80  → admit AT2 as PAM
    #   Since AT2 has higher PSI, it becomes the top candidate.
    orth = {
        "Q1.1": {"og": "OG0000001", "orthologs": ["AT1"]},   # only AT1 called ortholog
    }
    ogs = {
        "OG0000001": {"Sbicolor_v3.1.1": ["Q1.1"],
                      "Athaliana_TAIR10": ["AT1", "AT2"]},
    }
    psi_by_og = {
        "OG0000001": {
            ("AT1", "Q1.1"): 0.80,   # OF ortholog → sets baseline = 0.80
            ("AT2", "Q1.1"): 0.85,   # paralog, above baseline → admit as PAM
        },
    }
    sp_to_og = {("Sbicolor_v3.1.1", "Q1.1"): "OG0000001",
                ("Athaliana_TAIR10", "AT1"): "OG0000001",
                ("Athaliana_TAIR10", "AT2"): "OG0000001"}
    curated = {
        "AT1": {"function": "Alpha # cytosol"},
        "AT2": {"function": "Beta # plastid"},
    }
    annotations, stats, pair_stats = pr.annotate_species(
        "Sbicolor_v3.1.1", "Athaliana_TAIR10", orth,
        ogs, psi_by_og, sp_to_og, curated, threshold=0.60,
    )
    # Both AT1 (O, 0.80) and AT2 (PAM, 0.85) are candidates; AT2 has strictly
    # higher PSI so wins the top slot outright — no tie, so no AMB_HIT.
    # This is the whole point: paralog admission changes the top ortholog
    # from AT1 (what naive OF gave us) to AT2 (what PSI actually supports).
    assert pair_stats["O"] == 1
    assert pair_stats["PAM"] == 1
    assert annotations["Q1"]["status"] == "ANNOTATED"
    assert annotations["Q1"]["top_ortholog"] == ("Athaliana_TAIR10", "AT2")
    assert annotations["Q1"]["function"] == "Beta # plastid"
    assert annotations["Q1"]["psi"] == 0.85

    # Compare against admit_paralogs=False: only AT1 is a candidate → AT1 wins,
    # a different (potentially wrong) annotation is propagated.
    ann_naive, _, pair_stats_naive = pr.annotate_species(
        "Sbicolor_v3.1.1", "Athaliana_TAIR10", orth,
        ogs, psi_by_og, sp_to_og, curated, threshold=0.60,
        admit_paralogs=False,
    )
    assert pair_stats_naive.get("PAM", 0) == 0
    assert ann_naive["Q1"]["status"] == "ANNOTATED"
    assert ann_naive["Q1"]["top_ortholog"] == ("Athaliana_TAIR10", "AT1")
    assert ann_naive["Q1"]["function"] == "Alpha # cytosol"


def test_annotate_species_paralog_rejected_below_baseline():
    """A paralog below the baseline is dropped (PRM), so if OF called no
    ortholog for the query, the paralog can't propagate."""
    orth = {
        "Q1.1": {"og": "OG0000001", "orthologs": ["AT2"]},   # OF ortholog: only AT2
    }
    ogs = {
        "OG0000001": {"Sbicolor_v3.1.1": ["Q1.1"],
                      "Athaliana_TAIR10": ["AT1", "AT2"]},
    }
    psi_by_og = {
        "OG0000001": {
            ("AT2", "Q1.1"): 0.80,   # OF ortholog → baseline = 0.80
            ("AT1", "Q1.1"): 0.65,   # paralog, BELOW baseline → PRM (reject)
        },
    }
    sp_to_og = {("Sbicolor_v3.1.1", "Q1.1"): "OG0000001",
                ("Athaliana_TAIR10", "AT1"): "OG0000001",
                ("Athaliana_TAIR10", "AT2"): "OG0000001"}
    curated = {
        "AT1": {"function": "Alpha # cytosol"},
        "AT2": {"function": "Beta # plastid"},
    }
    annotations, stats, pair_stats = pr.annotate_species(
        "Sbicolor_v3.1.1", "Athaliana_TAIR10", orth,
        ogs, psi_by_og, sp_to_og, curated, threshold=0.60,
    )
    assert pair_stats.get("O", 0) == 1
    assert pair_stats.get("PAM", 0) == 0
    assert annotations["Q1"]["top_ortholog"] == ("Athaliana_TAIR10", "AT2")


def test_annotate_species_fallback_baseline_pah():
    """No OF orthologs in an OG for (query, ref) → fall back to 0.5.
    Paralogs above 0.5 get tagged PAH and accepted."""
    orth = {}   # No OF orthologs in the whole run
    ogs = {
        "OG0000001": {"Sbicolor_v3.1.1": ["Q1.1"],
                      "Athaliana_TAIR10": ["AT1"]},
    }
    psi_by_og = {
        "OG0000001": {("AT1", "Q1.1"): 0.75},  # no OF ortholog, > 0.5 fallback
    }
    sp_to_og = {("Sbicolor_v3.1.1", "Q1.1"): "OG0000001",
                ("Athaliana_TAIR10", "AT1"): "OG0000001"}
    curated = {"AT1": {"function": "Alpha # cytosol"}}
    annotations, stats, pair_stats = pr.annotate_species(
        "Sbicolor_v3.1.1", "Athaliana_TAIR10", orth,
        ogs, psi_by_og, sp_to_og, curated, threshold=0.60,
    )
    assert pair_stats.get("PAH", 0) == 1
    assert pair_stats.get("O", 0) == 0
    assert annotations["Q1"]["status"] == "ANNOTATED"


def test_annotate_species_threshold_none_applies_no_phylum_gate():
    """threshold=None skips the phylum gate; the fallback baseline still applies."""
    ogs = {"OG1": {"Q": ["Q1.1", "Q2.1"], "Athaliana_TAIR10": ["AT1"]}}
    psi_by_og = {"OG1": {("AT1", "Q1.1"): 0.55, ("AT1", "Q2.1"): 0.45}}
    sp_to_og = {("Q", "Q1.1"): "OG1", ("Q", "Q2.1"): "OG1"}
    curated = {"AT1": {"function": "Alpha # cytosol"}}

    gated, _, _ = pr.annotate_species(
        "Q", "Athaliana_TAIR10", {}, ogs, psi_by_og, sp_to_og, curated, threshold=0.60)
    ungated, _, _ = pr.annotate_species(
        "Q", "Athaliana_TAIR10", {}, ogs, psi_by_og, sp_to_og, curated, threshold=None)

    assert gated["Q1"]["status"] == "NO_ORTHOLOG"
    assert ungated["Q1"]["status"] == "ANNOTATED"
    assert "Q2" not in ungated   # 0.45 is below the 0.5 fallback baseline


def test_annotate_species_aggregates_multi_transcript_max_psi():
    """Two transcripts of the same query gene, each with an ortholog to the
    same ref gene. PSI(query_gene, ref_gene) = MAX over the transcript pairs."""
    orth = {
        "Q1.1": {"og": "OG0000001", "orthologs": ["AT1.1"]},
        "Q1.2": {"og": "OG0000001", "orthologs": ["AT1.2"]},
    }
    ogs = {"OG0000001": {"Sbicolor_v3.1.1": ["Q1.1", "Q1.2"],
                          "Athaliana_TAIR10": ["AT1.1", "AT1.2"]}}
    psi_by_og = {
        "OG0000001": {
            ("AT1.1", "Q1.1"): 0.65,
            ("AT1.2", "Q1.2"): 0.80,   # this one wins
            ("AT1.1", "Q1.2"): 0.55,
            ("AT1.2", "Q1.1"): 0.60,
        },
    }
    sp_to_og = {
        ("Sbicolor_v3.1.1", "Q1.1"): "OG0000001",
        ("Sbicolor_v3.1.1", "Q1.2"): "OG0000001",
        ("Athaliana_TAIR10", "AT1.1"): "OG0000001",
        ("Athaliana_TAIR10", "AT1.2"): "OG0000001",
    }
    curated = {"AT1": {"function": "Alpha # cytosol"}}
    annotations, stats, _ = pr.annotate_species(
        "Sbicolor_v3.1.1", "Athaliana_TAIR10", orth,
        ogs, psi_by_og, sp_to_og, curated, threshold=0.60,
    )
    assert set(annotations) == {"Q1"}
    assert annotations["Q1"]["status"] == "ANNOTATED"
    assert annotations["Q1"]["psi"] == 0.80
    assert annotations["Q1"]["top_ortholog"] == ("Athaliana_TAIR10", "AT1")


# --- compute_og_baselines + classify_og_pairs (Processing_v2 primitives) ------
def test_compute_og_baselines_percentile_over_of_orthologs():
    """Baseline for an OG = the BASELINE_PERCENTILE quantile over OF-called
    ortholog PSI values between the query and ref species in that OG.

    Was the arithmetic mean until the 10th percentile measured strictly
    better on the experimentally-evidenced in-paralog benchmark: same
    precision, 1.7x the recall."""
    orth = {
        "Q1.1": {"og": "OG0000001", "orthologs": ["AT1"]},
        "Q2.1": {"og": "OG0000001", "orthologs": ["AT2"]},
    }
    psi_by_og = {"OG0000001": {
        ("AT1", "Q1.1"): 0.80,
        ("AT2", "Q2.1"): 0.60,
        # Not an OF ortholog — should NOT contribute to the baseline
        ("AT1", "Q2.1"): 0.90,
    }}
    sp_to_og = {}
    b = pr.compute_og_baselines(orth, psi_by_og, sp_to_og,
                                 "Sbicolor_v3.1.1", "Athaliana_TAIR10")
    assert b["OG0000001"] == 0.60          # low end, not the 0.70 mean
    # At the top of the distribution the answer must still be 0.80: if the
    # 0.90 non-ortholog ever leaked in, this is where it would show.
    top = pr.compute_og_baselines(orth, psi_by_og, sp_to_og,
                                   "Sbicolor_v3.1.1", "Athaliana_TAIR10",
                                   percentile=1.0)
    assert top["OG0000001"] == 0.80


def test_compute_og_baselines_percentile_is_overridable():
    """The quantile is a parameter, defaulting to BASELINE_PERCENTILE."""
    orth = {f"Q{i}.1": {"og": "OG1", "orthologs": [f"AT{i}"]} for i in range(1, 11)}
    psi_by_og = {"OG1": {("AT%d" % i, "Q%d.1" % i): i / 10.0 for i in range(1, 11)}}
    got = {q: pr.compute_og_baselines(orth, psi_by_og, {}, "Q", "R",
                                       percentile=q)["OG1"]
           for q in (0.0, 0.10, 0.50, 1.0)}
    assert got == {0.0: 0.1, 0.10: 0.2, 0.50: 0.6, 1.0: 1.0}
    assert pr.BASELINE_PERCENTILE == 0.10


def test_compute_og_baselines_single_ortholog_pair():
    """An OG with one ortholog pair yields that pair's PSI rather than
    raising — most orthogroups carry only a handful of pairs."""
    orth = {"Q1.1": {"og": "OG1", "orthologs": ["AT1"]}}
    b = pr.compute_og_baselines(orth, {"OG1": {("AT1", "Q1.1"): 0.42}}, {},
                                 "Q", "R")
    assert b["OG1"] == 0.42


def test_compute_og_baselines_missing_when_no_of_orthologs():
    """OGs with no OF ortholog pair (for this query↔ref) don't appear in
    the baseline dict."""
    orth = {}
    psi_by_og = {"OG0000001": {("AT1", "Q1.1"): 0.90}}
    b = pr.compute_og_baselines(orth, psi_by_og, {},
                                 "Sbicolor_v3.1.1", "Athaliana_TAIR10")
    assert "OG0000001" not in b


def test_classify_og_pairs_tag_matrix():
    """Every case: O (OF ortholog), PAM (paralog above mean), PRM (below),
    PAH (paralog above fallback when no baseline), PRH (below fallback)."""
    q_tr = ["Q1"]
    r_tr = ["AT1", "AT2", "AT3"]
    of_pairs = {frozenset({"Q1", "AT1"})}
    psi_map = {
        pr._pair_key("Q1", "AT1"): 0.80,   # OF ortholog → O
        pr._pair_key("Q1", "AT2"): 0.85,   # paralog above 0.80 → PAM
        pr._pair_key("Q1", "AT3"): 0.50,   # paralog below 0.80 → PRM (rejected, not returned)
    }
    accepted = pr.classify_og_pairs(
        "OG_", q_tr, r_tr, of_pairs, psi_map, baseline=0.80,
    )
    tags = {(a, b, t) for (a, b, _p, t) in accepted}
    assert ("Q1", "AT1", "O") in tags
    assert ("Q1", "AT2", "PAM") in tags
    # AT3 rejected → not in the returned list
    assert not any(t == "AT3" for (a, b, _p, _tag) in accepted for t in (a, b))

    # No baseline available → use fallback 0.5.
    of_pairs_none = set()
    accepted2 = pr.classify_og_pairs(
        "OG_", q_tr, r_tr, of_pairs_none, psi_map,
        baseline=None, fallback_baseline=0.5,
    )
    tags2 = {(a, b, t) for (a, b, _p, t) in accepted2}
    assert ("Q1", "AT1", "PAH") in tags2
    assert ("Q1", "AT2", "PAH") in tags2
    # AT3 at exactly 0.5 → PRH, rejected (strict > comparison, matches Processing_v2)
    assert not any(a == "Q1" and b == "AT3" for (a, b, _p, _t) in accepted2)


# --- Two-layer conservation-gradient report (diagnostic) ---------------------
# See REPORT_orthofunctional_conservation_gradient.md and the module
# docstring: presence rate (Layer 1) must be measured over the FULL,
# unfiltered orthogroup set, never the PSI-computable subset, or the
# survivorship-bias artifact the split exists to avoid reappears.

GRADIENT_CURATED = {
    # Present in query, high relmax → confident, generalized.
    "AT_GEN_HIGH": {"function": "Gen1", "role_class": "generalized"},
    # Present in query, low relmax → no_confident_match, generalized.
    "AT_GEN_LOW":  {"function": "Gen2", "role_class": "generalized"},
    # NOT present in query at all (no gene in its OG for the query species).
    "AT_GEN_ABS":  {"function": "Gen3", "role_class": "generalized"},
    # Present, but its OG never got a PSI matrix (Layer 1 yes, Layer 2 no_psi).
    "AT_GEN_NOPSI": {"function": "Gen4", "role_class": "generalized"},
    # Specialized-metabolism gene, present, mid relmax → ambiguous.
    "AT_SPEC_MID": {"function": "Spec1", "role_class": "specialized"},
}

# Full, UNFILTERED orthogroup set (mirrors load_orthogroups' shape).
GRADIENT_OGS = {
    "OG_GEN_HIGH": {"Sbicolor_v3.1.1": ["Q1.1"], "Athaliana_TAIR10": ["AT_GEN_HIGH.1"]},
    # Two Sorghum paralogs in this OG (Q2.1, Q2_OTHER.1) -- OTHER scores much
    # higher against the same curated ref gene, so it sets the OG's ceiling.
    # This is exactly the "a promiscuous family's best hit isn't the one
    # being scored" case relmax is meant to catch.
    "OG_GEN_LOW":  {"Sbicolor_v3.1.1": ["Q2.1", "Q2_OTHER.1"], "Athaliana_TAIR10": ["AT_GEN_LOW.1"]},
    "OG_GEN_ABS":  {"Sbicolor_v3.1.1": [],       "Athaliana_TAIR10": ["AT_GEN_ABS.1"]},
    "OG_GEN_NOPSI": {"Sbicolor_v3.1.1": ["Q4.1"], "Athaliana_TAIR10": ["AT_GEN_NOPSI.1"]},
    "OG_SPEC_MID": {"Sbicolor_v3.1.1": ["Q5.1"], "Athaliana_TAIR10": ["AT_SPEC_MID.1"]},
}

GRADIENT_SP_TO_OG = {
    ("Sbicolor_v3.1.1", "Q1.1"): "OG_GEN_HIGH",
    ("Athaliana_TAIR10", "AT_GEN_HIGH.1"): "OG_GEN_HIGH",
    ("Sbicolor_v3.1.1", "Q2.1"): "OG_GEN_LOW",
    ("Sbicolor_v3.1.1", "Q2_OTHER.1"): "OG_GEN_LOW",
    ("Athaliana_TAIR10", "AT_GEN_LOW.1"): "OG_GEN_LOW",
    ("Athaliana_TAIR10", "AT_GEN_ABS.1"): "OG_GEN_ABS",
    ("Sbicolor_v3.1.1", "Q4.1"): "OG_GEN_NOPSI",
    ("Athaliana_TAIR10", "AT_GEN_NOPSI.1"): "OG_GEN_NOPSI",
    ("Sbicolor_v3.1.1", "Q5.1"): "OG_SPEC_MID",
    ("Athaliana_TAIR10", "AT_SPEC_MID.1"): "OG_SPEC_MID",
}

# PSI only covers a SUBSET of the OGs above (OG_GEN_NOPSI deliberately
# missing) -- mirrors cli.py restricting the PSI cache to curated OGs, and
# exercises the 'no_psi' band.
#
# OG_GEN_LOW deliberately has a HIGHER-scoring pair (Q2_OTHER.1, 0.80) that
# is NOT an OF-called ortholog (see GRADIENT_ORTHOLOGUES below) -- this is
# the case compute_relmax_confidence's docstring warns about: the
# denominator must come from OF-called pairs only, or a stray high-PSI
# paralog would inflate the ceiling and make the real (OF-called, low-PSI)
# ortholog look artificially worse than it is. With the OF-restriction,
# relmax = 0.20/0.20 = 1.0 -> confident, not 0.20/0.80 = 0.25.
GRADIENT_PSI_BY_OG = {
    "OG_GEN_HIGH": {("AT_GEN_HIGH.1", "Q1.1"): 0.95},
    "OG_GEN_LOW":  {("AT_GEN_LOW.1", "Q2.1"): 0.20,
                    ("AT_GEN_LOW.1", "Q2_OTHER.1"): 0.80},
    "OG_SPEC_MID": {("AT_SPEC_MID.1", "Q5.1"): 0.75},
}

# OrthoFinder's own ortholog calls: Q2.1 IS called an ortholog of
# AT_GEN_LOW.1; Q2_OTHER.1 is NOT (it's a same-OG paralog OF didn't call).
GRADIENT_ORTHOLOGUES = {
    "Q1.1": {"og": "OG_GEN_HIGH", "orthologs": ["AT_GEN_HIGH.1"]},
    "Q2.1": {"og": "OG_GEN_LOW",  "orthologs": ["AT_GEN_LOW.1"]},
    "Q5.1": {"og": "OG_SPEC_MID", "orthologs": ["AT_SPEC_MID.1"]},
}


def test_compute_presence_rates_uses_full_unfiltered_ogs():
    gene_ogs, _ = pr._curated_ref_gene_index(
        GRADIENT_CURATED, GRADIENT_SP_TO_OG, "Athaliana_TAIR10",
    )
    presence = pr.compute_presence_rates(
        GRADIENT_CURATED, gene_ogs, GRADIENT_OGS, "Sbicolor_v3.1.1",
    )
    assert presence["AT_GEN_HIGH"] is True
    assert presence["AT_GEN_LOW"] is True
    assert presence["AT_GEN_ABS"] is False   # no query gene in OG_GEN_ABS
    assert presence["AT_GEN_NOPSI"] is True  # present even though no PSI exists
    assert presence["AT_SPEC_MID"] is True


def test_compute_relmax_confidence_bands_and_no_psi():
    gene_ogs, gene_transcripts = pr._curated_ref_gene_index(
        GRADIENT_CURATED, GRADIENT_SP_TO_OG, "Athaliana_TAIR10",
    )
    confidence = pr.compute_relmax_confidence(
        GRADIENT_CURATED, gene_ogs, gene_transcripts,
        GRADIENT_OGS, GRADIENT_PSI_BY_OG,
        "Sbicolor_v3.1.1", "Athaliana_TAIR10",
        GRADIENT_ORTHOLOGUES,
    )
    assert confidence["AT_GEN_HIGH"]["band"] == "confident"
    assert confidence["AT_GEN_HIGH"]["relmax"] == pytest.approx(1.0)
    # Denominator is the OF-called ortholog ceiling (0.20, from Q2.1), NOT
    # the higher-scoring non-OF-called paralog (0.80, from Q2_OTHER.1) --
    # so relmax = 0.20/0.20 = 1.0, confident, despite the absolute PSI being
    # low. This is the whole point of restricting the denominator.
    assert confidence["AT_GEN_LOW"]["band"] == "confident"
    assert confidence["AT_GEN_LOW"]["relmax"] == pytest.approx(1.0)
    assert confidence["AT_GEN_LOW"]["psi"] == pytest.approx(0.20)
    assert confidence["AT_GEN_NOPSI"]["band"] == "no_psi"
    assert confidence["AT_GEN_NOPSI"]["relmax"] is None
    assert confidence["AT_SPEC_MID"]["band"] == "confident"


def test_compute_relmax_confidence_no_of_ortholog_in_og_is_no_psi():
    """An OG with PSI data but no OF-called ortholog pair for this species
    pair has no valid denominator -- reported as 'no_psi', not a divide
    against some other pair's score."""
    ogs = {"OG_X": {"Sbicolor_v3.1.1": ["Qx.1"], "Athaliana_TAIR10": ["ATX.1"]}}
    sp_to_og = {("Sbicolor_v3.1.1", "Qx.1"): "OG_X",
                ("Athaliana_TAIR10", "ATX.1"): "OG_X"}
    curated = {"ATX": {"function": "X", "role_class": "generalized"}}
    psi_by_og = {"OG_X": {("ATX.1", "Qx.1"): 0.55}}
    orth = {}   # no OF ortholog call at all for this species pair
    gene_ogs, gene_transcripts = pr._curated_ref_gene_index(curated, sp_to_og, "Athaliana_TAIR10")
    confidence = pr.compute_relmax_confidence(
        curated, gene_ogs, gene_transcripts, ogs, psi_by_og,
        "Sbicolor_v3.1.1", "Athaliana_TAIR10", orth,
    )
    assert confidence["ATX"]["band"] == "no_psi"
    assert confidence["ATX"]["relmax"] is None


def test_relmax_band_thresholds():
    assert pr._relmax_band(0.90) == "confident"
    assert pr._relmax_band(0.89999) == "ambiguous"
    assert pr._relmax_band(0.70) == "ambiguous"
    assert pr._relmax_band(0.69999) == "no_confident_match"


def test_conservation_gradient_report_end_to_end_shape():
    """Full report: presence + confidence, summarized per role_class, with
    percentages -- and confirms the report is purely additive (same inputs
    that would feed annotate_species, no shared mutable state)."""
    report = pr.conservation_gradient_report(
        GRADIENT_CURATED, GRADIENT_OGS, GRADIENT_SP_TO_OG,
        GRADIENT_PSI_BY_OG, "Sbicolor_v3.1.1", "Athaliana_TAIR10",
        GRADIENT_ORTHOLOGUES,
    )
    assert report["query_species"] == "Sbicolor_v3.1.1"
    assert report["ref_species"] == "Athaliana_TAIR10"

    gen = report["summary"]["generalized"]
    assert gen["n_curated"] == 4          # HIGH, LOW, ABS, NOPSI
    assert gen["n_present"] == 3          # ABS excluded
    assert gen["presence_pct"] == pytest.approx(75.0)
    assert gen["no_psi"] == 1             # NOPSI
    assert gen["n_confidence_scored"] == 2  # HIGH + LOW (NOPSI excluded)
    assert gen["confident"] == 2          # HIGH and LOW (OF-restricted denom) both confident
    assert gen["no_confident_match"] == 0
    assert gen["confident_pct"] == pytest.approx(100.0)

    spec = report["summary"]["specialized"]
    assert spec["n_curated"] == 1
    assert spec["n_present"] == 1
    assert spec["presence_pct"] == pytest.approx(100.0)
    assert spec["confident"] == 1

    # Explicit spot-check that per-gene detail is exposed too, not just the
    # summary -- callers may want to drill into individual genes.
    assert report["presence"]["AT_GEN_ABS"] is False
    assert report["confidence"]["AT_GEN_HIGH"]["band"] == "confident"


def test_conservation_gradient_report_is_read_only_re_annotate_species():
    """Running the gradient report alongside annotate_species on the same
    inputs must not change annotate_species's own output -- the two are
    independent views over the same data, not a shared pipeline stage."""
    orth = {"Q1.1": {"og": "OG_GEN_HIGH", "orthologs": ["AT_GEN_HIGH.1"]}}
    curated_min = {"AT_GEN_HIGH": {"function": "Gen1", "role_class": "generalized"}}
    before = pr.annotate_species(
        "Sbicolor_v3.1.1", "Athaliana_TAIR10", orth,
        GRADIENT_OGS, GRADIENT_PSI_BY_OG, GRADIENT_SP_TO_OG,
        curated_min, threshold=0.60,
    )
    pr.conservation_gradient_report(
        GRADIENT_CURATED, GRADIENT_OGS, GRADIENT_SP_TO_OG,
        GRADIENT_PSI_BY_OG, "Sbicolor_v3.1.1", "Athaliana_TAIR10",
        GRADIENT_ORTHOLOGUES,
    )
    after = pr.annotate_species(
        "Sbicolor_v3.1.1", "Athaliana_TAIR10", orth,
        GRADIENT_OGS, GRADIENT_PSI_BY_OG, GRADIENT_SP_TO_OG,
        curated_min, threshold=0.60,
    )
    assert before[0] == after[0]   # annotations
    assert before[1] == after[1]   # stats
    assert before[2] == after[2]   # pair_stats
