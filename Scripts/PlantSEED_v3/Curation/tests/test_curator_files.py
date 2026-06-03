"""Per-curator file I/O. The append helper is the one the CLI uses on every
action, so it gets the most coverage."""

import os

from plantseed_curation import curator_files as CF


def test_write_then_read_round_trip(tmp_db):
    CF.write_curator_file("vibhav", "test.tsv", "row1\nrow2")
    out = CF.read_curator_file("vibhav", "test.tsv")
    # write_curator_file ensures a trailing newline.
    assert out == "row1\nrow2\n"


def test_append_creates_and_extends(tmp_db):
    fp, n = CF.append_curator_file("vibhav", "log.tsv", ["a", "b"])
    assert n == 2
    fp2, n2 = CF.append_curator_file("vibhav", "log.tsv", ["c"])
    assert fp == fp2 and n2 == 1
    assert open(fp).read() == "a\nb\nc\n"


def test_append_handles_missing_trailing_newline(tmp_db):
    base = CF.curator_dir_path("vibhav")
    os.makedirs(base, exist_ok=True)
    fp = os.path.join(base, "log.tsv")
    with open(fp, "w") as f:
        f.write("first")  # no trailing newline
    CF.append_curator_file("vibhav", "log.tsv", ["second"])
    assert open(fp).read() == "first\nsecond\n"


def test_list_curator_files_skips_non_tsv(tmp_db):
    CF.write_curator_file("vibhav", "good.tsv", "a")
    CF.write_curator_file("vibhav", "ignored.txt", "b")  # sanitized to ignored.txt
    files = CF.list_curator_files("vibhav")
    names = [f["name"] for f in files]
    assert "good.tsv" in names
    assert "ignored.txt" not in names


def test_delete_curator_file(tmp_db):
    CF.write_curator_file("vibhav", "doomed.tsv", "x")
    assert CF.delete_curator_file("vibhav", "doomed.tsv") is True
    assert CF.read_curator_file("vibhav", "doomed.tsv") == ""
    assert CF.delete_curator_file("vibhav", "missing.tsv") is False


def test_parse_tsv_to_rows_extracts_columns():
    text = (
        "# header comment\n"
        "\n"
        "Alpha\tNEW\n"
        "Alpha\tADD\tfeatures\tF1\tc:PPDB\n"
        "bad-line-no-tabs\n"
    )
    rows = CF.parse_tsv_to_rows(text)
    # Comment line stripped; 3 actual rows remain.
    assert len(rows) == 3
    assert rows[0]["action"] == "NEW"
    assert rows[1]["extra"] == "c:PPDB"
    assert rows[2]["valid"] is False
