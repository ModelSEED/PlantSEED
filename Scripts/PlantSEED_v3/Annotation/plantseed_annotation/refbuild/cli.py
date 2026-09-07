"""`plantseed-refbuild` — build a refdata bundle from an OrthoFinder run.

    plantseed-refbuild build --orthofinder-results DIR --bundle-dir DIR --version v0
    plantseed-refbuild verify --bundle-dir DIR [--tier kbase]

The build is pure Python and reads nothing but the OrthoFinder output and the
curated data in this repository, so it needs none of SHOOT, MAFFT, EPA-ng or
gappa. That is deliberate: those tools gate the *enrichment* step, and a
bundle that carries the pruned families, their PSI matrices and the curation
payload is already enough to annotate against the existing reference and to
reproduce the published models. Enrichment turns this v0 into v1 later.

The build is byte-reproducible: the same OrthoFinder run and the same roles
file produce the same bytes, and `--source-date-epoch` pins the one field that
would otherwise differ. `verify` checks a bundle against its own manifest.
"""

from __future__ import annotations

import argparse
import os
import sys

from .. import paths
from ..algorithms import orthofinder_io
from . import build_curation, build_psi_matrices, bundle, prune, stamp_version

__all__ = ["build", "main"]


def build(results_dir, bundle_dir, version, *, n_workers=None, species=None,
          log=print) -> dict:
    """Prune, copy families, compute PSI, write curation, stamp. In that order.

    Stamping is last because the manifest hashes the payload; running it
    earlier would record a bundle that does not exist yet.
    """
    ogs_tsv = os.path.join(results_dir, "Orthogroups", "Orthogroups.tsv")
    if not os.path.isfile(ogs_tsv):
        raise FileNotFoundError(f"no Orthogroups.tsv under {results_dir}")

    log(f"[build] {version} from {results_dir}")
    # load_orthogroups returns (ogs, species_list), not just ogs.
    ogs, run_species = orthofinder_io.load_orthogroups(ogs_tsv)
    selected = prune.curated_orthogroups(ogs, species=species)
    report = prune.prune_report(ogs, selected)
    log(f"[prune] {report['og_kept']}/{report['og_total']} orthogroups touch "
        f"curated genes ({report['kept_fraction']:.1%})")

    bundle.ensure_layout(bundle_dir)
    families = prune.write_families(results_dir, bundle_dir, selected, log=log)
    psi = build_psi_matrices.build(results_dir, bundle_dir, selected,
                                   n_workers=n_workers, log=log)
    curation = build_curation.build(bundle_dir, log=log)

    manifest = stamp_version.stamp(
        bundle_dir, version, log=log,
        totals={"protein_count": curation["curated_features"]},
        sources={"phytozome_release": os.path.basename(results_dir.rstrip("/")),
                 "run_species": sorted(run_species)},
    )
    return {"manifest": manifest, "prune": report, "families": families,
            "psi": psi, "curation": curation}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="plantseed-refbuild",
        description="Build or verify a PlantSEED refdata bundle.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build a bundle from an OrthoFinder run")
    b.add_argument("--orthofinder-results", required=True)
    b.add_argument("--bundle-dir", required=True)
    b.add_argument("--version", required=True,
                   help="bundle version tag, e.g. v0 (see manifest_schema.json)")
    b.add_argument("--species", default=None,
                   help="restrict pruning to one species' curated genes. The "
                        "default keeps orthogroups curated in ANY species, "
                        "which is what carries specialized metabolism.")
    b.add_argument("--workers", type=int, default=None)
    b.add_argument("--source-date-epoch", default=None,
                   help="pin created_utc for a byte-reproducible build")
    b.add_argument("--quiet", action="store_true")

    v = sub.add_parser("verify", help="check a bundle against its manifest")
    v.add_argument("--bundle-dir", default=None)
    v.add_argument("--tier", default=None, choices=("kbase", "poplar", "local"))
    v.add_argument("--fast", action="store_true",
                   help="skip content hashing — a liveness probe, not a check")

    args = ap.parse_args(argv)

    def log(msg):
        if not getattr(args, "quiet", False):
            print(msg, file=sys.stderr, flush=True)

    if args.cmd == "build":
        if args.source_date_epoch:
            os.environ["SOURCE_DATE_EPOCH"] = args.source_date_epoch
        result = build(os.path.abspath(args.orthofinder_results),
                       os.path.abspath(args.bundle_dir), args.version,
                       n_workers=args.workers, species=args.species, log=log)
        print(result["manifest"]["content_id"])
        return 0

    from .. import reference

    ok, issues = reference.verify(args.bundle_dir, tier=args.tier,
                                  check_hashes=not args.fast)
    root = reference.bundle_dir(args.bundle_dir)
    if ok:
        print(f"OK  {root}  content_id "
              f"{reference.content_id(args.bundle_dir)[:12]}")
        return 0
    print(f"FAILED  {root}", file=sys.stderr)
    for issue in issues[:40]:
        print(f"  - {issue}", file=sys.stderr)
    if len(issues) > 40:
        print(f"  ... and {len(issues) - 40} more", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
