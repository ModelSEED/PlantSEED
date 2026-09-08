"""Preparing proteomes so identifiers survive the pipeline.

The 2021 reference run pre-prefixed its inputs and passed `-X`; the 2025 run
did not, and OrthoFinder joined species to gene itself with `_` after
rewriting every `.` --

    >CreinhardtiiCC_4532_707_v6_1_protein_Cre16.g651400_4532.1.p

-- which has no parse. These pin the convention that avoids it.
"""

import os

import pytest

from plantseed_annotation.refbuild import prepare_proteomes as prep

SEP = prep.SEPARATOR


def _write(tmp_path, name, records):
    p = tmp_path / name
    p.write_text("".join(f">{h}\n{s}\n" for h, s in records))
    return str(p)


def _headers(path):
    return [l[1:].rstrip("\n") for l in open(path) if l.startswith(">")]


class TestHeaderRewriting:
    def test_species_comes_from_the_filename(self, tmp_path):
        src = _write(tmp_path, "Sbicolor_454_v3.1.1.protein.fa",
                     [("Sobic.001G000100.1.p pacid=1", "MKKA")])
        prep.prepare_one(src, str(tmp_path / "out.fa"), log=lambda m: None)
        assert _headers(tmp_path / "out.fa") == [
            f"Sbicolor_v3.1.1{SEP}Sobic.001G000100.1.p"]

    def test_a_bare_integer_gene_id_is_now_parseable(self, tmp_path):
        """Smoellendorffii's ids are integers; concatenated with `_` there is
        no way to find the boundary."""
        src = _write(tmp_path, "Smoellendorffii_91_v1.0.protein.fa",
                     [("123858 pacid=1", "MKKA")])
        prep.prepare_one(src, str(tmp_path / "out.fa"), log=lambda m: None)
        header = _headers(tmp_path / "out.fa")[0]
        species, _, gene = header.partition(SEP)
        assert (species, gene) == ("Smoellendorffii_v1.0", "123858")

    def test_dots_in_the_species_name_survive(self, tmp_path):
        """OrthoFinder's own prefixing rewrites them; ours must not."""
        src = _write(tmp_path, "Gmax_508_Wm82.a4.v1.protein.fa",
                     [("Glyma.01G057200.1", "MKKA")])
        prep.prepare_one(src, str(tmp_path / "out.fa"), log=lambda m: None)
        assert _headers(tmp_path / "out.fa")[0].startswith("Gmax_Wm82.a4.v1" + SEP)

    def test_only_the_first_token_is_kept(self, tmp_path):
        src = _write(tmp_path, "X_1_v1.protein.fa",
                     [("AT1G01010.1 pacid=9 locus=AT1G01010 annot=x", "MKKA")])
        prep.prepare_one(src, str(tmp_path / "out.fa"), log=lambda m: None)
        assert _headers(tmp_path / "out.fa") == [f"X_v1{SEP}AT1G01010.1"]

    def test_sequence_bytes_are_untouched(self, tmp_path):
        """Only the header changes, so the residues are provably unaltered."""
        src = _write(tmp_path, "X_1_v1.protein.fa", [("a", "MKKA"), ("b", "WWY")])
        out = str(tmp_path / "out.fa")
        prep.prepare_one(src, out, log=lambda m: None)
        seqs = [l.rstrip("\n") for l in open(out) if not l.startswith(">")]
        assert seqs == ["MKKA", "WWY"]

    def test_input_order_is_preserved(self, tmp_path):
        """Order sets OrthoFinder's internal numbering; it must be a function
        of the input, not of the filesystem."""
        src = _write(tmp_path, "X_1_v1.protein.fa",
                     [("c", "M"), ("a", "M"), ("b", "M")])
        prep.prepare_one(src, str(tmp_path / "out.fa"), log=lambda m: None)
        assert [h.split(SEP)[1] for h in _headers(tmp_path / "out.fa")] == \
            ["c", "a", "b"]


