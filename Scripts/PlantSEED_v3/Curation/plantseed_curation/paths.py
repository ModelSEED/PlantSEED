"""Filesystem paths used by the curation tool.

Every path is overridable via a PLANTSEED_* environment variable so the test
suite (and any other caller) can point the whole package at a temporary copy
of the database without touching the real files.
"""

import os
import tempfile


def _env(name, default):
    return os.environ.get(name, default)


# The curation scripts live in Scripts/PlantSEED_v3/Curation/. This package
# sits next to them. Climb one directory to get the curation root, then up
# three more for the repo root (where Data/ lives).
_HERE = os.path.dirname(os.path.abspath(__file__))
_CURATION_ROOT = os.path.dirname(_HERE)
_REPO_ROOT = os.path.normpath(os.path.join(_CURATION_ROOT, "..", "..", ".."))


BASE_DIR = _env("PLANTSEED_BASE_DIR", _CURATION_ROOT)
ROLES_FILE = _env(
    "PLANTSEED_ROLES_FILE",
    os.path.join(_REPO_ROOT, "Data", "PlantSEED_v3", "PlantSEED_Roles.json"),
)
COMPLEXES_FILE = _env(
    "PLANTSEED_COMPLEXES_FILE",
    os.path.join(_REPO_ROOT, "Data", "PlantSEED_v3", "PlantSEED_Complexes.json"),
)
SCHEMA_FILE = _env("PLANTSEED_SCHEMA_FILE", os.path.join(BASE_DIR, "PlantSEED_Schema.yaml"))
CURATORS_DIR = _env("PLANTSEED_CURATORS_DIR", os.path.join(BASE_DIR, "Curators"))
CURATOR_REGISTRY = _env(
    "PLANTSEED_CURATOR_REGISTRY", os.path.join(CURATORS_DIR, "curator_registry.json")
)

ENZYME_DAT_URL = _env(
    "PLANTSEED_ENZYME_DAT_URL", "https://ftp.expasy.org/databases/enzyme/enzyme.dat"
)
ENZYME_DAT_CACHE = _env(
    "PLANTSEED_ENZYME_DAT_CACHE", os.path.join(tempfile.gettempdir(), "plantseed_enzyme.dat")
)


def refresh_from_env():
    """Re-read paths from the environment. Tests call this after setting
    PLANTSEED_* env vars in a fixture so the module-level constants reflect
    the new values."""
    global BASE_DIR, ROLES_FILE, COMPLEXES_FILE, SCHEMA_FILE, CURATORS_DIR, CURATOR_REGISTRY
    global ENZYME_DAT_URL, ENZYME_DAT_CACHE
    BASE_DIR = _env("PLANTSEED_BASE_DIR", _CURATION_ROOT)
    ROLES_FILE = _env(
        "PLANTSEED_ROLES_FILE",
        os.path.join(_REPO_ROOT, "Data", "PlantSEED_v3", "PlantSEED_Roles.json"),
    )
    COMPLEXES_FILE = _env(
        "PLANTSEED_COMPLEXES_FILE",
        os.path.join(_REPO_ROOT, "Data", "PlantSEED_v3", "PlantSEED_Complexes.json"),
    )
    SCHEMA_FILE = _env("PLANTSEED_SCHEMA_FILE", os.path.join(BASE_DIR, "PlantSEED_Schema.yaml"))
    CURATORS_DIR = _env("PLANTSEED_CURATORS_DIR", os.path.join(BASE_DIR, "Curators"))
    CURATOR_REGISTRY = _env(
        "PLANTSEED_CURATOR_REGISTRY", os.path.join(CURATORS_DIR, "curator_registry.json")
    )
    ENZYME_DAT_URL = _env(
        "PLANTSEED_ENZYME_DAT_URL", "https://ftp.expasy.org/databases/enzyme/enzyme.dat"
    )
    ENZYME_DAT_CACHE = _env(
        "PLANTSEED_ENZYME_DAT_CACHE",
        os.path.join(tempfile.gettempdir(), "plantseed_enzyme.dat"),
    )
