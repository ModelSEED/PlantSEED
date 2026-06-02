#!/usr/bin/env python
"""Apply a curator-authored TSV to PlantSEED_Roles.json.

Thin wrapper over `plantseed_curation.actions.run_apply` — the same code
path the dashboard's /api/apply endpoint uses. Preserved as a separate CLI
so existing `python3 Update_Enzymes_in_PlantSEED.py path/to/file.tsv`
workflows keep working unchanged.
"""

import os
import sys


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plantseed_curation import load_schema, run_apply


def _infer_curator(input_file):
    """Reproduce the original heuristic: curator name comes from the path,
    Curators/<gh-username>/.../<file>.tsv."""
    parts = os.path.abspath(input_file).split(os.sep)
    if "Curators" in parts:
        i = parts.index("Curators")
        if i + 1 < len(parts):
            return parts[i + 1]
    return ""


def main():
    if len(sys.argv) < 2:
        print("Error: missing argument.")
        print("Usage: Update_Enzymes_in_PlantSEED.py <path-to-updates.tsv>")
        sys.exit(1)

    input_file = sys.argv[1]
    if not os.path.isfile(input_file):
        print(f"Error: input file does not exist: {input_file}")
        print("Check the path and try again.")
        sys.exit(1)

    with open(input_file) as f:
        tsv_text = f.read()

    schema = load_schema()
    curator = _infer_curator(input_file)

    result = run_apply(tsv_text, curator, schema, dry_run=False)

    # Surface the issues the original printed inline. Errors go to stderr.
    for line in result.get("info", []):
        print(line)
    for w in result.get("warnings", []):
        print(f"[WARN] {w}")
    for e in result.get("errors", []):
        print(f"[ERROR] {e}", file=sys.stderr)

    print(
        f"\nCompleted with {len(result.get('warnings', []))} warning(s) and "
        f"{len(result.get('errors', []))} error(s)."
    )
    if result.get("errors"):
        sys.exit(2)


if __name__ == "__main__":
    main()
