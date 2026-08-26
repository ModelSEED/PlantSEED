"""psi — pairwise sequence identity computation + cache."""

import os

import pytest

from plantseed_core import runtime

from plantseed_annotation.algorithms import psi


@pytest.fixture(autouse=True)
def isolated_scratch(tmp_path, monkeypatch):
    """Point the scratch root at tmp_path for every test in this module.

    The PSI cache now defaults into runtime.scratch_dir(); without this the
    suite would write into the real system temp dir and two runs of the suite
    could see each other's caches.
    """
    monkeypatch.setenv(runtime.SCRATCH_ENV, str(tmp_path / "scratch"))


def test_compute_psi_for_msa_identical_pair():
    """Two identical, no-gap sequences → PSI = 1.0."""
    rows = psi.compute_psi_for_msa({"a": "MKKAA", "b": "MKKAA"})
    assert len(rows) == 1
    g1, g2, id1, id2, p = rows[0]
    assert (g1, g2) == ("a", "b")
    assert id1 == id2 == p == 1.0


def test_compute_psi_for_msa_completely_different():
    """No matching positions → PSI = 0.0."""
    rows = psi.compute_psi_for_msa({"a": "MKKAA", "b": "PPPPP"})
    _, _, id1, id2, p = rows[0]
    assert id1 == id2 == p == 0.0


def test_compute_psi_for_msa_gaps_shrink_denominator():
    """A gap-inserted position doesn't count toward matches OR toward the
    denominator (which uses the *unaligned* length of each sequence)."""
    # a: 5 non-gap chars, b: 5 non-gap chars, 5 matches (excluding the gap)
    rows = psi.compute_psi_for_msa({"a": "MKKAA-", "b": "MKKAA-"})
    _, _, id1, id2, p = rows[0]
    assert id1 == id2 == p == 1.0

    # a: 6 non-gap chars, b: 5 non-gap chars (a has a residue where b has a gap)
    rows = psi.compute_psi_for_msa({"a": "MKKAAA", "b": "MKKAA-"})
    _, _, id1, id2, p = rows[0]
    # 5 matches (positions 0-4); pos 5 skipped (gap on b)
    # id1 = 5/6, id2 = 5/5 = 1.0
    assert id1 == pytest.approx(5 / 6)
    assert id2 == 1.0
    assert p == pytest.approx((5 / 6 + 1.0) / 2)


def test_compute_psi_for_msa_pair_ordering_is_alphabetical():
    """Rows are sorted so the pair (features[i], features[j]) always has
    features[i] < features[j]. Callers depend on this for cache lookup."""
    rows = psi.compute_psi_for_msa({"z": "MK", "a": "MK", "m": "MK"})
    pairs = [(r[0], r[1]) for r in rows]
    assert pairs == [("a", "m"), ("a", "z"), ("m", "z")]


def test_psi_cache_roundtrip(tmp_path):
    """write_cache_file → read_cache_file yields the same rows (with the
    2-decimal rounding the file format imposes)."""
    rows = [
        ("a", "b", 0.75, 0.80, 0.775),
        ("a", "c", 0.55, 0.60, 0.575),
    ]
    p = tmp_path / "OG0000001.txt"
    psi.write_cache_file(str(p), "OG0000001", rows)
    loaded = psi.read_cache_file(str(p))
    assert len(loaded) == 2
    for orig, back in zip(rows, loaded):
        assert orig[0] == back[0] and orig[1] == back[1]
        # 2-decimal rounding
        assert round(orig[2], 2) == round(back[2], 2)
        assert round(orig[3], 2) == round(back[3], 2)
        assert round(orig[4], 2) == round(back[4], 2)


def test_ensure_psi_cache_computes_then_caches(tmp_path):
    """First call computes; second call finds the cache and skips."""
    of = tmp_path / "Results"
    (of / "MultipleSequenceAlignments").mkdir(parents=True)
    (of / "MultipleSequenceAlignments" / "OG0000001.fa").write_text(
        ">a\nMKKAA\n>b\nMKKAA\n"
    )
    cache1, stats1 = psi.ensure_psi_cache(str(of), n_workers=1, log=lambda m: None)
    assert os.path.isfile(os.path.join(cache1, "OG0000001.txt"))
    assert stats1.get("OG0000001") == 1  # 1 pair

    # Second call: cache hit
    cache2, stats2 = psi.ensure_psi_cache(str(of), n_workers=1, log=lambda m: None)
    assert cache1 == cache2
    # Cache hit shows up as 0 in the returned stats (nothing recomputed)
    assert stats2.get("OG0000001") == 0


def test_ensure_psi_cache_restricts_by_ogs(tmp_path):
    """Passing `ogs=` restricts computation to the requested OGs; others are
    ignored."""
    of = tmp_path / "Results"
    (of / "MultipleSequenceAlignments").mkdir(parents=True)
    for og in ("OG0000001", "OG0000002"):
        (of / "MultipleSequenceAlignments" / (og + ".fa")).write_text(
            ">a\nMK\n>b\nMK\n"
        )
    cache_dir, stats = psi.ensure_psi_cache(
        str(of), ogs={"OG0000001"}, n_workers=1, log=lambda m: None,
    )
    assert os.path.isfile(os.path.join(cache_dir, "OG0000001.txt"))
    assert not os.path.isfile(os.path.join(cache_dir, "OG0000002.txt"))


