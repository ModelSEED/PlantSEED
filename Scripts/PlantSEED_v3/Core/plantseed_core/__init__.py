"""plantseed_core — the platform-neutral foundation of PlantSEED v3.

Everything here is pure stdlib and knows nothing about KBase, modelseed.org,
CTS, or KIND*AI. Platform adapters live in ModelSEED/plantseed-delivery and
depend on this package; the dependency never runs the other way. A CI gate
rejects any import of installed_clients, cobrakbase, DataFileUtil,
KBaseReport, SDK_CALLBACK_URL or kbutillib under Scripts/PlantSEED_v3/.

Present:

  strings   the `role1 / role2 # cpt1 # cpt2` function-string contract, and the
            guards that keep reserved delimiters out of curated role names
  runtime   the writable-root contract — output and scratch only, because every
            platform mounts reference data read-only
  errors    the exception hierarchy

Landing over Phase 0-1: types, serde + JSON Schemas, registry (@capability and
the manifest export that drives per-platform codegen), loc, idnorm, ontology,
provenance, data.
"""

from .__about__ import DATA_VERSION, __version__
from . import errors, runtime, strings
from .errors import (
    CapabilityError,
    DataVersionError,
    PlantSEEDError,
    ReservedDelimiterError,
)
from .strings import (
    COMPARTMENT_SEP,
    KBASE_FUNCTION_SEP,
    RESERVED_SUBSTRINGS,
    ROLE_SEP,
    assert_kbase_safe,
    compose_function_string,
    find_reserved,
    parse_function_string,
)

__all__ = [
    "__version__",
    "DATA_VERSION",
    # modules
    "errors",
    "runtime",
    "strings",
    # errors
    "PlantSEEDError",
    "ReservedDelimiterError",
    "DataVersionError",
    "CapabilityError",
    # the function-string contract
    "ROLE_SEP",
    "COMPARTMENT_SEP",
    "KBASE_FUNCTION_SEP",
    "RESERVED_SUBSTRINGS",
    "assert_kbase_safe",
    "find_reserved",
    "compose_function_string",
    "parse_function_string",
]
