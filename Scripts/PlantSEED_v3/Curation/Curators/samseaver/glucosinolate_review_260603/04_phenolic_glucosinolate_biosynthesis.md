# Phenolic (benzylic) glucosinolate biosynthesis — curation review

PlantSEED subsystem (currently): **`Aromatic glucosinolate biosynthesis`** (lumped with indolic — see Gap 1 in `03_indolic_glucosinolate_biosynthesis.md`).

Scope: L-phenylalanine → first fully formed phenolic glucosinolate (**glucotropeolin / benzyl glucosinolate**, `cpd01457`). Stops at the SOT step. The (also-aromatic) tyrosine-derived branch is not curated in PlantSEED at all and is noted only as out-of-scope.

Sources read:
- `Data/PlantSEED_v3/PlantSEED_Roles.json`
- `Curators/pelle283/Glucosinolates/*` (Aromatic_CYP79AB_Step1.tsv, CYP83AB_Step2.tsv, GSTF_Step3.tsv, GGP_Step4.tsv, SUR1_Step5.tsv, UGT_Step6.tsv, SOT_Step7.tsv, UpdatingReactionsGSL.tsv, NewStep_Spontaneous)

## Curated step sequence (phenylalanine → glucotropeolin)

| # | Substrate → product | EC | PlantSEED role | Reaction | A. thaliana genes |
|---|---|---|---|---|---|
| 1a | L-Phenylalanine (`cpd00066`) + O₂ + NADPH → N-hydroxy-L-phenylalanine (`cpd20960`) | 1.14.14.40 | **Phenylalanine N-monooxygenase (EC 1.14.14.40)** | rxn16423 | CYP79A2 (AT5G05260) |
| 1b | N-hydroxy-L-phenylalanine (`cpd20960`) + O₂ + NADPH → N,N-dihydroxy-L-phenylalanine (`cpd20963`) | 1.14.14.40 | same role | rxn16424 | same |
| 1c | N,N-dihydroxy-L-phenylalanine (`cpd20963`) → (E)-phenylacetaldoxime (`cpd20962` ≡ `cpd14796`) + CO₂ | 1.14.14.40 | same role | rxn16425 | same |
| 1d *(spontaneous, listed under aliphatic subsystem — see Gap 4)* | N-benzylformamide (`cpd11229`) → (Z)-phenylacetaldehyde oxime (`cpd14796`) | — | **Spontaneous Reaction** | rxn22371 | (none) |
| 2 | (E)-phenylacetaldoxime → 2-phenylacetonitrile oxide (`cpd23383`) | 1.14.14.45 | **Aromatic aldoxime N-monooxygenase (EC 1.14.14.45)** | **MISSING — see Gap 2** | CYP83A1 (AT4G13770), CYP83B1 (AT4G31500) |
| 3 | 2-phenylacetonitrile oxide (`cpd23383`) + GSH → S-[(Z)-phenylacetohydroximoyl]-L-glutathione (`cpd23384`) | 2.5.1.18 | **Glutathione S-transferase** | rxn21809 | GSTF11 (AT3G03190), GSTU20 (AT1G78370), GSTF9/F10/U7 (AT2G30860, AT2G30870, AT1G27130) |
| 4 | S-phenylacetohydroximoyl-glutathione (`cpd23384`) + H₂O → N-[S-phenylacetohydroximoyl-L-cysteinyl]glycine (`cpd23385`) + γ-Glu | 3.4.19.16 | **Glucosinolate gamma-glutamyl hydrolase (EC 3.4.19.16)** | rxn21817 | GGP1 (AT4G30530), GGP2-6 (see report 02) |
| 4b | phenyl-Cys-Gly conjugate (`cpd23385`) + H₂O → S-(phenylacetothiohydroximoyl)-L-cysteine (`cpd17427`) + Gly | 3.4.13.23 | (no role) | **MISSING — see Gap 3** | — |
| 5 | S-(phenylacetothiohydroximoyl)-L-cysteine (`cpd17427`) → phenylthioacetohydroximate (`cpd02332`) + Pyr + NH₃ | 4.4.1.13 | **Alkylthiohydroximate C-S lyase (EC 4.4.1.13)** | rxn14068 | SUR1 (AT2G20610) |
| 6 | phenylthioacetohydroximate (`cpd02332`) + UDP-Glc → desulfoglucotropeolin (`cpd00787`) + UDP | 2.4.1.195 | **N-hydroxythioamide S-beta-glucosyltransferase (EC 2.4.1.195)** | rxn02299 | UGT74B1 (AT1G24100) |
| 7 | desulfoglucotropeolin (`cpd00787`) + PAPS → **Glucotropeolin (`cpd01457`)** + PAP + H⁺ | 2.8.2.24 / 2.8.2.38 | **Aliphatic desulfoglucosinolate sulfotransferase (EC 2.8.2.38)** *(misclassified — see Gap 5)* | rxn02300 | SOT17 (AT1G18590), SOT18 (AT1G74090) |

**End-point: glucotropeolin** (`cpd01457`) — first fully formed phenolic glucosinolate.

## Curation actions still pending (gaps / open items)

