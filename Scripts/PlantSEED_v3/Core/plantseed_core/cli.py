"""`plantseed` — the top-level entry point.

Today it does one thing: emit the capability manifest. That is deliberately the
first thing built, because the manifest is what every other surface is
generated from, and because `<tool> capabilities --json` is verbatim the shape
KIND*AI's CAPABILITY_CONTRACT specifies for a tool to describe itself to the
agent.

Three properties this must keep, all of them requirements from somewhere:

  * machine-readable output on stdout, nothing else — koros parses it
  * works from any working directory; the agent session's cwd is ~/koros
  * no network, no credentials, no optional dependencies
"""

from __future__ import annotations

import argparse
import json
import sys

from . import registry


def _cmd_capabilities(args) -> int:
    manifest = registry.export_manifest()
    if args.json:
        json.dump(manifest, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    caps = manifest["capabilities"]
    if not caps:
        print("no capabilities registered", file=sys.stderr)
        return 0
    width = max(len(c["name"]) for c in caps)
    for c in caps:
        print(f"{c['name']:<{width}}  {c['summary'].splitlines()[0]}")
    return 0


def _cmd_describe(args) -> int:
    try:
        cap = registry.get(args.name)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    json.dump(cap.to_dict(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _cmd_version(args) -> int:
    from .__about__ import DATA_VERSION, __version__

    if args.json:
        json.dump({"version": __version__, "data_version": DATA_VERSION},
                  sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    else:
        print(f"plantseed {__version__} (data {DATA_VERSION})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="plantseed",
        description="PlantSEED v3 — plant genome annotation, metabolic "
                    "reconstruction and curation.",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("capabilities",
                       help="list registered capabilities (--json for the manifest)")
    p.add_argument("--json", action="store_true",
                   help="emit the full machine-readable manifest")
    p.set_defaults(handler=_cmd_capabilities)

    p = sub.add_parser("describe", help="emit one capability's declaration as JSON")
    p.add_argument("name")
    p.set_defaults(handler=_cmd_describe)

    p = sub.add_parser("version", help="package and data versions")
    p.add_argument("--json", action="store_true")
    p.set_defaults(handler=_cmd_version)

    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
