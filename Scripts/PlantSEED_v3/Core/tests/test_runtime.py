"""Tests for the writable-root contract.

These encode a rule that cannot fail locally: on poplar every directory is
writable, so a violation only appears inside a KBase or CTS container — and
for CTS, during a manual image review. The tests are the only place the rule
is checkable before then.
"""

import os
import tempfile
from pathlib import Path

import pytest

from plantseed_core import runtime


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    out, scratch, inp = tmp_path / "out", tmp_path / "scratch", tmp_path / "in"
    inp.mkdir()
    monkeypatch.setenv(runtime.OUTPUT_ENV, str(out))
    monkeypatch.setenv(runtime.SCRATCH_ENV, str(scratch))
    monkeypatch.setenv(runtime.INPUT_ENV, str(inp))
    return {"out": out, "scratch": scratch, "in": inp}


class TestRoots:
    def test_output_root_is_created(self, dirs):
        assert runtime.output_root().is_dir()

    def test_output_root_can_be_probed_without_creating(self, dirs):
        runtime.output_root(create=False)
        assert not dirs["out"].exists()

    def test_scratch_defaults_to_the_temporary_directory(self, monkeypatch):
        monkeypatch.delenv(runtime.SCRATCH_ENV, raising=False)
        assert runtime.scratch_dir(create=False) == Path(tempfile.gettempdir()).resolve()

    def test_named_scratch_is_a_subdirectory(self, dirs):
        assert runtime.scratch_dir("psi").parent == dirs["scratch"].resolve()

    def test_input_root_is_not_writable(self, dirs):
        assert not runtime.is_writable_path(dirs["in"])


class TestTheRule:
    def test_output_and_scratch_are_writable(self, dirs):
        for k in ("out", "scratch"):
            assert runtime.is_writable_path(dirs[k])

    def test_nested_paths_under_a_root_are_writable(self, dirs):
        assert runtime.is_writable_path(dirs["out"] / "a" / "b.json")

    def test_everything_else_is_refused(self, dirs, tmp_path):
        for bad in (dirs["in"] / "cache", tmp_path / "elsewhere", Path("/data/x")):
            assert not runtime.is_writable_path(bad)

    def test_assert_writable_returns_the_path(self, dirs):
        p = dirs["out"] / "model.json"
        assert runtime.assert_writable(p) == p.resolve()

    def test_assert_writable_raises_with_a_usable_message(self, dirs):
        with pytest.raises(PermissionError) as exc:
            runtime.assert_writable(dirs["in"] / "cache" / "og.txt")
        msg = str(exc.value)
        assert "permitted" in msg and runtime.SCRATCH_ENV in msg

    def test_the_refdata_case_this_exists_for(self, dirs, monkeypatch):
        """psi.ensure_psi_cache used to default its cache inside results_dir,
        which on KBase and CTS is the read-only refdata mount. It now routes
        through scratch_dir(); this pins the distinction that made it wrong."""
        refdata = dirs["in"] / "OrthoFinder_Results"
        assert not runtime.is_writable_path(refdata / "Pairwise_Sequence_Identity")
        assert runtime.is_writable_path(runtime.scratch_dir("Pairwise_Sequence_Identity"))


class TestNoPlatformInference:
    def test_defaults_need_no_environment(self, monkeypatch):
        """The core must work with nothing set — an adapter supplies the paths,
        the core never guesses which platform it is on."""
        for v in (runtime.INPUT_ENV, runtime.OUTPUT_ENV, runtime.SCRATCH_ENV):
            monkeypatch.delenv(v, raising=False)
        assert runtime.writable_roots()
        assert runtime.input_root() == Path.cwd().resolve()


class TestStrictMode:
    """`enforce_writable` is the form writers actually call: silent on a
    workstation, hard failure once an adapter has declared the mounts."""

    def test_off_until_the_platform_declares_itself(self, monkeypatch):
        monkeypatch.delenv(runtime.OUTPUT_ENV, raising=False)
        assert not runtime.strict_mode()

    def test_on_once_output_is_declared(self, dirs):
        assert runtime.strict_mode()

    def test_unconfigured_allows_an_arbitrary_destination(self, tmp_path, monkeypatch):
        """`--out /scratch/seaver/model.json` on poplar is not an error, and a
        gate that called it one would be turned off within a day."""
        monkeypatch.delenv(runtime.OUTPUT_ENV, raising=False)
        target = tmp_path / "anywhere" / "model.json"
        assert runtime.enforce_writable(target) == target.resolve()

    def test_configured_refuses_a_destination_outside_the_roots(self, dirs):
        with pytest.raises(PermissionError):
            runtime.enforce_writable(dirs["in"] / "model.json")

    def test_configured_still_allows_the_roots(self, dirs):
        for p in (dirs["out"] / "model.json", dirs["scratch"] / "og.txt"):
            assert runtime.enforce_writable(p) == p.resolve()

    def test_scratch_stays_writable_when_only_output_is_declared(self, tmp_path, monkeypatch):
        """An adapter that sets OUTPUT_ENV alone must not lock the temp dir —
        that is where the PSI cache lands."""
        monkeypatch.setenv(runtime.OUTPUT_ENV, str(tmp_path / "out"))
        monkeypatch.delenv(runtime.SCRATCH_ENV, raising=False)
        assert runtime.enforce_writable(runtime.scratch_dir("psi", create=False))
