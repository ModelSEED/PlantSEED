"""plantseed_curation — shared library backing Curation_Tool.py,
Curation_Tool_Dashboard.py, and Update_Enzymes_in_PlantSEED.py.

Both the CLI and the dashboard funnel through the same validate_payload /
build_tsv_rows / run_apply functions so they produce byte-identical TSV
rows for the same curator inputs.
"""

from . import (
    actions,
    cli_io,
    constants,
    curator_files,
    expasy,
    identity,
    paths,
    schema,
    search,
    store,
)

# Commonly-used names at top level so callers can do
# `from plantseed_curation import build_tsv_rows, ranked_search`.
from .actions import (
    apply_actions,
    assign_complex_kbase_id,
    assign_kbase_id,
    build_tsv_rows,
    complex_kbase_id,
    derive_new_complexes,
    enzyme_index_from_complexes,
    enzyme_rxn_cpts,
    parse_tsv_text,
    preview_for_enzyme,
    run_apply,
    seed_new_entries,
    validate_payload,
    validate_subcomplex_pointers,
)
from .cli_io import Console, ExitRequested
from .constants import (
    ACTION_DESCRIPTIONS,
    ACTION_FIELDS,
    ACTION_MIN_COLS,
    ACTION_OPTIONS,
    AUTO_POPULATED_FIELDS,
    COMPARTMENT_IDS,
    COMPARTMENTS,
    DEFAULT_COMPARTMENT,
    DEFAULT_LOC_SOURCE,
    DEPRECATED_REASSIGN_ALIASES,
    EXIT_SHORTCUT,
    MULTI_COL_FIELDS,
    SCALAR_TYPES,
)
from .curator_files import (
    append_curator_file,
    curator_dir_path,
    delete_curator_file,
    list_all_curators,
    list_curator_files,
    parse_tsv_to_rows,
    read_curator_file,
    write_curator_file,
)
from .identity import (
    atomic_write,
    confirm_curator_registry,
    detect_github_username,
    get_git_email,
    get_git_username,
    load_curator_registry,
    normalize_existing_dirname,
    sanitize_filename,
    sanitize_username,
    save_curator_registry,
)
from .schema import (
    IssueCollector,
    default_role_from_schema,
    ensure_schema_defaults,
    load_schema,
    required_empty_fields,
    validate_dependencies,
)
from .search import (
    FIELD_PREFIXES,
    find_exact_match,
    find_substring_match,
    fuzzy_match,
    parse_query,
    ranked_search,
    search_features,
)
from .store import DataStore

__all__ = [
    # subpackages
    "actions", "cli_io", "constants", "curator_files", "expasy",
    "identity", "paths", "schema", "search", "store",
    # actions
    "apply_actions", "assign_complex_kbase_id", "assign_kbase_id",
    "build_tsv_rows", "complex_kbase_id", "derive_new_complexes",
    "enzyme_index_from_complexes", "enzyme_rxn_cpts", "parse_tsv_text",
    "preview_for_enzyme", "run_apply", "seed_new_entries",
    "validate_payload", "validate_subcomplex_pointers",
    # cli_io
    "Console", "ExitRequested",
    # constants
    "ACTION_DESCRIPTIONS", "ACTION_FIELDS", "ACTION_MIN_COLS", "ACTION_OPTIONS",
    "AUTO_POPULATED_FIELDS", "COMPARTMENT_IDS", "COMPARTMENTS",
    "DEFAULT_COMPARTMENT", "DEFAULT_LOC_SOURCE", "DEPRECATED_REASSIGN_ALIASES",
    "EXIT_SHORTCUT", "MULTI_COL_FIELDS", "SCALAR_TYPES",
    # curator_files
    "append_curator_file", "curator_dir_path", "delete_curator_file",
    "list_all_curators", "list_curator_files", "parse_tsv_to_rows",
    "read_curator_file", "write_curator_file",
    # identity
    "atomic_write", "confirm_curator_registry", "detect_github_username",
    "get_git_email", "get_git_username", "load_curator_registry",
    "normalize_existing_dirname", "sanitize_filename", "sanitize_username",
    "save_curator_registry",
    # schema
    "IssueCollector", "default_role_from_schema", "ensure_schema_defaults",
    "load_schema", "required_empty_fields", "validate_dependencies",
    # search
    "FIELD_PREFIXES", "find_exact_match", "find_substring_match",
    "fuzzy_match", "parse_query", "ranked_search", "search_features",
    # store
    "DataStore",
]