def test_psi_lookup_order_independent(tmp_path):
    """Lookup by (a, b) or (b, a) returns the same PSI."""
    of = tmp_path / "Results"
    (of / "MultipleSequenceAlignments").mkdir(parents=True)
    (of / "MultipleSequenceAlignments" / "OG0000001.fa").write_text(
        ">a\nMKKAA\n>b\nMKKAA\n"
    )
    cache_dir, _ = psi.ensure_psi_cache(str(of), n_workers=1, log=lambda m: None)
    loaded = psi.load_psi_for_ogs(cache_dir, {"OG0000001"})
    assert psi.psi_lookup(loaded, "OG0000001", "a", "b") == 1.0
    assert psi.psi_lookup(loaded, "OG0000001", "b", "a") == 1.0
    assert psi.psi_lookup(loaded, "OG0000001", "a", "missing") is None


# --- cache location: the read-only-refdata fix -------------------------------

def _one_og_results(tmp_path, name="Results"):
    of = tmp_path / name
    (of / "MultipleSequenceAlignments").mkdir(parents=True)
    (of / "MultipleSequenceAlignments" / "OG0000001.fa").write_text(
        ">a\nMKKAA\n>b\nMKKAA\n"
    )
    return of


def test_default_cache_never_lands_inside_results_dir(tmp_path):
    """The whole point: results_dir is the refdata mount on KBase and CTS, and
    it is bound read-only there."""
    of = _one_og_results(tmp_path)
    cache_dir, _ = psi.ensure_psi_cache(str(of), n_workers=1, log=lambda m: None)

    assert runtime.is_writable_path(cache_dir)
    assert not os.path.isdir(of / psi.PSI_CACHE_DIRNAME)
    assert os.path.realpath(str(of)) not in os.path.realpath(cache_dir)


def test_default_cache_survives_a_read_only_results_dir(tmp_path):
    """The failure this replaces: makedirs inside a 0o555 input."""
    of = _one_og_results(tmp_path)
    os.chmod(of, 0o555)
    try:
        cache_dir, stats = psi.ensure_psi_cache(
            str(of), n_workers=1, log=lambda m: None,
        )
        assert stats.get("OG0000001") == 1
        assert os.path.isfile(os.path.join(cache_dir, "OG0000001.txt"))
    finally:
        os.chmod(of, 0o755)


def test_two_runs_do_not_share_a_cache(tmp_path):
    """OrthoFinder numbers OGs from OG0000000 every time, so an unscoped
    scratch cache would serve one run's PSI for another run's orthogroups."""
    a = _one_og_results(tmp_path, "Results_A")
    b = _one_og_results(tmp_path, "Results_B")
    dir_a, _ = psi.cache_search_path(str(a))
    dir_b, _ = psi.cache_search_path(str(b))
    assert dir_a != dir_b


def test_cache_dir_is_stable_across_calls(tmp_path):
    of = _one_og_results(tmp_path)
    assert psi.cache_search_path(str(of))[0] == psi.cache_search_path(str(of))[0]


def test_prebuilt_cache_beside_results_is_read_not_rewritten(tmp_path):
    """A cache already sitting in results_dir — an existing poplar cache, or
    refdata shipping PSI computed at image-build time — must still be used."""
    of = _one_og_results(tmp_path)
    legacy = of / psi.PSI_CACHE_DIRNAME
    legacy.mkdir()
    psi.write_cache_file(str(legacy / "OG0000001.txt"), "OG0000001",
                         [("a", "b", 0.5, 0.5, 0.5)])
    before = (legacy / "OG0000001.txt").read_text()

    write_dir, read_dirs = psi.cache_search_path(str(of))
    assert str(legacy) in read_dirs and read_dirs[0] == write_dir

    _, stats = psi.ensure_psi_cache(str(of), n_workers=1, log=lambda m: None)
    assert stats.get("OG0000001") == 0            # cache hit, nothing recomputed
    assert not os.path.isfile(os.path.join(write_dir, "OG0000001.txt"))
    assert (legacy / "OG0000001.txt").read_text() == before

    # ...and the values that reach the annotator are the prebuilt ones.
    loaded = psi.load_psi_for_ogs(read_dirs, {"OG0000001"})
    assert psi.psi_lookup(loaded, "OG0000001", "a", "b") == 0.5


def test_load_psi_for_ogs_accepts_a_single_dir_or_a_search_path(tmp_path):
    of = _one_og_results(tmp_path)
    cache_dir, _ = psi.ensure_psi_cache(str(of), n_workers=1, log=lambda m: None)
    one = psi.load_psi_for_ogs(cache_dir, {"OG0000001"})
    many = psi.load_psi_for_ogs([cache_dir, str(tmp_path / "nope")], {"OG0000001"})
    assert one == many


def test_explicit_cache_dir_still_wins(tmp_path):
    of = _one_og_results(tmp_path)
    mine = tmp_path / "mine"
    cache_dir, _ = psi.ensure_psi_cache(
        str(of), cache_dir=str(mine), n_workers=1, log=lambda m: None,
    )
    assert cache_dir == str(mine)
    assert os.path.isfile(mine / "OG0000001.txt")
