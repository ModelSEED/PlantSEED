"""Offline scripts that build a versioned refdata bundle under
<BUNDLE_ROOT>/<version>/.

Runs on poplar (has SHOOT, OrthoFinder, DIAMOND, MAFFT + the compute), not
inside the KBase SDK container (too big, wrong host).

Order (Phase 1):
  1. build_orthofinder_db       — baseline OrthoFinder MSA-mode run over Phytozome
  2. build_shoot_db             — SHOOT database from that OrthoFinder run
  3. enrich_with_curated_proteins — SHOOT-place each non-Arabidopsis PlantSEED-
                                    curated UniProt protein into its OG's fasta+MSA+tree
  4. build_psi_matrices         — per-OG pairwise sequence identity over enriched families
  5. stamp_version              — write manifest.json + finalize the bundle dir

Distribution (Phase 6):
  Bundle build is triggered by a GitHub Action on merges to dev that touch
  Data/PlantSEED_v3/PlantSEED_Roles.json or PlantSEED_Complexes.json, via
  a webhook to a poplar-side listener that invokes stamp_version's CLI.
"""
