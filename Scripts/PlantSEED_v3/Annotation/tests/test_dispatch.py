"""dispatch.annotate — the place_query -> psi_refined -> genome_io chain.

Builds a complete, hand-written synthetic bundle (families + curation +
manifest) rather than running plantseed-refbuild, so these tests exercise
exactly the contract dispatch.annotate relies on (reference.verify passing,
load_bundle_curation finding what it expects) without depending on real
PlantSEED_Roles.json content or a real OrthoFinder run.

Skipped whole-file if diamond/mafft aren't on PATH -- same guard as
test_place_query.py, which this module's happy path runs underneath.
"""

import json
import os
import shutil

import pytest

pq = pytest.importorskip("plantseed_annotation.algorithms.place_query")

DIAMOND_AVAILABLE = shutil.which(pq.DIAMOND_BIN) is not None
MAFFT_AVAILABLE = shutil.which(pq.MAFFT_BIN) is not None

pytestmark = pytest.mark.skipif(
    not (DIAMOND_AVAILABLE and MAFFT_AVAILABLE),
    reason=f"requires diamond ({pq.DIAMOND_BIN!r}) and mafft ({pq.MAFFT_BIN!r}) on PATH",
)

from plantseed_annotation import dispatch
from plantseed_annotation.refbuild import bundle as _bundle

_REF_SEQUENCE = "MKVLSTATGKTVIVGLGAAGGIGQPLSLLLKNSPLVSRLTLYDIAG"
_QUERY_SEQUENCE = "MKVLSTATGKTVIVGLGAAGGIGQPLSLLLKNSPLVSRLTLYDIAN"


@pytest.fixture
def tiny_bundle(tmp_path):
    """A complete, minimally valid bundle: one curated orthogroup, one
    curated Arabidopsis gene, phylum thresholds, and a manifest that
    reference.verify() accepts.
    """
    bundle_dir = tmp_path / "bundle"
    _bundle.ensure_layout(str(bundle_dir))

    families_dir = bundle_dir / _bundle.FAMILIES_DIR
    with open(families_dir / "OG0000001.fa", "w") as fh:
        fh.write(f">Athaliana_TAIR10||AT1G00001.1\n{_REF_SEQUENCE}\n")
        fh.write(f">Sbicolor_v3.1.1||Sobic.001G000100.1\n{_REF_SEQUENCE}\n")

    curation_dir = bundle_dir / _bundle.CURATION_DIR
    curated_features = {
        "Athaliana_TAIR10": {
            "AT1G00001": {
                "function": "Alpha dehydrogenase (EC 1.1.1.1) # cytosol",
                "roles": ["Alpha dehydrogenase (EC 1.1.1.1)"],
                "compartments": ["c"],
            },
        },
    }
    _bundle.write_json(str(curation_dir / "curated_features.json"), curated_features)
    _bundle.write_json(str(curation_dir / "phylum_thresholds.json"),
                       {"Eudicot": 0.60, "Monocot": 0.55, "Basal": 0.30})

    manifest = {
        "schema_version": 1,
        "bundle_version": "vTEST",
        "created_utc": "2026-01-01T00:00:00Z",
        "sources": {},
        "tool_versions": {},
        "curated_non_arabidopsis": [],
        "contents": {},
        "totals": {},
    }
    contents = {}
    for rel, abs_path in _bundle.iter_payload(str(bundle_dir)):
        digest, size = _bundle.sha256_file(abs_path)
        contents[rel] = {"sha256": digest, "bytes": size}
    manifest["contents"] = contents
    manifest["content_id"] = _bundle.content_id(contents)
    _bundle.write_json(str(bundle_dir / _bundle.MANIFEST), manifest)

    return str(bundle_dir)


@pytest.fixture
def query_fasta(tmp_path):
    path = tmp_path / "query.faa"
    path.write_text(f">Sbicolor_v4.0||TestGene1.1\n{_QUERY_SEQUENCE}\n")
    return str(path)


