"""`plantseed-reconstruct` — thin CLI wrapper around
`Scripts/PlantSEED_v3/Model/reconstruct_app_impl.py::ReconstructAppImpl`.

Consumes:
  - an annotated genome JSON (as produced by plantseed-annotate)
  - a template JSON (default: Scripts/PlantSEED_v3/Template/PlantSEED_Neutral_Template.json)
  - a compartments JSON (default: Data/PlantSEED_v3/Compartments/PlantSEED_Compartments.json)

Produces an FBAModel-shaped JSON matching what
`reconstruct_app_impl.py::main` writes today (KBase-native format).

The wrapper is thin: argparse + a call into ReconstructAppImpl. All
algorithm changes should land in reconstruct_app_impl.py itself.
"""

import argparse
import importlib.util
import json
import os
import sys

from . import paths


def _load_reconstruct_impl():
    """Import ReconstructAppImpl from Scripts/PlantSEED_v3/Model/reconstruct_app_impl.py
    (which isn't packaged, so we load it by path)."""
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.normpath(os.path.join(here, "..", "..", "..", ".."))
    impl_path = os.path.join(
        repo_root, "Scripts", "PlantSEED_v3", "Model", "reconstruct_app_impl.py",
    )
    if not os.path.isfile(impl_path):
        sys.exit(f"ERROR: reconstruct_app_impl.py not found at {impl_path}")
    spec = importlib.util.spec_from_file_location("reconstruct_app_impl", impl_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ReconstructAppImpl


def _default_template_path():
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.normpath(os.path.join(here, "..", "..", "..", ".."))
    return os.path.join(
        repo_root, "Scripts", "PlantSEED_v3", "Template",
        "PlantSEED_Biomass_Template.json",
    )


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
