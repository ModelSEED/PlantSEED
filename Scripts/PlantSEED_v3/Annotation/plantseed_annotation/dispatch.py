"""Choose the algorithm chain for a given (genome, tier) pair.

Primary path (all tiers):
  place_query.run(...)  ->  psi_refined.identify_orthologs(...)  ->
  propagate.function_from(...)

Fast path (kbase tier only, once bundle grows past 10 GB):
  kmer.annotate(...)  as pre-filter, escalate to primary path only for
  proteins the kmer index couldn't confidently call.

Per-phylum defaults from phylum_thresholds.json in the bundle; caller can
override via config for A/B experiments.
"""
