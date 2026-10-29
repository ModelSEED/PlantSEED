"""place_query — DIAMOND-based placement into curated orthogroups.

Exercises the real `diamond` and `mafft` binaries against a tiny synthetic
bundle (one orthogroup, a handful of members) -- these tests are skipped if
either tool is not on PATH (or named by PLANTSEED_ANNOT_DIAMOND_BIN /
PLANTSEED_ANNOT_MAFFT_BIN), since a CI box or a dev checkout without them
installed should not fail the suite for an external-tool dependency this
module is explicit about needing.

See the module docstring in place_query.py for why this is DIAMOND-only
placement rather than a full OrthoFinder `-b` insert-mode run: the latter
needs each reference species' full original proteome and rebuilds the whole
similarity graph, neither of which the bundle format carries or an MCP tool
call's latency budget tolerates.
"""

import os
import shutil

import pytest

pq = pytest.importorskip("plantseed_annotation.algorithms.place_query")

DIAMOND_AVAILABLE = shutil.which(pq.DIAMOND_BIN) is not None
MAFFT_AVAILABLE = shutil.which(pq.MAFFT_BIN) is not None

pytestmark = pytest.mark.skipif(
    not (DIAMOND_AVAILABLE and MAFFT_AVAILABLE),
    reason=f"requires diamond ({pq.DIAMOND_BIN!r}) and mafft ({pq.MAFFT_BIN!r}) "
           "on PATH; set PLANTSEED_ANNOT_DIAMOND_BIN / PLANTSEED_ANNOT_MAFFT_BIN "
           "to point at them if installed elsewhere",
)

# A tiny, made-up protein family: three "reference" members (one per species)
# that are visibly similar to each other, and one "distractor" member from a
# different, unrelated family -- so a placement test can tell "found the
# right OG" from "found some OG".
_OG_MEMBERS = {
    "SpeciesA||geneA1": "MKVLSTATGKTVIVGLGAAGGIGQPLSLLLKNSPLVSRLTLYDIAG",
    "SpeciesB||geneB1": "MKVLSTATGKSVIVGLGAAGGIGQPLSLLLKASPLVSRLTLYDVAG",
    "SpeciesC||geneC1": "MKVLSTATGKTVIVGLGAAGGIGQALSLLLKNSPLVSRLTLYDIAG",
}

_DISTRACTOR_OG_MEMBERS = {
    "SpeciesA||geneA2": "MFAGWEDCPPQRSTTVKLMNHIYFGADCEQWRTYASDFGHJKLPOI",
    "SpeciesB||geneB2": "MFAGWEDCPPQRSTTVKLMNHIYFGADCEQWRTYASDFGHJKLPOQ",
}

# The query is a near-identical variant of the first OG, from a fourth
# species not in the bundle at all -- what an "annotate this new genome"
# caller actually hands in.
_QUERY_SEQUENCE = "MKVLSTATGKTVIVGLGAAGGIGQPLSLLLKNSPLVSRLTLYDIAN"


@pytest.fixture
def tiny_bundle(tmp_path):
    """A bundle with orthofinder_families/ only -- place_query never reads
    psi_matrices/ or curation/, so this is all a placement test needs."""
    bundle_dir = tmp_path / "bundle"
    families_dir = bundle_dir / "orthofinder_families"
    families_dir.mkdir(parents=True)

    def _write_fasta(path, members):
        with open(path, "w") as fh:
            for gene, seq in members.items():
                fh.write(f">{gene}\n{seq}\n")

    _write_fasta(families_dir / "OG0000001.fa", _OG_MEMBERS)
    _write_fasta(families_dir / "OG0000002.fa", _DISTRACTOR_OG_MEMBERS)
    return str(bundle_dir)


@pytest.fixture
def query_fasta(tmp_path):
    path = tmp_path / "query.faa"
    path.write_text(f">QuerySpecies||queryGene1\n{_QUERY_SEQUENCE}\n")
    return str(path)


