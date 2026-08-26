"""Run the shipped entry points the way a container runs them.

Every other test in this repo runs on a filesystem where everything is
writable, which is exactly the condition under which the rule in
`plantseed_core.runtime` cannot fail. KBase binds refdata at /data with
mode "ro" and CTS builds its refdata mount with writable=False, so a write
into an input directory is a crash there and a silent success here.

This module removes that asymmetry: it declares the mounts the way an adapter
would, makes the inputs genuinely read-only, and runs the real code paths. Two
assertions per case, and the second is the stronger one:

  1. the run succeeds — nothing tried to create a directory it may not
  2. the input tree is byte-for-byte unchanged afterwards — nothing wrote
     somewhere that merely happened to be permitted

(2) matters because chmod alone is a weak instrument. A test process that
owns the directory can still be granted a write by a permissive umask, by
running as root in a CI container, or on a filesystem that ignores the mode
bits. Comparing a snapshot catches the write regardless of whether the
kernel stopped it.

This is the test that would have caught `ensure_psi_cache` defaulting its
cache into `<results_dir>/Pairwise_Sequence_Identity/`.
"""

import contextlib
import json
import os
import stat

import pytest

from plantseed_core import runtime


_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, "..", "..", "..", ".."))
_PAPER = os.path.join(_REPO, "Papers", "bioflux-preprint-260807")
_TEMPLATE = os.path.join(_REPO, "Scripts", "PlantSEED_v3", "Template",
                         "PlantSEED_Biomass_Template.json")
_COMPARTMENTS = os.path.join(_REPO, "Data", "PlantSEED_v3", "Compartments",
                             "PlantSEED_Compartments.json")


# --- helpers -----------------------------------------------------------------

def snapshot(root):
    """Every path under `root` with its size and mtime.

    Directories are included: creating an empty one is a write, and it is
    precisely what the PSI bug did.
    """
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in list(dirnames) + list(filenames):
            p = os.path.join(dirpath, name)
            rel = os.path.relpath(p, root)
            st = os.lstat(p)
            out[rel] = (stat.S_IFMT(st.st_mode), st.st_size, st.st_mtime_ns)
    return out


def assert_untouched(root, before, what):
    after = snapshot(root)
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
    assert not (added or removed or changed), (
        f"{what} modified its input tree at {root}\n"
        f"  created: {added}\n  removed: {removed}\n  changed: {changed}\n"
        "Inputs are the refdata mount on KBase and CTS and are bound read-only "
        "there. Route the write through plantseed_core.runtime."
    )


@contextlib.contextmanager
def read_only(root):
    """Strip every write bit under `root`, and put them back afterwards.

    Directories are cleared last and restored first: a directory with no write
    bit cannot have its children's modes changed.
    """
    root = os.fspath(root)
    saved = {}
    entries = []
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            entries.append((os.path.join(dirpath, name), False))
        for name in dirnames:
            entries.append((os.path.join(dirpath, name), True))
    entries.append((root, True))
    # Files first, then directories deepest-first.
    entries.sort(key=lambda e: (e[1], -len(e[0].split(os.sep))))
    for p, _is_dir in entries:
        saved[p] = os.stat(p).st_mode
        os.chmod(p, saved[p] & ~0o222)
    try:
        yield
    finally:
        for p in sorted(saved, key=lambda p: len(p.split(os.sep))):
            with contextlib.suppress(FileNotFoundError):
                os.chmod(p, saved[p])


@pytest.fixture
def mounts(tmp_path, monkeypatch):
    """Declare the mount layout the way a KBase or CTS adapter would."""
    out = tmp_path / "output"
    scratch = tmp_path / "scratch"
    inp = tmp_path / "refdata"
    inp.mkdir()
    monkeypatch.setenv(runtime.OUTPUT_ENV, str(out))
    monkeypatch.setenv(runtime.SCRATCH_ENV, str(scratch))
    monkeypatch.setenv(runtime.INPUT_ENV, str(inp))
    assert runtime.strict_mode()
    return {"out": out, "scratch": scratch, "in": inp}


def _orthofinder_tree(root, n_ogs=3):
    """A minimal OrthoFinder results directory: MSAs are all psi.py reads."""
    msa = root / "MultipleSequenceAlignments"
    msa.mkdir(parents=True)
    for i in range(n_ogs):
        (msa / f"OG{i:07d}.fa").write_text(">a\nMKKAAG\n>b\nMKKAWG\n>c\nMKPAAG\n")
    return root


# --- the annotation path ------------------------------------------------------

