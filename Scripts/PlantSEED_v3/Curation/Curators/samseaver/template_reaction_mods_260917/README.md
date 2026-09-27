# Thylakoid proton pumps — migrated out of the template generator

`proton_pumps.tsv` replaces two hardcoded blocks that lived at the bottom of
`Scripts/PlantSEED_v3/Template/Generate_Core_ModelTemplate.py`. Their comment read:

> Rather than trying to find or create a new reaction in the biochemistry
> I'm modifying the reactions here in the template generation

which is exactly right — the proton translocation is real chemistry that the
ModelSEED reaction does not carry. The modification was correct; only its
location was a problem, because a curator could not see it or change it.

## What the rows mean

Photosystem II (`rxn20632`) takes 4 H+ from the stroma (`d`) and releases 4 into
the thylakoid lumen (`y`). Cytochrome b6-f (`rxn20595`) already carries protons
in `d`, so its coefficient is reset to -2, and 4 are released into `y` — two
pumped plus two from plastoquinol oxidation.

Both are expressed as `compound@compartment` keys, which is why the same
compound appears twice for one enzyme:

    "stoichiometry": {"cpd00067@d": "-4", "cpd00067@y": "4"}

A single-key-per-compound form could not represent a pump at all.

## Equivalence

The generated template is byte-identical before and after the migration; the
hardcoded blocks were deleted in the same commit that added this file.
