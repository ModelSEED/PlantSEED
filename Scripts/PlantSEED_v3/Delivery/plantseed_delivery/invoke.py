"""Running a declared capability from inside a long-lived server.

Two things differ from a one-shot container, and both are here rather than in
the tool definitions so the MCP layer stays thin.

**Where output goes.** `runtime.output_root()` reads process-global env, which
is exactly right for a CTS job — one process, one output mount — and wrong for
a server handling concurrent calls. Each call gets its own directory under
`runtime.scratch_dir("mcp")` and passes the path explicitly; the writers
already take their destination as a parameter and are already gated by
`runtime.enforce_writable`, so nothing global is mutated.

**What comes back.** Not the artifact. An Athaliana model is 1218 reactions and
1313 compounds; inlining that as a tool result would spend the session's entire
context on one call. Tools return counts, a path and a content hash, and the
caller reads the file if it wants the model.

Invocation is per-capability on purpose. The *tool surface* is generic over the
registry — name, description and schema all come from the declaration — but
turning params into an actual call is not, because the registry declares no
CLI-argv convention yet. With one capability, a dict of adapters is honest;
inventing a general argv contract before `annotate` exists would be guessing.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile

from plantseed_core import registry, runtime

__all__ = ["reconstruct", "INVOKERS", "call"]


def _fresh_output_dir() -> str:
    """A private, writable directory for one call."""
    return tempfile.mkdtemp(prefix="run-", dir=str(runtime.scratch_dir("mcp")))


def _artifact_path(capability: str, key: str, out_dir: str) -> str:
    """The declared filename for one of a capability's outputs.

    Read from the registry rather than hardcoded, so renaming an `Artifact`
    moves the file here too.
    """
    cap = registry.get(capability)
    for art in cap.outputs:
        if art.key == key:
            return os.path.join(out_dir, art.filename)
    raise KeyError(f"{capability} declares no output {key!r}")


def _digest(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def reconstruct(genome: str, template: str | None = None,
                compartments: str | None = None,
                model_id: str | None = None) -> dict:
    """Reconstruct a model. Mirrors `plantseed-reconstruct`'s parameters.

    Called in-process rather than as a subprocess: the run is sub-second and
    pure Python, and going through `main()` keeps the CLI's own default
    resolution for template and compartments rather than duplicating it. The
    CLI signals failure with `sys.exit`, so `SystemExit` is a result here, not
    a crash.
    """
    from plantseed_annotation import reconstruct_cli

    if not genome or not os.path.isfile(genome):
        return {"error": f"genome not found: {genome!r}"}

    out_dir = _fresh_output_dir()
    out_path = _artifact_path("reconstruct", "model", out_dir)

    argv = ["--genome", genome, "--out", out_path, "--quiet"]
    for flag, value in (("--template", template),
                        ("--compartments", compartments),
                        ("--model-id", model_id)):
        if value:
            argv += [flag, value]

    try:
        rc = reconstruct_cli.main(argv)
    except SystemExit as exc:                    # argparse / an input error
        return {"error": str(exc.code) if exc.code else "reconstruction failed"}
    except Exception as exc:                     # never take the server down
        return {"error": f"reconstruction failed: {exc}"}
    if rc != 0:
        return {"error": f"plantseed-reconstruct exited {rc}"}

    with open(out_path) as fh:
        model = json.load(fh)
    # Only the `model` artifact: `reconstruct` also declares a `provenance`
    # output that the CLI does not yet write. Reporting a path for a file that
    # is not there would be worse than not reporting it.
    return {
        "model_id": model.get("id"),
        "model_path": out_path,
        "sha256": _digest(out_path),
        "n_reactions": len(model.get("modelreactions") or []),
        "n_compounds": len(model.get("modelcompounds") or []),
        "n_biomasses": len(model.get("biomasses") or []),
        "note": "The model is on disk, not inlined — it is too large for a "
                "tool result. Read model_path, or ask for a summary.",
    }


#: capability name -> the callable that runs it. A capability without an entry
#: is declared but not yet reachable over MCP, which `call` says out loud.
INVOKERS = {"reconstruct": reconstruct}


def call(capability: str, **kwargs) -> dict:
    invoker = INVOKERS.get(capability)
    if invoker is None:
        return {"error": f"capability {capability!r} is declared but has no "
                         "MCP invoker yet"}
    return invoker(**kwargs)
