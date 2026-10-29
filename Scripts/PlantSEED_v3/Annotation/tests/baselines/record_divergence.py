#!/usr/bin/env python3
"""Measure an intentional annotator change and append it to the ledger.

Run this AFTER making the change and BEFORE committing, then commit the
appended line together with the code:

    tests/baselines/record_divergence.py \
        --id baseline-percentile \
        --rationale "In-paralog baseline moved from the mean to the 10th
                     percentile because ..."

What it measures is the delta between what the annotator produces NOW and what
`v2.5 artifacts + the ledger as it already stands` predicts. That is deliberate:
each record is attributable to its own change rather than to the accumulated
drift, so the ledger reads as a timeline and a bad entry can be removed without
invalidating its neighbours.

Refuses to write an entry with no measured effect, and refuses to overwrite an
existing id — re-recording a change means deleting its line first, which should
be a visible edit in the diff rather than a silent replacement.
"""

import argparse
import datetime
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ANNOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, _ANNOT)
sys.path.insert(0, _HERE)

from plantseed_annotation import cli                                # noqa: E402
from ledger import (LEDGER, REPO, annotate_all, diff,               # noqa: E402
                    expected_functions, load_ledger, published,
                    reference_run)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True,
                    help="short kebab-case slug, e.g. baseline-percentile")
    ap.add_argument("--rationale", required=True,
                    help="why the change was made, in enough detail that "
                         "someone who did not make it can judge whether it "
                         "was right (>80 chars)")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--dry-run", action="store_true",
                    help="print the record instead of appending it")
    args = ap.parse_args(argv)

    run = reference_run()
    if run is None:
        raise SystemExit("the OrthoFinder run named in provenance.json is not "
                         "on this host; the delta cannot be measured here")
    entries = load_ledger()
    if any(e["id"] == args.id for e in entries):
        raise SystemExit(f"ledger already has an entry '{args.id}'; delete "
                         f"that line first if you mean to re-record it")
    if len(args.rationale) <= 80:
        raise SystemExit("rationale is too short to be useful to anyone later")

    deltas = {}
    for species, observed in annotate_all(run, cli).items():
        want = expected_functions(published(species), entries, species)
        lost, gained, changed = diff(want, observed)
        deltas[species] = {"lost": lost, "gained": gained, "changed": changed}
        print(f"  {species:<20} lost={len(lost):<4} gained={len(gained):<4} "
              f"changed={len(changed)}", file=sys.stderr)

    if not any(d["lost"] or d["gained"] or d["changed"] for d in deltas.values()):
        raise SystemExit("no measured effect on any genome — nothing to record. "
                         "If the change really is behaviour-neutral, it does not "
                         "belong in the ledger.")

    record = {"id": args.id, "date": args.date,
              "rationale": " ".join(args.rationale.split()), "deltas": deltas}
    line = json.dumps(record, sort_keys=True)
    if args.dry_run:
        print(line)
        return 0
    with open(LEDGER, "a") as fh:
        fh.write(line + "\n")
    print(f"appended '{args.id}' to {os.path.relpath(LEDGER, REPO)}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
