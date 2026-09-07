"""The curation payload: everything derived from PlantSEED_Roles.json.

The annotator needs the curated-feature index and the per-phylum PSI
thresholds, and both are derivations of files in the repository. Materialising
them into the bundle rather than reading the repository at run time is what
lets a KBase container — which has the bundle mounted and no checkout — do the
same work, and what pins an annotation to one curation vintage.

Both files go through `bundle.write_json`, so a rebuild from the same roles
file is byte-identical.
"""

from __future__ import annotations

import os

from .. import paths
from ..algorithms import propagate
from . import bundle

__all__ = ["build", "CURATED_FEATURES", "PHYLUM_THRESHOLDS"]

CURATED_FEATURES = "curated_features.json"
PHYLUM_THRESHOLDS = "phylum_thresholds.json"


def build(bundle_dir, roles_data=None, log=print) -> dict:
    """Write the curation payload. Returns a summary for the manifest."""
    out_dir = os.path.join(bundle.ensure_layout(bundle_dir), bundle.CURATION_DIR)

    features = propagate.build_curated_features(roles_data=roles_data)
    # Nested species -> gene -> data, because the in-memory index is keyed by
    # a (species, gene) tuple and JSON has no tuple keys. Same grouping the
    # annotator wants anyway.
    by_species = propagate.curated_features_by_source_species(features)
    bundle.write_json(os.path.join(out_dir, CURATED_FEATURES), by_species)

    bundle.write_json(os.path.join(out_dir, PHYLUM_THRESHOLDS),
                      dict(paths.PHYLUM_THRESHOLDS_DEFAULT))

    log(f"[curation] {len(features)} curated features across "
        f"{len(by_species)} species -> {out_dir}")
    return {
        "curation_dir": out_dir,
        "curated_features": len(features),
        "curated_species": len(by_species),
    }
