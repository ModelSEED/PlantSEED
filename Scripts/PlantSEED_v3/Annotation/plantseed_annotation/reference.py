"""Locate + verify the versioned refdata bundle at annotation time.

A bundle directory contains everything the annotator needs to place a
query genome's proteins into the enriched OrthoFinder families and
propagate PlantSEED functions:

    <BUNDLE_DIR>/
      manifest.json
      orthofinder_families_enriched/
      shoot_db/
      psi_matrices/
      curation/
      phylum_thresholds.json
      uniprot_sequences.faa

Filled in at Phase 1 (refbuild) and consumed at Phase 2 (algorithms).
"""

# Phase-2 stubs — implementations land as the algorithms come online.
def load_manifest(bundle_dir=None):
    raise NotImplementedError("Phase 1: implement manifest load + version pin")


def verify(bundle_dir=None):
    """Return (ok: bool, issues: [str]) for the bundle at `bundle_dir`.
    Checks manifest present, hashes match, expected subdirs exist,
    total size <= tier refdata_gb_max."""
    raise NotImplementedError("Phase 1: implement bundle integrity check")
