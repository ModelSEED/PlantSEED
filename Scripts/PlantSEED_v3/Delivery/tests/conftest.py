"""Shared fixtures for the delivery tests.

Mirrors the pattern in the other three suites: make the package importable
without installation, and give any test that touches module state a way to
start clean.
"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
DELIVERY_ROOT = os.path.dirname(HERE)
sys.path.insert(0, DELIVERY_ROOT)

#: The repo root, for the preprint artifacts the reconstruction tests use.
REPO_ROOT = os.path.normpath(os.path.join(DELIVERY_ROOT, "..", "..", ".."))
PAPER = os.path.join(REPO_ROOT, "Papers", "bioflux-preprint-260807")
GENOME = os.path.join(PAPER, "Athaliana_TAIR10_annotated_genome.json")

HAVE_GENOME = os.path.isfile(GENOME)


@pytest.fixture(autouse=True)
def clean_query_cache():
    """The query module caches a DataStore for the process lifetime, which is
    the point in production and a cross-test leak here."""
    from plantseed_delivery import queries

    queries.reset_cache()
    yield
    queries.reset_cache()


@pytest.fixture(autouse=True)
def declared_mounts(tmp_path, monkeypatch):
    """Declare both roots for every test.

    OUTPUT_ENV is not optional here. Per-call artifacts land under the output
    root, which defaults to the cwd — so without this the suite writes model
    JSON into whatever directory pytest was started from. It did, once.

    Setting OUTPUT_ENV also turns runtime.strict_mode() on, which is the state
    the container runs in, so the tests exercise the enforced path rather than
    the permissive one.
    """
    from plantseed_core import runtime

    monkeypatch.setenv(runtime.OUTPUT_ENV, str(tmp_path / "output"))
    monkeypatch.setenv(runtime.SCRATCH_ENV, str(tmp_path / "scratch"))
