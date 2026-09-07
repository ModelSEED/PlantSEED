"""Offline scripts that build a versioned refdata bundle under
<BUNDLE_ROOT>/<version>/.

Runs where the compute is (poplar), not inside the KBase SDK container.

**Order, revised.** The original plan built the SHOOT-enriched reference
first and treated everything else as downstream of it. That order was wrong
for the goal: an Arabidopsis-based annotator is useful on its own, it is what
the published models were produced with, and it needs none of SHOOT,
OrthoFinder, MAFFT, EPA-ng or gappa. Enrichment adds specialized metabolism
that Arabidopsis lacks -- real value, but value that presumes a working
annotator to add it to.

So SHOOT moved to the end of the refactor, and the bundle has two vintages:

  v0 -- what `cli.build` produces today, from an existing OrthoFinder run
        1. prune              orthogroups touching a curated gene, any species
        2. write_families     copy those alignments into the bundle
        3. build_psi_matrices per-OG pairwise sequence identity
        4. build_curation     curated features + phylum thresholds
        5. stamp_version      manifest.json, content hashes, content_id

  v1 -- v0 plus SHOOT enrichment, at the END of the refactor
        build_shoot_db                SHOOT database from the OrthoFinder run
        enrich_with_curated_proteins  place each non-Arabidopsis curated
                                      protein into its orthogroup

Scale, measured rather than assumed: 32 of 1,518 curated features are
UniProt-sourced and therefore unreachable in v0. Everything else is already
in the reference run, so v0 covers 98% of the curation.

`build_orthofinder_db` stays scaffold too. Both delivered bundles so far were
built from a pre-existing run, and running OrthoFinder ourselves is a
separate concern from assembling a bundle out of one.

Distribution (Phase 6): a merge to dev touching PlantSEED_Roles.json or
PlantSEED_Complexes.json triggers a rebuild and a fresh manifest.
"""
