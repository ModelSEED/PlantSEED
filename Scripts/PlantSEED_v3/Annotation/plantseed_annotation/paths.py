"""Filesystem paths used by the annotator.

Every path is overridable via a PLANTSEED_ANNOT_* environment variable so the
test suite (and any caller pinning a specific bundle version) can point the
package at an alternative location without touching the module source.

Mirrors the layout / conventions of plantseed_curation.paths — see that
module for the pattern rationale.
"""

import os


def _env(name, default):
    return os.environ.get(name, default)


# This package lives at Scripts/PlantSEED_v3/Annotation/plantseed_annotation/.
# Climb four levels to reach the repo root (where Data/ lives).
_HERE = os.path.dirname(os.path.abspath(__file__))
_ANNOTATION_ROOT = os.path.dirname(_HERE)
_REPO_ROOT = os.path.normpath(os.path.join(_ANNOTATION_ROOT, "..", "..", ".."))


# Refdata bundle location. Populated at Phase 1 by refbuild/ scripts; consumed
# by reference.py + algorithms/* at annotation time.
#
# Default points at /kb/data (the KBase refdata NFS mount that poplar
# already has). Override via env for local dev.
BUNDLE_ROOT = _env(
    "PLANTSEED_ANNOT_BUNDLE_ROOT",
    "/kb/data/plantseed_annotation",
)
BUNDLE_VERSION = _env("PLANTSEED_ANNOT_BUNDLE_VERSION", "latest")
BUNDLE_DIR = _env(
    "PLANTSEED_ANNOT_BUNDLE_DIR",
    os.path.join(BUNDLE_ROOT, BUNDLE_VERSION),
)

# Curation source-of-truth files this package reads at bundle build time.
# Default is co-located inside the repo (Data/PlantSEED_v3/) so refbuild
# can run offline on a fresh clone.
ROLES_FILE = _env(
    "PLANTSEED_ANNOT_ROLES_FILE",
    os.path.join(_REPO_ROOT, "Data", "PlantSEED_v3", "PlantSEED_Roles.json"),
)
COMPLEXES_FILE = _env(
    "PLANTSEED_ANNOT_COMPLEXES_FILE",
    os.path.join(_REPO_ROOT, "Data", "PlantSEED_v3", "PlantSEED_Complexes.json"),
)


def refresh_from_env():
    """Re-read paths from the environment. Tests call this after setting
    PLANTSEED_ANNOT_* env vars in a fixture so the module-level constants
    reflect the new values."""
    global BUNDLE_ROOT, BUNDLE_VERSION, BUNDLE_DIR, ROLES_FILE, COMPLEXES_FILE
    BUNDLE_ROOT = _env("PLANTSEED_ANNOT_BUNDLE_ROOT", "/kb/data/plantseed_annotation")
    BUNDLE_VERSION = _env("PLANTSEED_ANNOT_BUNDLE_VERSION", "latest")
    BUNDLE_DIR = _env(
        "PLANTSEED_ANNOT_BUNDLE_DIR",
        os.path.join(BUNDLE_ROOT, BUNDLE_VERSION),
    )
    ROLES_FILE = _env(
        "PLANTSEED_ANNOT_ROLES_FILE",
        os.path.join(_REPO_ROOT, "Data", "PlantSEED_v3", "PlantSEED_Roles.json"),
    )
    COMPLEXES_FILE = _env(
        "PLANTSEED_ANNOT_COMPLEXES_FILE",
        os.path.join(_REPO_ROOT, "Data", "PlantSEED_v3", "PlantSEED_Complexes.json"),
    )
