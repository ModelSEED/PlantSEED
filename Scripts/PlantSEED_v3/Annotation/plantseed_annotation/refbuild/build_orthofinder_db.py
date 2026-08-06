"""Baseline OrthoFinder MSA-mode run on the Phytozome reference species
set, producing per-OG fastas + MSAs + gene trees.

Wraps the same OrthoFinder command kb_orthofinder currently runs; output
goes to `<BUNDLE_DIR>/orthofinder_families_enriched/` (before enrichment)
or a tmp dir that `enrich_with_curated_proteins` then mutates in place.

Filled in at Phase 1.
"""