class TestBuildReferenceDb:
    def test_builds_a_usable_dmnd_file(self, tiny_bundle, tmp_path):
        dmnd = pq.build_reference_db(
            tiny_bundle, db_path=str(tmp_path / "refdb"), log=lambda m: None)
        assert os.path.isfile(dmnd)
        assert dmnd.endswith(".dmnd")

    def test_missing_families_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            pq.build_reference_db(str(tmp_path / "nope"), log=lambda m: None)

    def test_reuses_an_existing_db_without_rebuilding(self, tiny_bundle, tmp_path):
        db_path = str(tmp_path / "refdb")
        first = pq.build_reference_db(tiny_bundle, db_path=db_path, log=lambda m: None)
        mtime_1 = os.path.getmtime(first)
        second = pq.build_reference_db(tiny_bundle, db_path=db_path, log=lambda m: None)
        assert second == first
        assert os.path.getmtime(second) == mtime_1   # not rebuilt

    def test_force_rebuilds(self, tiny_bundle, tmp_path):
        db_path = str(tmp_path / "refdb")
        first = pq.build_reference_db(tiny_bundle, db_path=db_path, log=lambda m: None)
        mtime_1 = os.path.getmtime(first)
        import time
        time.sleep(1.1)   # mtime resolution
        second = pq.build_reference_db(
            tiny_bundle, db_path=db_path, force=True, log=lambda m: None)
        assert os.path.getmtime(second) != mtime_1

    def test_concurrent_cold_builds_do_not_corrupt_each_other(
            self, tiny_bundle, query_fasta, tmp_path):
        """Regression test for a real bug: three simultaneous `annotate`
        calls against a never-before-built bundle each ran `diamond makedb`
        into the same db_path at once, and one call's partial write
        corrupted another's read of it mid-build -- surfaced as a DIAMOND
        segfault (exit -11) or "Unexpected end of input" in production
        testing. build_reference_db now serializes concurrent builders with
        an flock; this drives N threads at an empty cache simultaneously and
        requires every one of them to come back with the same, valid,
        usable .dmnd path."""
        import concurrent.futures

        db_path = str(tmp_path / "refdb")
        n_workers = 5

        def _build():
            return pq.build_reference_db(tiny_bundle, db_path=db_path, log=lambda m: None)

        with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as pool:
            results = list(pool.map(lambda _: _build(), range(n_workers)))

        assert len(set(results)) == 1          # every caller agrees on the path
        dmnd_path = results[0]
        assert os.path.isfile(dmnd_path)
        assert os.path.getsize(dmnd_path) > 0
        # No leftover build artifacts from any racing attempt.
        leftovers = [f for f in os.listdir(tmp_path)
                    if f.startswith("refdb.building.")]
        assert leftovers == []
        # And the db is actually usable -- not just present.
        hits = pq.search(query_fasta, dmnd_path, log=lambda m: None)
        assert hits


class TestSearchAndBestHit:
    def test_search_finds_the_similar_og_not_the_distractor(
            self, tiny_bundle, query_fasta, tmp_path):
        dmnd = pq.build_reference_db(tiny_bundle, db_path=str(tmp_path / "refdb"),
                                     log=lambda m: None)
        hits = pq.search(query_fasta, dmnd, log=lambda m: None)
        assert "QuerySpecies||queryGene1" in hits
        best_header = hits["QuerySpecies||queryGene1"][0][0]
        og_id, ref_gene = pq._parse_reference_header(best_header)
        assert og_id == "OG0000001"
        assert ref_gene in _OG_MEMBERS

    def test_best_hit_per_query_gene(self, tiny_bundle, query_fasta, tmp_path):
        dmnd = pq.build_reference_db(tiny_bundle, db_path=str(tmp_path / "refdb"),
                                     log=lambda m: None)
        hits = pq.search(query_fasta, dmnd, log=lambda m: None)
        placement = pq.best_hit_per_query_gene(hits)
        assert placement["QuerySpecies||queryGene1"][0] == "OG0000001"

    def test_a_query_with_no_hit_is_absent_from_placement(self, tiny_bundle, tmp_path):
        no_hit_fasta = tmp_path / "no_hit.faa"
        no_hit_fasta.write_text(
            ">QuerySpecies||unrelatedGene\n"
            "QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ\n")
        dmnd = pq.build_reference_db(tiny_bundle, db_path=str(tmp_path / "refdb"),
                                     log=lambda m: None)
        hits = pq.search(str(no_hit_fasta), dmnd, log=lambda m: None)
        placement = pq.best_hit_per_query_gene(hits)
        assert "QuerySpecies||unrelatedGene" not in placement


