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
def test_compute_og_baselines_mean_over_of_orthologs():
    """Baseline for an OG = arithmetic mean over OF-called ortholog PSI values
    between the query and ref species in that OG."""
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
    assert b["OG0000001"] == (0.80 + 0.60) / 2   # 0.70


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