class TestRefusals:
    """Better to stop than to emit a header nobody can split."""

    def test_a_separator_already_in_the_id_is_refused(self, tmp_path):
        src = _write(tmp_path, "X_1_v1.protein.fa", [(f"gene{SEP}x", "M")])
        with pytest.raises(ValueError, match="already contains"):
            prep.prepare_one(src, str(tmp_path / "out.fa"), log=lambda m: None)

    def test_duplicate_ids_are_refused(self, tmp_path):
        src = _write(tmp_path, "X_1_v1.protein.fa", [("g", "M"), ("g", "W")])
        with pytest.raises(ValueError, match="duplicate"):
            prep.prepare_one(src, str(tmp_path / "out.fa"), log=lambda m: None)

    def test_two_files_normalising_to_one_species_are_refused(self, tmp_path):
        """`Sbicolor_454_v3.1.1` and `Sbicolor_999_v3.1.1` collapse to the same
        name; OrthoFinder would silently treat them as one species."""
        src = tmp_path / "src"
        src.mkdir()
        for pid in ("454", "999"):
            _write(src, f"Sbicolor_{pid}_v3.1.1.protein.fa", [(f"g{pid}", "M")])
        with pytest.raises(ValueError, match="normalise to species"):
            prep.prepare(str(src), str(tmp_path / "out"), log=lambda m: None)

    def test_an_empty_directory_is_reported(self, tmp_path):
        (tmp_path / "src").mkdir()
        with pytest.raises(FileNotFoundError):
            prep.prepare(str(tmp_path / "src"), str(tmp_path / "out"),
                         log=lambda m: None)


class TestPrimaryOnly:
    def test_the_longest_transcript_per_locus_wins(self, tmp_path):
        src = _write(tmp_path, "X_1_v1.protein.fa", [
            ("AT1G01010.1 locus=AT1G01010", "MK"),
            ("AT1G01010.2 locus=AT1G01010", "MKKAAG"),
            ("AT1G01020.1 locus=AT1G01020", "WW"),
        ])
        out = str(tmp_path / "out.fa")
        report = prep.prepare_one(src, out, primary_only=True, log=lambda m: None)
        assert report["dropped"] == 1
        assert [h.split(SEP)[1] for h in _headers(out)] == \
            ["AT1G01010.2", "AT1G01020.1"]

    def test_it_is_off_by_default(self, tmp_path):
        src = _write(tmp_path, "X_1_v1.protein.fa", [
            ("A.1 locus=A", "MK"), ("A.2 locus=A", "MKKA")])
        prep.prepare_one(src, str(tmp_path / "out.fa"), log=lambda m: None)
        assert len(_headers(tmp_path / "out.fa")) == 2

    def test_locus_prefers_the_header_field(self, tmp_path):
        """`locus=` is authoritative; stripping a trailing number is a guess
        that is wrong for ids that merely end in one."""
        assert prep.locus_of("thing.1", "thing.1 locus=THING") == "THING"
        assert prep.locus_of("Sobic.001G161100.1.p") == "Sobic.001G161100"
        assert prep.locus_of("123858") == "123858"


def test_the_whole_directory_round_trips(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _write(src, "Athaliana_447_Araport11.protein.fa", [("AT1G01010.1", "MK")])
    _write(src, "Smoellendorffii_91_v1.0.protein.fa", [("123858", "WW")])
    report = prep.prepare(str(src), str(tmp_path / "out"), log=lambda m: None)

    assert report["proteomes"] == 2 and report["sequences"] == 2
    recovered = {}
    for name in os.listdir(tmp_path / "out"):
        for header in _headers(tmp_path / "out" / name):
            species, sep, gene = header.partition(SEP)
            assert sep == SEP and header.count(SEP) == 1
            recovered[gene] = species
    assert recovered == {"AT1G01010.1": "Athaliana_TAIR10",
                         "123858": "Smoellendorffii_v1.0"}