1. **No separate "Benzenic glucosinolate biosynthesis" subsystem.** See Gap 1 in `03_indolic_glucosinolate_biosynthesis.md` — currently lumped with indolic. Splitting matches MetaCyc PWY-1187 / PWY-601 organisation.
2. **Step 2 has no reaction in PlantSEED.** `Aromatic aldoxime N-monooxygenase (EC 1.14.14.45)` carries only `rxn14107` (the indolic IAOx → IAOx-N-oxide reaction). The phenolic equivalent — `cpd20962`/`cpd14796` (phenylacetaldoxime) → `cpd23383` (2-phenylacetonitrile oxide) — is not in the role's reactions list. Either (a) find or create a ModelSEED reaction for that conversion and ADD it to the role, or (b) confirm that `cpd20962` ≡ `cpd23383` chemically (formula C8H9NO vs C8H9NO2 — they are NOT the same, so a real reaction is needed). Without this step the pathway is broken at the entry to the GST step.
3. **Step 4b (cysteinylglycine-S-conjugate dipeptidase) has no phenolic reaction.** `cpd23385` (phenyl-Cys-Gly conjugate) → `cpd17427` (phenyl-Cys conjugate) needs a ModelSEED reaction and addition to the role. Same gap as for indolic — see Gap 2 in `03_indolic_glucosinolate_biosynthesis.md`. Without this step, GGP's product is a dead-end.
4. **Spontaneous reaction (rxn22371) mis-classified.** Sits under `Aliphatic glucosinolate biosynthesis` subsystem but involves phenylacetaldoxime — a phenolic intermediate. Move to the (proposed) `Benzenic glucosinolate biosynthesis` subsystem. Also: `rxn22371` flows the "wrong way" (N-benzylformamide → phenylacetaldoxime) — verify whether this is a side-reaction recovering the oxime from a degradation product, or whether the directionality needs flipping for inclusion in the forward pathway.
5. **Step 7 (SOT for glucotropeolin) is held by the aliphatic role, not the aromatic role.** `rxn02300` (desulfoglucotropeolin → glucotropeolin) is in `Aliphatic desulfoglucosinolate sulfotransferase (EC 2.8.2.38)`. The `Aromatic desulfoglucosinolate sulfotransferase (EC 2.8.2.24)` role exists with `rxns=[]`. `pelle283/SOT_Step7.tsv` proposes moving rxn02300 + rxn11704 to the new role and reassigning AT1G74100. Same gap as Gap 4 in `03_indolic_glucosinolate_biosynthesis.md`.
6. **CYP83A1 (`AT4G13770`) dual-assignment.** `pelle283/CYP83AB_Step2.tsv` line 6 ADDs `AT4G13770` to the aromatic aldoxime N-monooxygenase role — but `AT4G13770` is also the gene for the *aliphatic* role `(Methylsulfanyl)alkanaldoxime N-monooxygenase (EC 1.14.14.43)` (per line 2 of the same file). Confirm whether CYP83A1's documented broad substrate scope (aliphatic + phenolic + indolic aldoximes) justifies the dual assignment, or whether the aromatic-role assignment should be conditional on substrate availability. Likely correct as dual — but worth noting.
7. **Tyrosine-derived (4-hydroxybenzyl / sinalbin) branch is absent.** PlantSEED has no roles or reactions for L-tyrosine → p-hydroxyphenylacetaldoxime → sinalbin / glucosinalbin. Out of scope for this review but worth flagging if "phenolic glucosinolate" is interpreted broadly (some authors group tyrosine-derived sinalbin under "phenolic" rather than its own "p-hydroxybenzylic" category).

## Compound-identity check

`cpd20962` ("(E)-Phenylacetaldoxime", C8H9NO) and `cpd14796` ("(Z)-Phenylacetaldehyde oxime", C8H9NO) are E/Z stereoisomers of the same molecule, with separate ModelSEED IDs. The CYP79A2 product (rxn16425) is `cpd20962` (E); the spontaneous reaction (rxn22371, see Gap 4) involves `cpd14796` (Z). If the downstream CYP83 reaction (when added — see Gap 2) consumes one isomer specifically, the pathway will only carry flux for that isomer. Worth recording whether an E/Z interconversion is biologically relevant or if these should be merged in MS Biochem.

## Downstream / explicitly excluded

Phenolic glucosinolate secondary modifications (e.g. hydroxybenzyl variants, benzoyloxy derivatives) are not curated in PlantSEED as a distinct cluster — the `Benzoylated glucosinolates modification, unresolved step` role (rxn21838, rxn21837, rxn23787) is currently grouped under aliphatic and concerns aliphatic GSL benzoylation rather than the benzylic GSL pathway. Excluded.

## Cross-reference

- Steps 3 (GST), 4 (GGP), 6 (UGT), 7 (SOT) are shared by role with the indolic glucosinolate pathway; see `03_indolic_glucosinolate_biosynthesis.md` for the parallel reaction set.
- Step 2 (CYP83 / `Aromatic aldoxime N-monooxygenase`) is the most prominent gap in this report — see Gap 2 above. The same role currently covers only the indolic substrate.
- Step 5 (C-S lyase / SUR1) is a shared role; the phenolic-specific reaction is rxn14068 (vs rxn12019 indolic, rxn24582 aliphatic 4MTB).
