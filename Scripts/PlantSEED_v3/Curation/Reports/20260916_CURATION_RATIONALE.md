# Glucosinolate expansion — rationale for the applied TSVs

Companion to `pelletier_feedback_260915.md`. The TSVs themselves are bare actions;
the reasoning lives here.

## `GS_OX_ChainLength_260915.tsv`

Only the C3 S-oxygenation was curated, so five measured methylsulfinylalkyl
glucosinolates were absent from the reconstruction. All five reactions already
existed in ModelSEED with the same NADPH+O2 signature as `rxn41751`:

| reaction | product |
|---|---|
| `rxn45613` | glucoraphanin |
| `rxn46901` | glucoalyssin |
| `rxn41495` | glucohesperin |
| `rxn42226` | glucoibarin |
| `rxn44557` | glucohirsutin |

GS-OX5 (`AT1G12140`) is split into its own C8-only role because PlantSEED assigns
genes per role, and Sam requires it off the short chains. Li 2008 (PMID 18799661):
GS-OX2/3/4 act "independent of chain length", GS-OX5 is specific to
8-methylthiooctyl GSL. The two roles are isozymes on C8, which is correct.

## `Aliphatic_CS_Lyase_Dipeptidase_260916.tsv`

Five of six aliphatic tracks were broken between the GGP and UGT steps, so no
methylthioalkyl glucosinolate could be made and everything downstream — including
the S-oxygenation above — was unreachable. The missing reactions all existed,
balanced and unassigned. No new biochemistry.

Verified chains, dipeptidase → C-S lyase → UGT → SOT:

```
rxn41037 -> rxn27041 -> rxn37539 -> rxn14362  => glucoerucin
rxn46896 -> rxn27042 -> rxn37540 -> rxn27056  => glucoberteroin
rxn44540 -> rxn27043 -> rxn37541 -> rxn27057  => glucolesquerellin
rxn47990 -> rxn27044 -> rxn37542 -> rxn27058  => 7-methylthioheptyl GSL
rxn47415 -> rxn27045 -> rxn37543 -> rxn27059  => 8-methylthiooctyl GSL
```

No gene work needed: Mikkelsen 2004 (PMID 14996218) shows SUR1 is a single gene
family and not redundant, so `AT2G20610` covers every chain length.

The dipeptidase role gains its missing chain lengths but stays **gene-less** —
EC 3.4.13.23 is unidentified in Arabidopsis. Research gap, not curation.

### Duplicates deliberately avoided

Two reactions would also have closed steps but reference duplicate compounds the
reconstruction does not use. Both reported separately for obsolescence.

- `rxn27046` uses `cpd28293` "UDP-GLUCOSE" — stereo-undefined duplicate of
  `cpd00026`: same InChIKey skeleton, undefined anomeric centre, and mass 566.0
  against a formula computing to 564.3. The reconstruction uses `cpd00026` in 22
  reactions, `cpd28293` in none. Used `rxn37539` instead.
- `rxn14339` uses `cpd17432` — exact duplicate of `cpd24789`, identical InChIKey
  `RHJXZAWQBJGJJP-FQUWQITNSA-N` and SMILES, null mass. Used `rxn24582` instead.

## `SCPL17_Acylation_260916.tsv`

Both acylation roles had zero genes, so their reactions could not link a
metabolite to any transcript. Lee 2012 (PMID 22762247) eliminates the
alternatives — `scpl5` is wild-type, `sng2` acts indirectly — and finds scpl17
loses both product classes while accumulating precursors.

**Evidence class: reverse genetics, no in vitro assay.** Accepted by Sam
2026-09-16. Revisit if the enzymology lands.

BZO1 (`AT1G65880`) deliberately not added: characterised, but the same paper
reassigns its in vivo role upstream of this step. It belongs in phenylpropanoid
metabolism if wanted.

Both roles renamed from "... unresolved step", which encoded the unknown gene into
the name. That phrasing is used by only these two roles out of 935. New names
follow the local pattern with the explicit `(no EC)` marker used by 10 other
roles; confirmed these reactions carry no EC in their ModelSEED aliases.
`kbase_id` changes on both; no complex file references them by name.

## Not addressed

**Aliphatic myrosinase.** Needed for exactly one measured compound —
6-(methylthio)hexyl isothiocyanate (ICC leaf 0.183), the only breakdown product
among the 21. Blocked upstream: the compound does not exist in ModelSEED, and
glucolesquerellin has no hydrolysis reaction. TGG1 `AT5G26000` / TGG2 `AT5G25980`
are approved by Sam but cannot be assigned to anything yet.

**Gluconasturtiin.** Research gap — the aldoxime-forming enzyme for
homophenylalanine is unidentified in Arabidopsis.

**Phenolic glucosinolates are blocked at the CYP83 step (rxn53279).** Confirmed by
FBA 2026-09-17: L-phenylalanine reaches (E)-phenylacetaldoxime (`cpd20962`) at flux
224, and everything from step 2 onward is zero, through to glucotropeolin. This is
Gap 2 of `Curators/samseaver/glucosinolate_review_260603/04_phenolic_glucosinolate_biosynthesis.md`,
now confirmed from the model side.

`rxn53279` — (E)-phenylacetaldoxime + O2 + reduced [NADPH--hemoprotein reductase]
-> 2-phenylacetonitrile oxide — is the reaction, and it is on no role. The
`Aromatic aldoxime N-monooxygenase (EC 1.14.14.45)` role carries CYP83A1
(`AT4G13770`) and CYP83B1 (`AT4G31500`) but only the *indolic* reaction
(`rxn14107`). So the gene is curated and the reaction is not.

It cannot simply be assigned. All four routes to `cpd23383` fail the balance check:

| reaction | status | substrate |
|---|---|---|
| `rxn53279` | CPDFORMERROR | (E)-phenylacetaldoxime `cpd20962` |
| `rxn21793` | CI:-1 | (Z)-phenylacetaldehyde oxime `cpd14796` |
| `rxn21794` | CI:-1 | (Z)-phenylacetaldehyde oxime `cpd14796` |
| `rxn42286` | CI:-2 | N-benzylformamide + reduced flavin |

`CPDFORMERROR` is the generic `[NADPH--hemoprotein reductase]` pair having no usable
formula; `CI:-n` is a charge imbalance. And the E/Z split matters: `rxn53279` takes
the (E) isomer that CYP79A2 actually makes, while the charge-imbalanced alternatives
take the (Z) form, so picking one of those would strand the pathway on the wrong
isomer.

**Historical note.** `Generate_Core_ModelTemplate.py` used to carry a hardcoded block
swapping the generic hemoprotein pair (`cpd42231`/`cpd42232`) for flavins
(`cpd21035`/`cpd11630`) on `rxn53279` — an attempt to make it balance. Since the
reaction reaches no template, the block never executed. It was removed on
2026-09-17 when the other template modifications were migrated to curator TSVs;
deliberately NOT migrated, because a TSV row would sit inert and imply the step was
handled. Fixing this needs the reaction repaired upstream in ModelSEEDDatabase, not
a PlantSEED-side override.

**Step 4b is a second, downstream break.** `rxn42261` (phenolic) and `rxn41115`
(indolic) are the unassigned cysteinylglycine-S-conjugate dipeptidase reactions.
Both are balanced and could be assigned today, but doing so alone unblocks nothing:
verified by FBA, adding both leaves every indolic and phenolic target at zero.
