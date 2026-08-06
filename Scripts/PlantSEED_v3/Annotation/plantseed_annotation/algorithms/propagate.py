"""Top ortholog -> PlantSEED function record.

Given a top_ortholog (from psi_refined) and the bundle's cached curation
lookup, emit both:
  - the legacy `role # compartment` string (so unchanged plant_fba
    reconstruction consumes it as-is during the transition)
  - the new `PS_role_*` stable id list (for the v2 reconstructor)

Arabidopsis-vs-other-species agnostic — the enriched bundle put curated
non-Arabidopsis proteins into the reference at refbuild time, so a top
ortholog from Sorghum or a curated moss carries the same weight here as
one from Arabidopsis.
"""