def test_psi_cache_runs_against_a_read_only_refdata_mount(mounts):
    """The regression this module exists for."""
    from plantseed_annotation.algorithms import psi

    results = _orthofinder_tree(mounts["in"] / "OrthoFinder_Results")
    before = snapshot(mounts["in"])

    with read_only(mounts["in"]):
        cache_dir, stats = psi.ensure_psi_cache(
            str(results), n_workers=1, log=lambda m: None,
        )

    assert len(stats) == 3 and all(v == 3 for v in stats.values())
    assert runtime.is_writable_path(cache_dir)
    assert_untouched(mounts["in"], before, "ensure_psi_cache")


def test_a_prebuilt_cache_in_refdata_is_read_and_left_alone(mounts):
    """The production shape: refdata ships PSI computed at image-build time."""
    from plantseed_annotation.algorithms import psi

    results = _orthofinder_tree(mounts["in"] / "OrthoFinder_Results", n_ogs=2)
    prebuilt = results / psi.PSI_CACHE_DIRNAME
    prebuilt.mkdir()
    # Written with a plain open() on purpose: psi.write_cache_file is gated and
    # would (correctly) refuse this destination. An image build populates it
    # before the mount ever becomes an input.
    (prebuilt / "OG0000000.txt").write_text("OG0000000\ta:0.50\tb:0.50\t0.50\n")
    before = snapshot(mounts["in"])

    with read_only(mounts["in"]):
        write_dir, read_dirs = psi.cache_search_path(str(results))
        _, stats = psi.ensure_psi_cache(str(results), n_workers=1,
                                        log=lambda m: None)
        loaded = psi.load_psi_for_ogs(read_dirs, {"OG0000000", "OG0000001"})

    assert stats["OG0000000"] == 0            # served from refdata
    assert stats["OG0000001"] == 3            # computed into scratch
    assert psi.psi_lookup(loaded, "OG0000000", "a", "b") == 0.5
    assert not os.path.exists(os.path.join(write_dir, "OG0000000.txt"))
    assert_untouched(mounts["in"], before, "ensure_psi_cache with a prebuilt cache")


def test_annotated_genome_lands_in_the_output_mount(mounts):
    from plantseed_annotation.genome_io import write_annotated_genome

    dest = mounts["out"] / "annotated_genome.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    write_annotated_genome(str(dest), "g1",
                           {"geneA": {"status": "ANNOTATED",
                                      "function": "role1 # cytosol"}})
    assert json.loads(dest.read_text())["id"] == "g1"


def test_writing_outside_the_mounts_is_refused(mounts):
    from plantseed_annotation.genome_io import write_annotated_genome

    with pytest.raises(PermissionError):
        write_annotated_genome(str(mounts["in"] / "sneaky.json"), "g1", {})


# --- the reconstruction path --------------------------------------------------

_HAVE_PAPER = (os.path.isdir(_PAPER) and os.path.isfile(_TEMPLATE)
               and os.path.isfile(_COMPARTMENTS))


@pytest.mark.skipif(not _HAVE_PAPER,
                    reason="preprint artifacts / template not present (installed wheel)")
def test_reconstruct_cli_writes_only_to_the_output_mount(mounts, monkeypatch):
    """End-to-end through the console script, with the repo's real inputs
    read-only for the duration."""
    from plantseed_annotation import reconstruct_cli

    genome = os.path.join(_PAPER, "Athaliana_TAIR10_annotated_genome.json")
    out = mounts["out"] / "model.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    before = snapshot(_PAPER)

    with read_only(_PAPER):
        rc = reconstruct_cli.main([
            "--genome", genome, "--template", _TEMPLATE,
            "--compartments", _COMPARTMENTS, "--model-id", "ro_test",
            "--out", str(out), "--quiet",
        ])

    assert rc == 0
    assert json.loads(out.read_text())["modelreactions"]
    assert_untouched(_PAPER, before, "plantseed-reconstruct")


@pytest.mark.skipif(not _HAVE_PAPER,
                    reason="preprint artifacts / template not present (installed wheel)")
def test_reconstruct_cli_rejects_a_bad_destination_before_reconstructing(mounts, capsys):
    """Fail fast: the check is at the top of main(), not at the final open(),
    so a rejected destination costs a second rather than a full run."""
    from plantseed_annotation import reconstruct_cli

    with pytest.raises(SystemExit) as exc:
        reconstruct_cli.main([
            "--genome", os.path.join(_PAPER, "Athaliana_TAIR10_annotated_genome.json"),
            "--out", str(mounts["in"] / "model.json"), "--quiet",
        ])
    assert "refusing to write outside" in str(exc.value)
    assert "modelreactions" not in capsys.readouterr().out
