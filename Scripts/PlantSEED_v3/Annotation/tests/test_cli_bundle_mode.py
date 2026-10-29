"""plantseed-annotate's --bundle-dir/--query-fasta mode (cli._main_bundle_mode).

Mode-selection validation (mutual exclusion, required pairing) needs no
external tools and is tested unconditionally. The happy-path annotation run
reuses test_dispatch.py's tiny_bundle fixture and is skipped without
diamond/mafft, same as that module.
"""

import json
import os
import shutil

import pytest

from plantseed_annotation import cli

pq = pytest.importorskip("plantseed_annotation.algorithms.place_query")

DIAMOND_AVAILABLE = shutil.which(pq.DIAMOND_BIN) is not None
MAFFT_AVAILABLE = shutil.which(pq.MAFFT_BIN) is not None

from plantseed_annotation.refbuild import bundle as _bundle

_REF_SEQUENCE = "MKVLSTATGKTVIVGLGAAGGIGQPLSLLLKNSPLVSRLTLYDIAG"
_QUERY_SEQUENCE = "MKVLSTATGKTVIVGLGAAGGIGQPLSLLLKNSPLVSRLTLYDIAN"


@pytest.fixture
def tiny_bundle(tmp_path):
    bundle_dir = tmp_path / "bundle"
    _bundle.ensure_layout(str(bundle_dir))

    families_dir = bundle_dir / _bundle.FAMILIES_DIR
    with open(families_dir / "OG0000001.fa", "w") as fh:
        fh.write(f">Athaliana_TAIR10||AT1G00001.1\n{_REF_SEQUENCE}\n")
        fh.write(f">Sbicolor_v3.1.1||Sobic.001G000100.1\n{_REF_SEQUENCE}\n")

    curation_dir = bundle_dir / _bundle.CURATION_DIR
    _bundle.write_json(str(curation_dir / "curated_features.json"), {
        "Athaliana_TAIR10": {
            "AT1G00001": {
                "function": "Alpha dehydrogenase (EC 1.1.1.1) # cytosol",
                "roles": ["Alpha dehydrogenase (EC 1.1.1.1)"],
                "compartments": ["c"],
            },
        },
    })
    _bundle.write_json(str(curation_dir / "phylum_thresholds.json"),
                       {"Eudicot": 0.60, "Monocot": 0.55, "Basal": 0.30})

    manifest = {"schema_version": 1, "bundle_version": "vTEST",
                "created_utc": "2026-01-01T00:00:00Z", "sources": {},
                "tool_versions": {}, "curated_non_arabidopsis": [],
                "contents": {}, "totals": {}}
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


class TestModeSelection:
    def test_neither_mode_given_exits(self, tmp_path, capsys):
        out_path = str(tmp_path / "out.json")
        with pytest.raises(SystemExit, match="pass either --orthofinder-results"):
            cli.main(["--query-species", "X", "--out", out_path])

    def test_both_modes_given_exits(self, tmp_path):
        out_path = str(tmp_path / "out.json")
        with pytest.raises(SystemExit, match="mutually exclusive"):
            cli.main([
                "--orthofinder-results", str(tmp_path),
                "--bundle-dir", str(tmp_path), "--query-fasta", str(tmp_path / "q.faa"),
                "--query-species", "X", "--out", out_path,
            ])

    def test_bundle_without_fasta_exits(self, tmp_path):
        out_path = str(tmp_path / "out.json")
        with pytest.raises(SystemExit, match="must be given together"):
            cli.main([
                "--bundle-dir", str(tmp_path), "--query-species", "X",
                "--out", out_path,
            ])

    def test_fasta_without_bundle_exits(self, tmp_path):
        out_path = str(tmp_path / "out.json")
        with pytest.raises(SystemExit, match="must be given together"):
            cli.main([
                "--query-fasta", str(tmp_path / "q.faa"), "--query-species", "X",
                "--out", out_path,
            ])

    def test_gradient_report_rejected_in_bundle_mode(self, tiny_bundle, query_fasta, tmp_path):
        out_path = str(tmp_path / "out.json")
        with pytest.raises(SystemExit, match="not available in --bundle-dir mode"):
            cli.main([
                "--bundle-dir", tiny_bundle, "--query-fasta", query_fasta,
                "--query-species", "Sbicolor_v4.0", "--phylum", "Eudicot",
                "--conservation-gradient-report", str(tmp_path / "gradient.json"),
                "--out", out_path,
            ])


@pytest.mark.skipif(
    not (DIAMOND_AVAILABLE and MAFFT_AVAILABLE),
    reason="requires diamond and mafft on PATH",
)
class TestBundleModeEndToEnd:
    def test_annotates_and_writes_metadata(self, tiny_bundle, query_fasta, tmp_path):
        out_path = str(tmp_path / "out.json")
        rc = cli.main([
            "--bundle-dir", tiny_bundle, "--query-fasta", query_fasta,
            "--query-species", "Sbicolor_v4.0", "--ref-species", "Athaliana_TAIR10",
            "--phylum", "Eudicot", "--workers", "1",
            "--out", out_path, "--quiet",
        ])
        assert rc == 0
        with open(out_path) as fh:
            genome = json.load(fh)

        feature_ids = {f["id"] for f in genome["features"]}
        assert "TestGene1" in feature_ids

        meta = genome["metadata"]
        assert meta["mode"] == "bundle"
        assert meta["query_species"] == "Sbicolor_v4.0"
        assert meta["n_annotated_features"] == 1
        assert meta["phylum"] == "Eudicot"
        assert "diagnostics" not in genome   # folded into metadata, not left as a sibling key

    def test_missing_query_fasta_exits(self, tiny_bundle, tmp_path):
        out_path = str(tmp_path / "out.json")
        with pytest.raises(SystemExit, match="query FASTA not found"):
            cli.main([
                "--bundle-dir", tiny_bundle,
                "--query-fasta", str(tmp_path / "does_not_exist.faa"),
                "--query-species", "Sbicolor_v4.0", "--phylum", "Eudicot",
                "--out", out_path,
            ])

    def test_invalid_bundle_exits(self, query_fasta, tmp_path):
        not_a_bundle = tmp_path / "not_a_bundle"
        not_a_bundle.mkdir()
        out_path = str(tmp_path / "out.json")
        with pytest.raises(SystemExit, match="ERROR:"):
            cli.main([
                "--bundle-dir", str(not_a_bundle), "--query-fasta", query_fasta,
                "--query-species", "Sbicolor_v4.0", "--phylum", "Eudicot",
                "--out", out_path,
            ])
