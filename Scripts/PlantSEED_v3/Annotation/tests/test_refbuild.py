"""Building a refdata bundle, and the property the build is judged on.

Byte-reproducibility is the point of most of these. A bundle is rsynced to
KBase refdata, mounted read-only in two containers, and diffed against its
successor to show what enrichment added — none of which means anything if two
builds of the same inputs differ. And it is exactly the kind of property that
holds today and quietly stops holding when someone iterates a dict, formats a
float, or sorts under a different locale.

The fixture is a synthetic OrthoFinder run, so these are fast and hermetic.
The real 31,196-orthogroup run is exercised by hand; what is pinned here is
the behaviour, not the scale.
"""

import json
import os
import shutil

import pytest

from plantseed_annotation import paths, reference
from plantseed_annotation.refbuild import bundle, cli, prune, stamp_version


@pytest.fixture
def of_run(tmp_path):
    """A minimal OrthoFinder results directory with three orthogroups.

    Two contain a curated Arabidopsis gene, one does not — so pruning has
    something to drop and the test can tell selection from "kept everything".
    """
    root = tmp_path / "Results_Test"
    (root / "Orthogroups").mkdir(parents=True)
    (root / "MultipleSequenceAlignments").mkdir()

    curated = _a_curated_arabidopsis_gene()
    rows = [
        ("OG0000001", f"{curated}.1", "Sobic.001G000100.1"),
        ("OG0000002", "AT9G999990.1", "Sobic.009G999900.1"),   # uncurated
        ("OG0000003", f"{_another_curated()}.1", ""),
    ]
    with open(root / "Orthogroups" / "Orthogroups.tsv", "w") as fh:
        fh.write("Orthogroup\tAthaliana_TAIR10\tSbicolor_v3.1.1\n")
        for og, at, sb in rows:
            fh.write(f"{og}\t{at}\t{sb}\n")
    for og, at, sb in rows:
        members = [g for g in (at, sb) if g]
        (root / "MultipleSequenceAlignments" / f"{og}.fa").write_text(
            "".join(f">{g}\nMKKAAG{'W' if i else 'A'}\n"
                    for i, g in enumerate(members)))
    return str(root)


def _curated_by_species():
    from plantseed_annotation.algorithms import propagate

    return propagate.curated_features_by_source_species(
        propagate.build_curated_features())


def _a_curated_arabidopsis_gene():
    return sorted(_curated_by_species()["Athaliana_TAIR10"])[0]


def _another_curated():
    return sorted(_curated_by_species()["Athaliana_TAIR10"])[1]


def _build(of_run, dest, **kw):
    kw.setdefault("n_workers", 1)
    kw.setdefault("log", lambda m: None)
    return cli.build(of_run, str(dest), kw.pop("version", "v0"), **kw)


class TestPruning:
    def test_only_orthogroups_with_a_curated_gene_are_kept(self, of_run):
        from plantseed_annotation.algorithms import orthofinder_io

        ogs, _ = orthofinder_io.load_orthogroups(
            os.path.join(of_run, "Orthogroups", "Orthogroups.tsv"))
        assert prune.curated_orthogroups(ogs) == ["OG0000001", "OG0000003"]

    def test_the_result_is_sorted(self, of_run):
        """Selection feeds directory contents, so its order reaches the bytes."""
        from plantseed_annotation.algorithms import orthofinder_io

        ogs, _ = orthofinder_io.load_orthogroups(
            os.path.join(of_run, "Orthogroups", "Orthogroups.tsv"))
        selected = prune.curated_orthogroups(ogs)
        assert selected == sorted(selected)

    def test_transcripts_are_normalised_to_genes(self, of_run):
        """Orthogroups.tsv holds transcript ids ('AT1G01010.1'); the curation
        is gene-level. Matching raw finds nothing, silently."""
        from plantseed_annotation.algorithms import orthofinder_io

        ogs, _ = orthofinder_io.load_orthogroups(
            os.path.join(of_run, "Orthogroups", "Orthogroups.tsv"))
        assert prune.curated_orthogroups(ogs), (
            "no orthogroup matched — transcript-to-gene normalisation is off")

    def test_the_report_counts_both_sides(self, of_run):
        from plantseed_annotation.algorithms import orthofinder_io

        ogs, _ = orthofinder_io.load_orthogroups(
            os.path.join(of_run, "Orthogroups", "Orthogroups.tsv"))
        r = prune.prune_report(ogs, prune.curated_orthogroups(ogs))
        assert r["og_total"] == 3 and r["og_kept"] == 2 and r["og_dropped"] == 1


