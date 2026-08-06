"""Place a query genome's proteins into the enriched OrthoFinder families.

Default: OrthoFinder `-b` insert mode against the pre-computed enriched
families in <BUNDLE_DIR>/orthofinder_families_enriched/. Wraps the same
subprocess pattern kb_orthofinder currently uses.

Follow-up: DIAMOND-first placement for a faster path once the algorithm is
validated (skips MAFFT + tree-build for OGs where DIAMOND is confident).
"""
