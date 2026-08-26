"""Where it is legal to write.

Every delivery platform mounts reference data read-only — KBase binds refdata
at /data with mode "ro", and CTS's executor builds its refdata mount with
writable=False. CTS additionally requires, as a condition of image approval,
that a container "not write to anywhere except the output folder and the
temporary directory" (cdm-task-service docs/admin_image_setup.md).

The trap is that none of this reproduces locally. On poplar the reference
directory is ordinary writable disk, so code that caches beside its inputs
passes every test and fails only inside the two containers that are hardest to
re-run — and, for CTS, during a manual per-version human review. So the rule
lives here as code rather than as something we remember.

Two writable roots, no others:

    output_root()   artifacts the caller asked for
    scratch_dir()   anything transient

Reading is unrestricted; `input_root()` is provided for symmetry and is never
writable. Everything is env-driven with plain defaults, so the core never
infers which platform it is on — an adapter sets the variables, the core obeys.

Writers call `enforce_writable()` on a caller-supplied destination. It is a
no-op until an adapter declares the mounts, because the alternative refuses
`--out /scratch/seaver/model.json` on a workstation, where the roots default
to the cwd and the temp dir and nothing has gone wrong. Silent locally, hard
failure wherever the platform is declared — which is where the rule exists.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

__all__ = [
    "INPUT_ENV", "OUTPUT_ENV", "SCRATCH_ENV",
    "input_root", "output_root", "scratch_dir", "writable_roots",
    "is_writable_path", "assert_writable", "strict_mode", "enforce_writable",
]

INPUT_ENV = "PLANTSEED_INPUT_DIR"
OUTPUT_ENV = "PLANTSEED_OUTPUT_DIR"
SCRATCH_ENV = "PLANTSEED_SCRATCH_DIR"


def _resolved(value) -> Path:
    return Path(value).expanduser().resolve()


def input_root() -> Path:
    """Where inputs are read from. Never writable. Defaults to the cwd."""
    return _resolved(os.environ.get(INPUT_ENV) or Path.cwd())


def output_root(create: bool = True) -> Path:
    """The single directory artifacts go in.

    CTS collects results with `find <mount> -type f` and strips the mount
    prefix, so everything written here comes back to the caller and nesting
    buys nothing.
    """
    p = _resolved(os.environ.get(OUTPUT_ENV) or Path.cwd())
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


def scratch_dir(name: str | None = None, create: bool = True) -> Path:
    """A writable temporary directory.

    Use this for caches. The motivating case is `psi.ensure_psi_cache`, whose
    default is a subdirectory of its own input — which is the read-only
    refdata mount on both KBase and CTS.
    """
    root = _resolved(os.environ.get(SCRATCH_ENV) or tempfile.gettempdir())
    p = root / name if name else root
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


def writable_roots() -> tuple[Path, ...]:
    """Every directory this process may write to. Nothing else is legal."""
    return (output_root(create=False), scratch_dir(create=False))


def is_writable_path(path) -> bool:
    p = _resolved(path)
    return any(p == r or r in p.parents for r in writable_roots())


def strict_mode() -> bool:
    """True once a platform adapter has declared where output goes.

    `OUTPUT_ENV` is the signal: the core cannot tell a container from a login
    node, and must not try, so it takes the adapter setting that variable as
    the statement that the mount layout is now real and enforceable.
    """
    return bool(os.environ.get(OUTPUT_ENV))


def enforce_writable(path) -> Path:
    """`assert_writable` where the platform is declared; a no-op where it isn't.

    Call this — not `assert_writable` — at the top of any function that writes
    to a destination it was handed. The unconditional form would break ordinary
    CLI use, where `--out` is an arbitrary path and the default roots are the
    cwd and the temp dir. Under KBase or CTS the adapter sets `OUTPUT_ENV` and
    the same call becomes a hard stop before the file is opened.
    """
    return assert_writable(path) if strict_mode() else _resolved(path)


def assert_writable(path) -> Path:
    """Return `path`, or raise if it lies outside the writable roots.

    Call before opening any file for writing whose destination is caller- or
    config-supplied. The message names the roots so the fix is obvious.
    """
    p = _resolved(path)
    if not is_writable_path(p):
        roots = ", ".join(str(r) for r in writable_roots())
        raise PermissionError(
            f"refusing to write outside the writable roots: {p}\n"
            f"  permitted: {roots}\n"
            f"  set {OUTPUT_ENV} / {SCRATCH_ENV}, or route through "
            f"plantseed_core.runtime.scratch_dir()"
        )
    return p