class TestBuild:
    def test_it_produces_the_expected_layout(self, of_run, tmp_path):
        dest = tmp_path / "bundle"
        _build(of_run, dest)
        for sub in bundle.PAYLOAD_DIRS:
            assert (dest / sub).is_dir(), sub
        assert (dest / bundle.MANIFEST).is_file()

    def test_only_selected_orthogroups_are_materialised(self, of_run, tmp_path):
        dest = tmp_path / "bundle"
        _build(of_run, dest)
        fams = sorted(p[:-3] for p in os.listdir(dest / bundle.FAMILIES_DIR))
        psi = sorted(p[:-4] for p in os.listdir(dest / bundle.PSI_DIR))
        assert fams == ["OG0000001", "OG0000003"] == psi

    def test_families_are_copied_byte_for_byte(self, of_run, tmp_path):
        """Not re-serialised: the bundle's copy must hash to the source's."""
        dest = tmp_path / "bundle"
        _build(of_run, dest)
        src = os.path.join(of_run, "MultipleSequenceAlignments", "OG0000001.fa")
        got = dest / bundle.FAMILIES_DIR / "OG0000001.fa"
        assert bundle.sha256_file(src) == bundle.sha256_file(str(got))

    def test_the_curation_payload_is_written(self, of_run, tmp_path):
        from plantseed_annotation.refbuild import build_curation

        dest = tmp_path / "bundle"
        _build(of_run, dest)
        features = json.loads(
            (dest / bundle.CURATION_DIR / build_curation.CURATED_FEATURES).read_text())
        assert "Athaliana_TAIR10" in features
        thresholds = json.loads(
            (dest / bundle.CURATION_DIR / build_curation.PHYLUM_THRESHOLDS).read_text())
        assert thresholds == dict(paths.PHYLUM_THRESHOLDS_DEFAULT)


class TestByteReproducibility:
    """The property the whole build is judged on."""

    def test_two_builds_are_byte_identical(self, of_run, tmp_path, monkeypatch):
        monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
        a, b = tmp_path / "a", tmp_path / "b"
        _build(of_run, a)
        _build(of_run, b)
        for rel, absolute in bundle.iter_payload(str(a)):
            assert bundle.sha256_file(absolute) == \
                bundle.sha256_file(str(b / rel)), rel
        assert (a / bundle.MANIFEST).read_bytes() == (b / bundle.MANIFEST).read_bytes()

    def test_the_worker_count_does_not_change_the_output(self, of_run, tmp_path,
                                                         monkeypatch):
        """PSI is computed in a process pool with imap_unordered; if any output
        depended on completion order this would catch it."""
        monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
        a, b = tmp_path / "a", tmp_path / "b"
        _build(of_run, a, n_workers=1)
        _build(of_run, b, n_workers=4)
        assert (bundle.content_id(_contents(a)) == bundle.content_id(_contents(b)))

    def test_source_date_epoch_pins_the_timestamp(self, monkeypatch):
        monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
        assert bundle.created_utc() == "2023-11-14T22:13:20Z"

    def test_an_unset_epoch_still_produces_a_valid_stamp(self, monkeypatch):
        monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
        assert bundle.created_utc().endswith("Z")

    def test_json_is_written_with_stable_formatting(self, tmp_path):
        """json.dump's defaults leave a trailing space after every comma and
        preserve insertion order; either would make equal values differ."""
        p1, p2 = tmp_path / "1.json", tmp_path / "2.json"
        bundle.write_json(str(p1), {"b": 1, "a": [2, 3]})
        bundle.write_json(str(p2), {"a": [2, 3], "b": 1})
        assert p1.read_bytes() == p2.read_bytes()
        assert p1.read_bytes().endswith(b"\n")

    def test_content_id_changes_when_any_byte_changes(self, of_run, tmp_path):
        dest = tmp_path / "bundle"
        result = _build(of_run, dest)
        before = result["manifest"]["content_id"]
        target = next(iter(sorted(os.listdir(dest / bundle.PSI_DIR))))
        (dest / bundle.PSI_DIR / target).write_text("tampered\n")
        after = stamp_version.build_manifest(str(dest), "v0")["content_id"]
        assert before != after

    def test_content_id_survives_moving_the_bundle(self, of_run, tmp_path):
        """It hashes contents, not paths — a bundle rsynced elsewhere is the
        same bundle."""
        a = tmp_path / "here"
        _build(of_run, a)
        moved = tmp_path / "there"
        shutil.copytree(a, moved)
        assert (stamp_version.build_manifest(str(a), "v0")["content_id"] ==
                stamp_version.build_manifest(str(moved), "v0")["content_id"])


