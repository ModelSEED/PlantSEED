"""Load a PlantSEED biomass TSV (PlantSEED_Biomass.txt convention) into an
already-built cobrakbase FBAModel, adding each listed compound to an
existing biomass reaction as an extra reagent.

Convention (same six tab-separated columns as Data/PlantSEED_v3/Biomass/*.txt):

    <class>|<subclass>	<cpd_id>	<compartment letter>	<coefficient>	<name>	<class>

Only columns 2-4 (compound, compartment, coefficient) are used to build the
reagent; columns 1, 5 and 6 are documentation. Lines that are blank, start
with '#', or start with a space are skipped, matching
Add_ModelTemplate_Biomass.py's own parser.

This is deliberately generic: it does not know anything about glucosinolates
specifically, and works for any biomass file following the convention --
PlantSEED_Biomass.txt itself, Extended_Maize_Leaf_Biomass.txt,
plantseed-glucosinolate-biomass.txt, or a future one.

Coefficient sign convention matches PlantSEED_Biomass.txt and
Add_ModelTemplate_Biomass.py: a positive value in the file is a biomass
PRECURSOR (consumed), so it is negated here, same as that script does
(`coefficient = 0.0-float(array[3])`). A compound appearing more than once in
the file (as PlantSEED_Biomass.txt does, e.g. PPi) has its coefficients
summed, also matching that script.
"""

import os


def parse_biomass_file(path):
    """Parse a biomass TSV into {(cpd_id, compartment_letter): coefficient}.

    Coefficients for repeated (cpd_id, compartment) pairs are summed. The
    sign is flipped from the file's convention (positive = consumed) to the
    cobra convention (negative = consumed), matching
    Add_ModelTemplate_Biomass.py exactly.
    """
    coefficients = {}
    with open(path) as fh:
        for raw in fh:
            line = raw.rstrip("\r\n")
            if line == "" or line[0] in (" ", "#"):
                continue
            array = line.split("\t")
            if len(array) < 4:
                continue
            cpd_id = array[1]
            cpt = array[2]
            coefficient = 0.0 - float(array[3])
            key = (cpd_id, cpt)
            coefficients[key] = coefficients.get(key, 0.0) + coefficient
    return coefficients


def load_biomass_into_model(model, biomass_path, biomass_reaction_id="bio1",
                             compartment_index="0", quiet=False):
    """Add every compound in `biomass_path` to `model`'s biomass reaction as
    an extra reagent, using the model's existing stoichiometry convention
    (<cpd_id>_<compartment letter><compartment_index>).

    Mutates `model` in place and returns it. Raises KeyError (via cobra) if a
    listed compound/compartment is not present in the model -- the compound
    has to actually be producible in the network for this to mean anything,
    which is the point of running this after the pathway-connectivity check,
    not instead of it.

    `compartment_index` matches the single-model-instance convention used
    throughout this pipeline (cpd01457_c -> cpd01457_c0); override only if a
    model uses a different compartment indexing scheme.
    """
    if biomass_reaction_id not in model.reactions:
        raise ValueError(f"No reaction '{biomass_reaction_id}' in model -- "
                          f"is this the right model / biomass id?")
    biomass_rxn = model.reactions.get_by_id(biomass_reaction_id)

    coefficients = parse_biomass_file(biomass_path)
    added, missing = [], []
    reagents = {}
    for (cpd_id, cpt), coefficient in coefficients.items():
        met_id = f"{cpd_id}_{cpt}{compartment_index}"
        if met_id not in model.metabolites:
            missing.append(met_id)
            continue
        met = model.metabolites.get_by_id(met_id)
        reagents[met] = coefficient
        added.append(met_id)

    if missing and not quiet:
        print(f"WARNING: {len(missing)} compound(s) from {os.path.basename(biomass_path)} "
              f"not found in model, skipped: {', '.join(missing)}")

    biomass_rxn.add_metabolites(reagents, combine=True)

    if not quiet:
        print(f"Added {len(added)} compound(s) from {os.path.basename(biomass_path)} "
              f"to {biomass_reaction_id}: {', '.join(added)}")

    return model