class TestLoadBundleCuration:
    def test_reads_curated_features_and_thresholds(self, tiny_bundle):
        curated_by_species, thresholds = dispatch.load_bundle_curation(tiny_bundle)
        assert "Athaliana_TAIR10" in curated_by_species
        assert "AT1G00001" in curated_by_species["Athaliana_TAIR10"]
        assert thresholds == {"Eudicot": 0.60, "Monocot": 0.55, "Basal": 0.30}

    def test_missing_curated_features_raises(self, tmp_path):
        bundle_dir = tmp_path / "empty_bundle"
        _bundle.ensure_layout(str(bundle_dir))
        with pytest.raises(FileNotFoundError):
            dispatch.load_bundle_curation(str(bundle_dir))

    def test_missing_thresholds_file_is_tolerated(self, tmp_path):
        """phylum_thresholds.json absent (an older or hand-built bundle)
        should not crash the curated-features read -- just come back empty,
        same as the file-not-found branch in load_bundle_curation."""
        bundle_dir = tmp_path / "bundle_no_thresholds"
        _bundle.ensure_layout(str(bundle_dir))
        _bundle.write_json(
            str(bundle_dir / _bundle.CURATION_DIR / "curated_features.json"),
            {"Athaliana_TAIR10": {"AT1G00001": {"function": "X"}}},
        )
        curated_by_species, thresholds = dispatch.load_bundle_curation(str(bundle_dir))
        assert curated_by_species
        assert thresholds == {}


class TestResolveThreshold:
    def test_explicit_wins(self):
        assert dispatch.resolve_threshold(
            "Eudicot", {"Eudicot": 0.60}, explicit_threshold=0.75) == 0.75

    def test_falls_back_to_bundle_table(self):
        assert dispatch.resolve_threshold("Eudicot", {"Eudicot": 0.60}) == 0.60

    def test_unknown_phylum_raises(self):
        with pytest.raises(ValueError):
            dispatch.resolve_threshold("Unknown", {"Eudicot": 0.60})

    def test_no_phylum_no_threshold_means_no_gate(self):
        assert dispatch.resolve_threshold(None, {"Eudicot": 0.60}) is None


class TestAnnotateEndToEnd:
    def test_annotates_a_near_identical_query_against_curated_ortholog(
            self, tiny_bundle, query_fasta):
        genome = dispatch.annotate(
            query_fasta, tiny_bundle, "Sbicolor_v4.0", "Athaliana_TAIR10",
            "Eudicot", n_workers=1, log=lambda m: None,
        )
        assert genome["id"] == "Sbicolor_v4.0"
        feature_ids = {f["id"] for f in genome["features"]}
        assert "TestGene1" in feature_ids
        feature = next(f for f in genome["features"] if f["id"] == "TestGene1")
        assert feature["functions"] == ["Alpha dehydrogenase (EC 1.1.1.1) # cytosol"]

        diag = genome["diagnostics"]
        assert diag["n_query_genes_searched"] == 1
        assert diag["n_query_genes_placed"] == 1
        assert diag["n_annotated_features"] == 1
        assert diag["phylum"] == "Eudicot"
        assert diag["psi_threshold"] == 0.60

    def test_unknown_ref_species_raises(self, tiny_bundle, query_fasta):
        with pytest.raises(ValueError, match="no curated features"):
            dispatch.annotate(
                query_fasta, tiny_bundle, "Sbicolor_v4.0", "NotASpecies",
                "Eudicot", log=lambda m: None,
            )

    def test_invalid_bundle_raises(self, tmp_path, query_fasta):
        not_a_bundle = tmp_path / "not_a_bundle"
        not_a_bundle.mkdir()
        with pytest.raises(ValueError, match="failed a fast verify"):
            dispatch.annotate(
                query_fasta, str(not_a_bundle), "Sbicolor_v4.0",
                "Athaliana_TAIR10", "Eudicot", log=lambda m: None,
            )

    def test_annotates_without_phylum(self, tiny_bundle, query_fasta):
        genome = dispatch.annotate(
            query_fasta, tiny_bundle, "Sbicolor_v4.0", "Athaliana_TAIR10",
            None, n_workers=1, log=lambda m: None,
        )
        assert {f["id"] for f in genome["features"]} == {"TestGene1"}
        assert genome["diagnostics"]["psi_threshold"] is None
        assert genome["diagnostics"]["phylum"] is None

    def test_high_threshold_leaves_gene_unannotated(self, tiny_bundle, query_fasta):
        """Same inputs, but a threshold above what a PAH-admitted paralog
        (no OF ortholog call exists, since DIAMOND makes none) can clear --
        confirms the threshold is actually being applied, not bypassed."""
        genome = dispatch.annotate(
            query_fasta, tiny_bundle, "Sbicolor_v4.0", "Athaliana_TAIR10",
            "Eudicot", threshold=0.999, n_workers=1, log=lambda m: None,
        )
        feature_ids = {f["id"] for f in genome["features"]}
        assert "TestGene1" not in feature_ids
        assert genome["diagnostics"]["n_annotated_features"] == 0