def _contents(root):
    return {rel: {"sha256": bundle.sha256_file(p)[0]}
            for rel, p in bundle.iter_payload(str(root))}


class TestVerify:
    def test_a_fresh_bundle_verifies(self, of_run, tmp_path):
        dest = tmp_path / "bundle"
        _build(of_run, dest)
        ok, issues = reference.verify(str(dest))
        assert ok, issues

    def test_a_modified_file_is_caught(self, of_run, tmp_path):
        """The realistic failure is a partial rsync, which raises nothing on
        its own — the annotator just finds fewer orthologs and looks like
        biology rather than a broken mount."""
        dest = tmp_path / "bundle"
        _build(of_run, dest)
        target = sorted(os.listdir(dest / bundle.PSI_DIR))[0]
        with open(dest / bundle.PSI_DIR / target, "a") as fh:
            fh.write("x")
        ok, issues = reference.verify(str(dest))
        assert not ok and any("content differs" in i for i in issues)

    def test_a_deleted_file_is_caught(self, of_run, tmp_path):
        dest = tmp_path / "bundle"
        _build(of_run, dest)
        os.unlink(dest / bundle.PSI_DIR / sorted(os.listdir(dest / bundle.PSI_DIR))[0])
        ok, issues = reference.verify(str(dest))
        assert not ok and any(i.startswith("missing:") for i in issues)

    def test_an_extra_file_is_caught(self, of_run, tmp_path):
        """An unexpected file means the bundle is not the one that was stamped."""
        dest = tmp_path / "bundle"
        _build(of_run, dest)
        (dest / bundle.PSI_DIR / "OG9999999.txt").write_text("stray\n")
        ok, issues = reference.verify(str(dest))
        assert not ok and any("not in manifest" in i for i in issues)

    def test_fast_mode_skips_hashing_but_still_sees_structure(self, of_run,
                                                              tmp_path):
        dest = tmp_path / "bundle"
        _build(of_run, dest)
        target = sorted(os.listdir(dest / bundle.PSI_DIR))[0]
        with open(dest / bundle.PSI_DIR / target, "a") as fh:
            fh.write("x")
        assert reference.verify(str(dest), check_hashes=False)[0]
        assert not reference.verify(str(dest), check_hashes=True)[0]

    def test_a_missing_bundle_is_an_issue_not_an_exception(self, tmp_path):
        ok, issues = reference.verify(str(tmp_path / "nope"))
        assert not ok and "does not exist" in issues[0]

    def test_the_tier_cap_is_enforced(self, of_run, tmp_path):
        """10 GB on the KBase tier is the binding constraint on the design."""
        dest = tmp_path / "bundle"
        _build(of_run, dest)
        manifest = bundle.read_json(str(dest / bundle.MANIFEST))
        manifest["totals"]["bytes_total"] = 99 * 10**9
        bundle.write_json(str(dest / bundle.MANIFEST), manifest)
        ok, issues = reference.verify(str(dest), tier="kbase", check_hashes=False)
        assert not ok and any("refdata cap" in i for i in issues)


class TestManifest:
    def test_it_matches_the_shipped_schema(self, of_run, tmp_path):
        js = pytest.importorskip("jsonschema")
        from plantseed_annotation import refbuild

        dest = tmp_path / "bundle"
        manifest = _build(of_run, dest)["manifest"]
        schema = bundle.read_json(
            os.path.join(os.path.dirname(refbuild.__file__),
                         "manifest_schema.json"))
        js.validate(manifest, schema)

    def test_shoot_fields_are_present_and_empty(self, of_run, tmp_path):
        """A v0 bundle carries no SHOOT-placed proteins. Present-and-empty so a
        consumer can tell that from a manifest that predates the field."""
        manifest = _build(of_run, tmp_path / "bundle")["manifest"]
        assert manifest["curated_non_arabidopsis"] == []
        assert manifest["sources"]["shoot_db_build_id"] == ""
