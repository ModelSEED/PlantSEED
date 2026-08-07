"""Finalize a bundle directory by writing its `manifest.json`.

Composes the bundle version key (see manifest_schema.json) from:
  - PlantSEED_Roles.json git SHA (from repo `git rev-parse HEAD -- Data/PlantSEED_v3/PlantSEED_Roles.json`)
  - Phytozome release used for the baseline OrthoFinder run
  - SHOOT DB build id (from create_shoot_db.py output)
  - Tool versions: OrthoFinder, DIAMOND, MAFFT, SHOOT, EPA-ng, MSA

Also records:
  - SHA-256 of every file in the bundle (for verify())
  - Bundle total size (for the per-tier refdata_gb_max check)
  - List of curated non-Arabidopsis proteins added via SHOOT this run
  - Delta vs previous bundle version (proteins added, dropped, resequenced)

Consumed at annotation time by reference.load_manifest / reference.verify.

Filled in at Phase 1.
"""
