"""orthofinder_io — Orthogroups.tsv / Orthologues.tsv / MSA parsers."""

import os

import pytest

from plantseed_annotation.algorithms import orthofinder_io as oio


@pytest.fixture
def tiny_of_results(tmp_path):
    """A minimal Orthofinder-Results-shaped directory tree."""
    root = tmp_path / "Results_TEST"
    (root / "Orthogroups").mkdir(parents=True)
    (root / "MultipleSequenceAlignments").mkdir()
    (root / "Orthologues" / "Orthologues_Sbicolor_v3.1.1").mkdir(parents=True)

    (root / "Orthogroups" / "Orthogroups.tsv").write_text(
        "Orthogroup\tAthaliana_TAIR10\tSbicolor_v3.1.1\n"
        "OG0000001\tAT1G01050, AT1G01060\tSobic.001G000100\n"
        "OG0000002\tAT2G00010\t\n"                               # ref-only
        "OG0000003\t\tSobic.002G000100, Sobic.002G000200\n"      # query-only
    )
    (root / "Orthologues" / "Orthologues_Sbicolor_v3.1.1"
        / "Sbicolor_v3.1.1__v__Athaliana_TAIR10.tsv").write_text(
        "Orthogroup\tSbicolor_v3.1.1\tAthaliana_TAIR10\n"
        "OG0000001\tSobic.001G000100\tAT1G01050, AT1G01060\n"
    )
    (root / "MultipleSequenceAlignments" / "OG0000001.fa").write_text(
        ">AT1G01050\nMKKAA----KLPLL\n"
        ">AT1G01060\nMKKAA----KLPLL\n"
        ">Sobic.001G000100\nMKKATTKKKLPLL-\n"
    )
    return str(root)


def test_load_orthogroups_shape(tiny_of_results):
    ogs, species = oio.load_orthogroups(
        os.path.join(tiny_of_results, "Orthogroups", "Orthogroups.tsv")
    )
    assert species == ["Athaliana_TAIR10", "Sbicolor_v3.1.1"]
    assert set(ogs) == {"OG0000001", "OG0000002", "OG0000003"}
    assert ogs["OG0000001"]["Athaliana_TAIR10"] == ["AT1G01050", "AT1G01060"]
    assert ogs["OG0000001"]["Sbicolor_v3.1.1"] == ["Sobic.001G000100"]
    assert ogs["OG0000002"]["Sbicolor_v3.1.1"] == []
    assert ogs["OG0000003"]["Athaliana_TAIR10"] == []


def test_species_gene_to_og_reverse_index(tiny_of_results):
    ogs, _ = oio.load_orthogroups(
        os.path.join(tiny_of_results, "Orthogroups", "Orthogroups.tsv")
    )
    idx = oio.species_gene_to_og_index(ogs)
    assert idx[("Athaliana_TAIR10", "AT1G01050")] == "OG0000001"
    assert idx[("Sbicolor_v3.1.1", "Sobic.002G000100")] == "OG0000003"
    assert ("Athaliana_TAIR10", "AT9G99999") not in idx


def test_orthologues_path_present_and_absent(tiny_of_results):
    path = oio.orthologues_path(
        tiny_of_results, "Sbicolor_v3.1.1", "Athaliana_TAIR10",
    )
    assert path is not None and path.endswith(
        "Sbicolor_v3.1.1__v__Athaliana_TAIR10.tsv")
    absent = oio.orthologues_path(
        tiny_of_results, "Athaliana_TAIR10", "Sbicolor_v3.1.1",
    )
    assert absent is None


def test_load_orthologues_symmetric(tiny_of_results):
    path = oio.orthologues_path(
        tiny_of_results, "Sbicolor_v3.1.1", "Athaliana_TAIR10",
    )
    q_to_r, r_to_q = oio.load_orthologues(path)
    assert q_to_r["Sobic.001G000100"]["og"] == "OG0000001"
    assert set(q_to_r["Sobic.001G000100"]["orthologs"]) == {"AT1G01050", "AT1G01060"}
    assert set(r_to_q["AT1G01050"]["orthologs"]) == {"Sobic.001G000100"}


def test_list_and_read_msa(tiny_of_results):
    msas = list(oio.list_alignments(tiny_of_results))
    assert msas == [("OG0000001",
                     os.path.join(tiny_of_results, "MultipleSequenceAlignments",
                                  "OG0000001.fa"))]
    seqs = oio.read_msa(msas[0][1])
    assert set(seqs) == {"AT1G01050", "AT1G01060", "Sobic.001G000100"}
    assert seqs["AT1G01050"] == "MKKAA----KLPLL"


