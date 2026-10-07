#!/usr/bin/env python
"""Load a biomass file into a model and run FBA.

Generalized companion to Test-Model-FBA.py: that script runs FBA against
whatever biomass is already baked into the model's template. This one adds
one more biomass file's compounds on top -- at a small coefficient, as
additional draws on the existing biomass reaction -- before optimizing, so a
specialized biomass list (glucosinolates, or any other future one) can be
tested without hand-editing PlantSEED_Biomass.txt or regenerating the
template.

Default --biomass-file is the glucosinolate biomass; pass a different path
to test any other file following the same convention (see
Data/PlantSEED_v3/Biomass/*.txt and biomass_loader.py's docstring).
"""
import argparse

from cobrakbase.core.kbase_object_factory import KBaseObjectFactory

from biomass_loader import load_biomass_into_model


def _build_argparser():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--model", default="test_arabidopsis_model.json",
        help="Path to the FBAModel JSON. Default: %(default)s")
    ap.add_argument("--media", default="PlantAutotrophicMedia.json",
        help="Path to the media JSON. Default: %(default)s")
    ap.add_argument("--biomass-file",
        default="../../../Data/PlantSEED_v3/Biomass/plantseed-glucosinolate-biomass.txt",
        help="Path to the biomass TSV to load into the model's biomass "
             "reaction before optimizing. Default: %(default)s")
    ap.add_argument("--biomass-reaction", default="bio1",
        help="Model biomass reaction id to add compounds to. Default: %(default)s")
    ap.add_argument("--quiet", action="store_true",
        help="Suppress the per-compound added/missing log lines.")
    return ap


def main():
    args = _build_argparser().parse_args()

    KBOF = KBaseObjectFactory()
    model = KBOF.build_object_from_file(args.model, "KBaseFBA.FBAModel")
    media = KBOF.build_object_from_file(args.media, "KBaseBiochem.Media")
    model.medium = media

    load_biomass_into_model(model, args.biomass_file,
                             biomass_reaction_id=args.biomass_reaction,
                             quiet=args.quiet)

    sol = model.optimize()
    print(sol)


if __name__ == "__main__":
    main()
