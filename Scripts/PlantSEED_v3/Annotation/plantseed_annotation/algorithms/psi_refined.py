"""PSI-refined ortholog resolution — port of
`~/Seq_Home/PlantSEED_Processing_v2/Identify_Functional_Homologs.py` as a
library.

Given a query protein placed in an orthogroup (by place_query) plus the
OG's members and its precomputed PSI matrix, pick the top curated ortholog
using:
  - per-species-pair mean PSI as the ortholog/paralog boundary
  - per-phylum threshold (from phylum_thresholds.json in the bundle) as the
    final propagation cutoff

Returns a top_ortholog record or a "no confident call" marker for
downstream propagate.py.
"""
