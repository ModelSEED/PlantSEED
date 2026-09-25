# Unblocking the phenolic glucosinolate pathway

Two breaks stopped glucotropeolin carrying flux.

## Step 2 — the CYP83 reaction was unassigned

`rxn21793` is the phenolic counterpart of `rxn21796`, the aliphatic CYP83 reaction
already curated on the (methylsulfanyl)alkanaldoxime role. Same form, same NADPH
cofactors, same CI:-1 status — and CI:-1 does not prevent template inclusion
(`rxn14107`, the curated indolic reaction, carries it too).

It is assigned to `Aromatic aldoxime N-monooxygenase (EC 1.14.14.45)`, which
already holds CYP83A1 (`AT4G13770`) and CYP83B1 (`AT4G31500`) and the indolic
reaction `rxn14107`.

### The stereoisomer swap

`rxn21793` as deposited consumes `cpd14796`, the **(Z)** aldoxime. The curated
CYP79A2 reaction `rxn16425` produces `cpd20962`, the **(E)** aldoxime. Nothing in
PlantSEED converts one to the other, so the chain would stop at step 1c.

The swap repoints `rxn21793` onto the (E) isomer. This is sound rather than a
fudge, because the stereocentre does not survive the step: the product
`cpd23383` (2-phenylacetonitrile oxide) is achiral — InChIKey
XAWCLWKTUKMCMO-**UHFFFAOYSA**-N, no stereo markers in its SMILES. The aldoxime
C=N becomes a nitrile oxide C#N+-O-, destroying the E/Z distinction. The (Z)
designation reappears downstream at `cpd23384` only because glutathione
conjugation reforms the C=N with a defined geometry; it is not inherited from the
substrate.

`rxn53279` is the alternative: it consumes the (E) isomer directly and needs no
swap, but its generic `[NADPH--hemoprotein reductase]` pair has no formula
(CPDFORMERROR) and would need two cofactor substitutions instead of one substrate
substitution. `rxn21793` is the cheaper and better-founded route.

### Why the rows are reaction-scoped

The 7th column restricts the swap to `rxn21793`. The complex also catalyses the
indolic `rxn14107`; an enzyme-wide override would inject the phenylalanine-derived
aldoxime into the tryptophan branch.

Note the complex is addressed by its `abstract_enzyme`, "Oxime metabolizining
monooxygenase in Trp, Phe, Tyr-derived glucosinolates biosynthesis", not by the
role name — complexes are keyed on abstract_enzyme.

## Step 4b — the dipeptidase reaction was unassigned

`rxn42261`, balanced and status OK, is the phenolic counterpart of the six
aliphatic and one indolic dipeptidase reactions on this role. The role still has
NO gene: EC 3.4.13.23 is unidentified in Arabidopsis.

## No isomerase

An earlier attempt added `rxn39977` (E/Z interconversion) as a new role. That was
solving a break created by choosing `rxn21793` without repointing its substrate.
It has been backed out and should not be reintroduced.
