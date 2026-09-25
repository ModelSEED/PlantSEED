# Unblocking the indolic glucosinolate pathway

Two defects stopped glucobrassicin carrying any flux. Both are addressed here.

## 1. Step 4b was unassigned

`rxn41115` — indole-3-acetohydroximoyl-cysteinylglycine + H2O -> S-(indolylmethyl-
thiohydroximoyl)-L-cysteine + glycine — is balanced (status OK) and existed in
ModelSEED, but sat on no role. It is the indolic counterpart of the six aliphatic
dipeptidase reactions already on this role.

The role still has NO gene: EC 3.4.13.23 is unidentified in Arabidopsis. The
reaction carries flux but contributes no GPR. That is a known and accepted hole.

## 2. Step 2 and step 3 use different IDs for the same molecule

    step 2  rxn14107 (CYP83B1)  produces  cpd17395  "IAOx N-oxide"
    step 3  rxn21810 (GST)      consumes  cpd23386  "indole-3-acetonitrile oxide"

Identical InChIKey, WPXDYLYFORNDRP-UHFFFAOYSA-N — stereo and charge layers
included. One compound entered into ModelSEED twice, so the pathway crosses from
one ID to the other and stops.

The real fix is a merge upstream in ModelSEEDDatabase. In anticipation of that,
`rxn21810` is repointed here: `cpd23386` removed, `cpd17395` added at the same
coefficient. When the merge lands these two rows become redundant and should be
deleted.

### Why these rows are reaction-scoped

The 7th column restricts the override to `rxn21810`. The `Glutathione
S-transferase` complex catalyses eight branch-specific reactions — one phenolic,
one indolic, six aliphatic chain lengths — all sharing a single role. An
enzyme-wide override was tested and added `cpd17395` to all eight, leaving the
aliphatic C4 reaction carrying both its own substrate and the indolic one. Scoping
is required here; it is not the default and should not be used where an enzyme's
reactions genuinely share the modification.
