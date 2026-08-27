"""`plantseed-reconstruct` — thin CLI wrapper around
`plantseed_model.reconstruct.ReconstructAppImpl`.

Consumes:
  - an annotated genome JSON (as produced by plantseed-annotate)
  - a template JSON (default: Scripts/PlantSEED_v3/Template/PlantSEED_Neutral_Template.json)
  - a compartments JSON (default: Data/PlantSEED_v3/Compartments/PlantSEED_Compartments.json)

Produces an FBAModel-shaped JSON matching what
`plantseed_model.reconstruct.main` writes today (KBase-native format).

The wrapper is thin: argparse + a call into ReconstructAppImpl. All
algorithm changes should land in plantseed_model/reconstruct.py itself.
"""

import argparse
import json
import os
import sys

from plantseed_core import runtime

from . import paths


def _load_reconstruct_impl():
    """Return ReconstructAppImpl.

    Now a plain import: the engine is packaged as `plantseed_model.reconstruct`.
    Kept as a function so callers and tests keep the same seam, and so the failure
    mode stays a clear message rather than an ImportError traceback when someone
    runs from a source tree without installing.
    """
    try:
        from plantseed_model import ReconstructAppImpl
    except ImportError as exc:
        sys.exit(
            "ERROR: could not import plantseed_model. Install the distribution "
            f"(`pip install .` from the PlantSEED repo root) — {exc}"
        )
    return ReconstructAppImpl


def _default_template_path():
    """The packaged template.

    Delegates to `paths` so this one location is env-overridable like every
    other data path in the package. It was not, and that made it the single
    thing that could not be relocated: installed as a wheel — in a container,
    or from PyPI — the source-tree-relative path it used to compute does not
    exist, so `plantseed-reconstruct` without `--template` could only run from
    a checkout.
    """
    return paths.TEMPLATE_FILE


def _build_argparser():
    ap = argparse.ArgumentParser(
        prog="plantseed-reconstruct",
        description="Reconstruct a plant metabolic model from an annotated "
                    "genome JSON + PlantSEED template.",
    )
    ap.add_argument("--genome", required=True,
        help="Path to the annotated genome JSON (from plantseed-annotate).")
    ap.add_argument("--template", default=None,
        help="Path to the PlantSEED template JSON. Default: %s"
             % _default_template_path())
    ap.add_argument("--compartments", default=None,
        help="Path to PlantSEED_Compartments.json. Default: %s"
             % paths.COMPARTMENTS_FILE)
    ap.add_argument("--model-id", default=None,
        help="Model id / name. Default: genome_id + '_model'.")
    ap.add_argument("--out", required=True,
        help="Output FBAModel JSON path.")
    ap.add_argument("--log-rxn", default=None,
        help="Optional reaction id to trace verbosely during reconstruction.")
    ap.add_argument("--quiet", action="store_true")
    return ap


def main(argv=None):
    args = _build_argparser().parse_args(argv)

    def log(msg):
        if not args.quiet:
            print(msg, file=sys.stderr, flush=True)

    # Check the destination before doing the work, not after: a reconstruction
    # or a PSI sweep that dies on the final open() has burned the whole run.
    # No-op unless an adapter has declared the mounts.
    try:
        runtime.enforce_writable(args.out)
    except PermissionError as exc:
        sys.exit(f"ERROR: {exc}")

    genome_path       = os.path.abspath(args.genome)
    template_path     = os.path.abspath(args.template or _default_template_path())
    compartments_path = os.path.abspath(args.compartments or paths.COMPARTMENTS_FILE)

    log(f"[cfg] genome:       {genome_path}")
    log(f"[cfg] template:     {template_path}")
    log(f"[cfg] compartments: {compartments_path}")

    for p in (genome_path, template_path, compartments_path):
        if not os.path.isfile(p):
            sys.exit(f"ERROR: file not found: {p}")

    with open(genome_path) as fh:
        genome_obj = json.load(fh)
    with open(template_path) as fh:
        template_obj = json.load(fh)
    with open(compartments_path) as fh:
        compartments = json.load(fh)

    model_id = args.model_id or (genome_obj.get("id", "model") + "_model")

    ReconstructAppImpl = _load_reconstruct_impl()
    recon = ReconstructAppImpl()
    # --quiet previously silenced only this wrapper; the engine printed to
    # stdout regardless. Progress now goes to stderr and honours the flag, so
    # stdout carries nothing but what a caller is meant to parse.
    recon.quiet = args.quiet
    recon._set_objects({"genome": genome_obj, "template": template_obj})

    input_params = {"id": model_id, "name": model_id, "cpts": compartments}
    log(f"[recon] running reconstruct_metabolism (model_id={model_id})")
    metabolism = recon.reconstruct_metabolism(input_params, log_rxn=args.log_rxn)

    with open(args.out, "w") as fh:
        json.dump(metabolism, fh, indent=4, sort_keys=True)
    log(f"[out] wrote {args.out}")
    log(f"      modelreactions:   {len(metabolism.get('modelreactions', []))}")
    log(f"      modelcompounds:   {len(metabolism.get('modelcompounds', []))}")
    log(f"      biomasses:        {len(metabolism.get('biomasses', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