# --- Species||prefix stripping + transcript_to_gene --------------------------
def test_load_orthogroups_strips_species_prefix(tmp_path):
    """Real OF results in Sam's repo carry a redundant '<species>||' prefix
    on every cell entry (built from fasta headers like `Species_id||gene.N`).
    The parser must strip it so callers can compare to curated gene ids."""
    tsv = tmp_path / "Orthogroups.tsv"
    tsv.write_text(
        "Orthogroup\tAthaliana_TAIR10\tSbicolor_v3.1.1\n"
        "OG0000001\tAthaliana_TAIR10||AT1G01050.1, Athaliana_TAIR10||AT1G01050.2\t"
        "Sbicolor_v3.1.1||Sobic.001G000100.1\n"
    )
    ogs, _ = oio.load_orthogroups(str(tsv))
    entry = ogs["OG0000001"]
    assert entry["Athaliana_TAIR10"] == [
        "Athaliana_TAIR10||AT1G01050.1", "Athaliana_TAIR10||AT1G01050.2"]
    assert entry["Sbicolor_v3.1.1"] == ["Sbicolor_v3.1.1||Sobic.001G000100.1"]


def test_load_orthologues_keeps_species_prefix(tmp_path):
    """Ids must stay prefixed so they match the PSI matrix keys."""
    tsv = tmp_path / "Sbicolor_v3.1.1__v__Athaliana_TAIR10.tsv"
    tsv.write_text(
        "Orthogroup\tSbicolor_v3.1.1\tAthaliana_TAIR10\n"
        "OG0000001\tSbicolor_v3.1.1||Sobic.001G000100.1\t"
        "Athaliana_TAIR10||AT1G01050.1, Athaliana_TAIR10||AT1G01050.2\n"
    )
    q_to_r, r_to_q = oio.load_orthologues(str(tsv))
    assert set(q_to_r) == {"Sbicolor_v3.1.1||Sobic.001G000100.1"}
    assert set(q_to_r["Sbicolor_v3.1.1||Sobic.001G000100.1"]["orthologs"]) == {
        "Athaliana_TAIR10||AT1G01050.1", "Athaliana_TAIR10||AT1G01050.2"}
    assert set(r_to_q) == {"Athaliana_TAIR10||AT1G01050.1",
                           "Athaliana_TAIR10||AT1G01050.2"}


def test_read_msa_keeps_the_species_prefix(tmp_path):
    """Unprefixed ids still pass through, for the 2021 reference and fixtures."""
    fasta = tmp_path / "OG.fa"
    fasta.write_text(
        ">Athaliana_TAIR10||AT1G01050.1\nMKK\n"
        ">Sbicolor_v3.1.1||Sobic.001G000100.1\nMKK\n"
        ">bare_gene\nMKK\n"
    )
    seqs = oio.read_msa(str(fasta))
    assert set(seqs) == {"Athaliana_TAIR10||AT1G01050.1",
                         "Sbicolor_v3.1.1||Sobic.001G000100.1", "bare_gene"}


def test_two_assemblies_of_one_organism_do_not_collide(tmp_path):
    """The defect this convention exists to prevent.

    Genome-scale gene ids are unique only WITHIN a proteome, so two assemblies
    of one organism share them by construction. Stripping the species made
    `Sbicolor_v3.1.1||Sobic.001G012200.1.p` and
    `Sbicolor_v5.1||Sobic.001G012200.1.p` the same key -- one silently
    overwrote the other, in 680 of 758 curated orthogroups of the 23-species
    reference, so every PSI value involving that gene was a coin flip between
    two different proteins.
    """
    fasta = tmp_path / "OG.fa"
    fasta.write_text(
        ">Sbicolor_v3.1.1||Sobic.001G012200.1.p\nMKKAA\n"
        ">Sbicolor_v5.1||Sobic.001G012200.1.p\nMKKWW\n"
    )
    seqs = oio.read_msa(str(fasta))
    assert len(seqs) == 2, "one assembly overwrote the other"
    assert seqs["Sbicolor_v3.1.1||Sobic.001G012200.1.p"] == "MKKAA"
    assert seqs["Sbicolor_v5.1||Sobic.001G012200.1.p"] == "MKKWW"


@pytest.mark.parametrize("gid, species, gene", [
    ("Athaliana_TAIR10||AT1G01050.1", "Athaliana_TAIR10", "AT1G01050.1"),
    ("Smoellendorffii_v1.0||98083",   "Smoellendorffii_v1.0", "98083"),
    ("bare_gene",                     "", "bare_gene"),
])
def test_split_id(gid, species, gene):
    assert oio.split_id(gid) == (species, gene)
    assert oio.species_of(gid) == species
    assert oio.gene_of(gid) == gene


@pytest.mark.parametrize("tid, gene", [
    # A prefixed id must still reduce to the bare gene: the curation is keyed
    # by species separately, so the prefix comes off at this one boundary.
    ("Athaliana_TAIR10||AT1G01050.1", "AT1G01050"),
    ("Sbicolor_v3.1.1||Sobic.001G234700.1.p", "Sobic.001G234700"),
    ("AT1G01050.1",        "AT1G01050"),
    ("AT1G01050.2",        "AT1G01050"),
    ("Sobic.001G234700.1", "Sobic.001G234700"),
    ("Potri.001G067600.1", "Potri.001G067600"),
    ("AT1G01050",          "AT1G01050"),           # already gene-level
    ("Sobic.001G234700",   "Sobic.001G234700"),    # last segment isn't digits
    ("simple",             "simple"),              # no dots at all
])
def test_transcript_to_gene(tid, gene):
    assert oio.transcript_to_gene(tid) == gene
