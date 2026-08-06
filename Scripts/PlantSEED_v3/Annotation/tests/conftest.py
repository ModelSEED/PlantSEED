"""Shared pytest fixtures for the plantseed_annotation test suite.

Mirrors the pattern from plantseed_curation/tests/conftest.py: every test
that mutates state gets a tmp bundle directory hierarchy plus
PLANTSEED_ANNOT_* env vars pointing at it. The library re-reads those env
vars via paths.refresh_from_env() so nothing touches a real /kb/data bundle.
"""

import os
import sys

import pytest


# Make the package importable without installation.
HERE = os.path.dirname(os.path.abspath(__file__))
ANNOTATION_ROOT = os.path.dirname(HERE)
sys.path.insert(0, ANNOTATION_ROOT)

FIXTURES = os.path.join(HERE, "fixtures")


@pytest.fixture
def tmp_bundle(tmp_path, monkeypatch):
    """Per-test tmp bundle root. Returns a dict with 'root', 'version', 'dir'.

    The bundle 'dir' is empty on creation; individual tests populate the
    manifest.json / subdirs they need. reference.verify() should be able to
    diagnose the empty bundle as invalid — that's the negative-case test.
    """
    bundle_root = str(tmp_path / "bundle_root")
    bundle_version = "vTEST"
    bundle_dir = os.path.join(bundle_root, bundle_version)
    os.makedirs(bundle_dir, exist_ok=True)

    monkeypatch.setenv("PLANTSEED_ANNOT_BUNDLE_ROOT",    bundle_root)
    monkeypatch.setenv("PLANTSEED_ANNOT_BUNDLE_VERSION", bundle_version)
    monkeypatch.setenv("PLANTSEED_ANNOT_BUNDLE_DIR",     bundle_dir)

    from plantseed_annotation import paths as p
    p.refresh_from_env()
    yield {"root": bundle_root, "version": bundle_version, "dir": bundle_dir}
    p.refresh_from_env()


# Placeholder for a shared standalone-genome fixture (a small Arabidopsis
# minimal genome for round-trip tests). Wired up at Phase 1 when
# genome_io.load exists.
