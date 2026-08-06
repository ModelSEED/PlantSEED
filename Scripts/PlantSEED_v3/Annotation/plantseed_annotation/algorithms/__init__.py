"""Pluggable annotation algorithms.

  place_query  — put a query genome's proteins into the enriched OrthoFinder
                 families (default: OrthoFinder -b insert mode against the
                 bundle; possible follow-up: DIAMOND-first placement)
  psi_refined  — port of Identify_Functional_Homologs.py; picks the top curated
                 ortholog per query using per-species-pair PSI mean + phylum
                 threshold
  propagate    — top ortholog -> PlantSEED function/compartment string and
                 PS_role_* stable id; source-species agnostic
  kmer         — 8-mer signature match (fast path, ported from ProbModelSEED)
"""
