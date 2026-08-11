#!/usr/bin/env python3
"""Fetch the external dependencies pinned in deps/external.json.

Three sources move faster than their PyPI registrations, so PlantSEED tracks
them by commit rather than by release:

    cobrakbase     Fxe/cobrakbase              adapter-only, never in the core
    modelseedpy    cshenry/ModelSEEDpy         gapfilling, ATP correction, FBA
    biochemistry   ModelSEED/ModelSEEDDatabase the ~80 MB reaction/compound data

They are deliberately NOT pyproject dependencies. A direct-reference (git+)
requirement makes the whole distribution un-publishable to PyPI, and pinning a
PyPI version would freeze us on releases that are already a year or more stale.

Stdlib only, so it runs before anything is installed — including inside a
container build step, which is its main use.

    python deps/fetch.py --list
    python deps/fetch.py                       # all three into ./deps/src
    python deps/fetch.py modelseedpy --install # clone and pip install it
    python deps/fetch.py --into /deps          # container layout
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

MANIFEST = Path(__file__).resolve().parent / "external.json"


def load():
    with open(MANIFEST) as fh:
        return json.load(fh)["dependencies"]


def run(cmd, cwd=None):
    print("  $", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def fetch_full(name, spec, dest: Path):
    """Clone at a pinned commit. --depth 1 needs the branch, then we hard-reset
    onto the commit; a bare `clone --depth 1 <sha>` is not supported by GitHub.
    """
    if dest.exists():
        print(f"{name}: {dest} exists — leaving it alone (delete to refetch)")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", "--quiet", "--branch", spec["branch"], spec["repo"], str(dest)])
    run(["git", "-C", str(dest), "checkout", "--quiet", spec["commit"]])


def fetch_sparse(name, spec, dest: Path):
    """Blobless sparse checkout — the repo is 1.32 GB, we need a fraction.

    --no-cone is required, not a preference. Cone mode only understands
    directory prefixes, so file-level patterns are silently ignored: asking for
    Biochemistry/reactions.tsv in cone mode yields the whole of
    Biochemistry/Structures and Biochemistry/Aliases instead, and 394 MB on
    disk. Verified the hard way.
    """
    if dest.exists():
        print(f"{name}: {dest} exists — leaving it alone (delete to refetch)")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
         "--branch", spec["branch"], spec["repo"], str(dest)])
    run(["git", "-C", str(dest), "sparse-checkout", "init", "--no-cone"])
    run(["git", "-C", str(dest), "sparse-checkout", "set", *spec["paths"]])
    run(["git", "-C", str(dest), "checkout", "--quiet", spec["commit"]])


def verify(name, spec, dest: Path) -> bool:
    if not dest.exists():
        print(f"{name}: MISSING at {dest}")
        return False
    got = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    ok = got == spec["commit"]
    print(f"{name}: {'ok  ' if ok else 'DRIFT'} {got[:12]}"
          + ("" if ok else f" (expected {spec['commit'][:12]})"))
    return ok


def install(name, spec, dest: Path):
    if spec.get("kind") != "python-package":
        return
    mode = spec.get("install", "pip-editable")
    cmd = [sys.executable, "-m", "pip", "install", "-e", str(dest)]
    if mode == "pip-editable-no-deps":
        # Deliberate: see pinned_because in the manifest. modelseedpy's
        # scikit-learn==1.2.0 pin does not build on 3.12 and we do not use the
        # code that needs it.
        cmd.insert(-1, "--no-deps")
    run(cmd)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*", help="subset to fetch (default: all)")
    ap.add_argument("--into", default=str(Path(__file__).resolve().parent / "src"),
                    help="destination directory (default: deps/src)")
    ap.add_argument("--install", action="store_true",
                    help="pip install the python packages after fetching")
    ap.add_argument("--list", action="store_true", help="show the pins and exit")
    ap.add_argument("--verify", action="store_true",
                    help="check existing checkouts match the pins; exit 1 on drift")
    args = ap.parse_args(argv)

    deps = load()
    unknown = set(args.names) - set(deps)
    if unknown:
        sys.exit(f"unknown dependency: {', '.join(sorted(unknown))}. "
                 f"known: {', '.join(deps)}")
    selected = {k: v for k, v in deps.items() if not args.names or k in args.names}
    root = Path(args.into).resolve()

    if args.list:
        for name, spec in selected.items():
            print(f"{name:14s} {spec['repo']}@{spec['commit'][:12]} "
                  f"({spec['branch']}, {spec['kind']})")
        return 0

    if args.verify:
        ok = all(verify(n, s, root / n) for n, s in selected.items())
        return 0 if ok else 1

    if not shutil.which("git"):
        sys.exit("git not found on PATH")

    for name, spec in selected.items():
        print(f"\n=== {name} ===")
        if spec.get("install") == "sparse-checkout":
            fetch_sparse(name, spec, root / name)
        else:
            fetch_full(name, spec, root / name)
        if args.install:
            install(name, spec, root / name)

    print(f"\nfetched into {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