class TestRealignAndScore:
    def test_realigns_and_scores_against_og_members_only(self, tiny_bundle):
        query_sequences_by_og = {
            "OG0000001": {"QuerySpecies||queryGene1": _QUERY_SEQUENCE},
        }
        psi_rows_by_og, ogs_query_members = pq.realign_and_score(
            query_sequences_by_og, tiny_bundle, log=lambda m: None)

        assert "OG0000001" in psi_rows_by_og
        assert ogs_query_members["OG0000001"] == ["QuerySpecies||queryGene1"]

        scored_members = {m for (_q, m, *_rest) in psi_rows_by_og["OG0000001"]}
        assert scored_members == set(_OG_MEMBERS)

        # The query is a near-identical variant of the OG -- every PSI
        # should be high, not a borderline or zero score.
        for _q, _m, _id_q, _id_m, psi_val in psi_rows_by_og["OG0000001"]:
            assert psi_val > 0.85

    def test_missing_alignment_in_bundle_is_skipped_not_fatal(self, tiny_bundle):
        query_sequences_by_og = {
            "OG_NOT_IN_BUNDLE": {"QuerySpecies||g1": _QUERY_SEQUENCE},
        }
        psi_rows_by_og, ogs_query_members = pq.realign_and_score(
            query_sequences_by_og, tiny_bundle, log=lambda m: None)
        assert psi_rows_by_og == {}
        assert ogs_query_members == {}


class TestPlaceEndToEnd:
    def test_place_returns_annotate_species_compatible_shapes(
            self, tiny_bundle, query_fasta):
        result = pq.place(query_fasta, tiny_bundle, "QuerySpecies",
                          log=lambda m: None)

        assert result["n_query_genes_searched"] == 1
        assert result["n_query_genes_placed"] == 1
        assert result["n_query_genes_scored"] == 1

        assert "OG0000001" in result["ogs"]
        assert "QuerySpecies||queryGene1" in result["ogs"]["OG0000001"]["QuerySpecies"]
        for spp in ("SpeciesA", "SpeciesB", "SpeciesC"):
            assert spp in result["ogs"]["OG0000001"]

        assert ("QuerySpecies", "QuerySpecies||queryGene1") in result["sp_gene_to_og"]
        assert result["sp_gene_to_og"][("QuerySpecies", "QuerySpecies||queryGene1")] == "OG0000001"

        # DIAMOND makes no reciprocal ortholog call -- see the module
        # docstring. psi_refined's O/PAM/PAH logic is expected to fall back
        # to the PAH/fallback-baseline path for every pair, which is already
        # tested behaviour, not something this module re-implements.
        assert result["orthologues_dict"] == {}

        pair_map = result["psi_by_og"]["OG0000001"]
        assert len(pair_map) == 3   # query vs each of the 3 members

    def test_place_feeds_annotate_species_without_modification(
            self, tiny_bundle, query_fasta):
        """The whole point of place()'s output shape: it should need no
        translation before annotate_species can consume it directly."""
        from plantseed_annotation.algorithms import psi_refined as pr

        result = pq.place(query_fasta, tiny_bundle, "QuerySpecies",
                          log=lambda m: None)

        curated = {
            "geneA1": {"function": "Alpha dehydrogenase # cytosol"},
            "geneB1": {"function": "Alpha dehydrogenase # cytosol"},
            "geneC1": {"function": "Alpha dehydrogenase # cytosol"},
        }
        annotations, stats, pair_stats = pr.annotate_species(
            "QuerySpecies", "SpeciesA",
            result["orthologues_dict"], result["ogs"], result["psi_by_og"],
            result["sp_gene_to_og"], curated, threshold=0.0,
        )
        assert "queryGene1" in annotations
        assert annotations["queryGene1"]["status"] == "ANNOTATED"
        assert annotations["queryGene1"]["function"] == "Alpha dehydrogenase # cytosol"
        # No OF-called ortholog exists (orthologues_dict is empty), so the
        # accepted pair must be a paralog admission (PAH, since there's no
        # per-OG baseline either without an OF call) -- never 'O'.
        assert pair_stats.get("O", 0) == 0
        assert pair_stats.get("PAH", 0) >= 1
