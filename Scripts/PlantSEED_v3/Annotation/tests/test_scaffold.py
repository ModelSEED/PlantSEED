"""Sanity tests for the scaffold — every module imports cleanly and the
paths + config surfaces behave the way conftest fixtures expect.

Real behavior tests land as each algorithm / refbuild step comes online in
Phases 1-3.
"""

import json
import os

import pytest


def test_package_imports_cleanly():
    """Every module in the package tree imports without side effects."""
    import plantseed_annotation
    for sub in ("paths", "config", "reference", "dispatch", "genome_io",
                "emit", "cli"):
        assert hasattr(plantseed_annotation, sub) or __import__(
            f"plantseed_annotation.{sub}", fromlist=[sub]
        )


def test_public_api_exports_are_all_importable():
    """Every name in __all__ actually resolves."""
    import plantseed_annotation as psa
    for name in psa.__all__:
        assert hasattr(psa, name), f"__all__ names {name!r} but attribute is missing"


def test_algorithms_and_refbuild_import():
    for m in ("place_query", "psi_refined", "propagate", "kmer"):
        __import__(f"plantseed_annotation.algorithms.{m}", fromlist=[m])
    for m in ("build_orthofinder_db", "build_shoot_db",
              "enrich_with_curated_proteins", "build_psi_matrices",
              "stamp_version"):
        __import__(f"plantseed_annotation.refbuild.{m}", fromlist=[m])


def test_tmp_bundle_fixture_sets_env(tmp_bundle):
    """Confirm the fixture wired the PLANTSEED_ANNOT_* env vars and that
    paths refreshed to point at the tmp bundle, not /kb/data."""
    from plantseed_annotation import paths as p
    assert p.BUNDLE_ROOT == tmp_bundle["root"]
    assert p.BUNDLE_VERSION == tmp_bundle["version"]
    assert p.BUNDLE_DIR == tmp_bundle["dir"]
    assert os.path.isdir(p.BUNDLE_DIR)


def test_config_tier_names():
    from plantseed_annotation import config
    assert set(config.BY_NAME) == {"kbase", "poplar", "local"}
    kb = config.get("kbase")
    assert kb.ram_gb_max == 22
    assert kb.cpu_max == 2
    assert kb.refdata_gb_max == 10
    with pytest.raises(ValueError):
        config.get("nope")


def test_manifest_schema_is_valid_json():
    schema_path = os.path.join(
        os.path.dirname(__file__), "..", "plantseed_annotation",
        "refbuild", "manifest_schema.json",
    )
    with open(schema_path) as f:
        schema = json.load(f)
    assert schema["title"].startswith("plantseed_annotation")
    assert schema["properties"]["schema_version"]["const"] == 1
    for req in ("bundle_version", "sources", "tool_versions", "contents",
                "totals", "curated_non_arabidopsis"):
        assert req in schema["required"]
