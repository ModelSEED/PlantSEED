"""Compute per-OG pairwise sequence identity matrices over the enriched
families, keyed by every member (Arabidopsis + curated non-Arabidopsis
proteins alike).

Port of `~/Seq_Home/PlantSEED_Processing_v2/Calculate_Pairwise_Sequence_Identity.py`
into a library callable, with the enriched families as input rather than
raw OrthoFinder output.

Output: `<BUNDLE_DIR>/psi_matrices/OG*.tsv` — one file per OG. Consumed
at annotation time by algorithms.psi_refined.

Filled in at Phase 1.
"""
