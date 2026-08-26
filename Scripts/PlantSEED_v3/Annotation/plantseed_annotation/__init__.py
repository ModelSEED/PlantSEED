"""plantseed_annotation — shared library for the plant genome annotator.

Public API (Phase 1a): the standalone annotator that consumes a user's
OrthoFinder results directory + PlantSEED_Roles.json and produces an
annotated genome JSON in the shape plantseed_model/reconstruct.py consumes.

    from plantseed_annotation import (
        build_curated_features, annotate_species, write_annotated_genome,
    )
"""

from . import config, genome_io, paths
from .algorithms import orthofinder_io, propagate, psi, psi_refined

from .algorithms.propagate import (
    COMPARTMENT_MAPPING,
    build_curated_features,
    curated_features_by_source_species,
    function_for_ortholog,
)
from .algorithms.psi_refined import (
    annotate_query_gene,
    annotate_species,
)
from .algorithms.psi import (
    cache_search_path,
    compute_psi_for_msa,
    ensure_psi_cache,
    load_psi_for_ogs,
)
from .algorithms.orthofinder_io import (
    load_orthogroups,
    load_orthologues,
    orthologues_path,
    read_msa,
    species_from_orthogroups,
    species_gene_to_og_index,
)
from .genome_io import (
    build_annotated_genome,
    write_annotated_genome,
)

__all__ = [
    # subpackages
    "config", "genome_io", "paths",
    "orthofinder_io", "propagate", "psi", "psi_refined",
    # propagate
    "COMPARTMENT_MAPPING", "build_curated_features",
    "curated_features_by_source_species", "function_for_ortholog",
    # psi_refined
    "annotate_query_gene", "annotate_species",
    # psi
    "cache_search_path", "compute_psi_for_msa", "ensure_psi_cache",
    "load_psi_for_ogs",
    # orthofinder_io
    "load_orthogroups", "load_orthologues", "orthologues_path",
    "read_msa", "species_from_orthogroups", "species_gene_to_og_index",
    # genome_io
    "build_annotated_genome", "write_annotated_genome",
]
