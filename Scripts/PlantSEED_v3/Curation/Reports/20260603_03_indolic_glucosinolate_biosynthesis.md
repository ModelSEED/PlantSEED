# Indolic glucosinolate biosynthesis — curation review

PlantSEED subsystem (currently): **`Aromatic glucosinolate biosynthesis`** (lumped with phenolic — see Gap 1 below).

Scope: L-tryptophan → first fully formed indolic glucosinolate (**glucobrassicin / indol-3-ylmethyl glucosinolate**, `cpd03467`). Stops at the SOT step. Secondary modifications of glucobrassicin (4-hydroxylation, 4-methoxylation, 1-methoxylation, 1-hydroxylation by CYP81F family + IGMTs) are out of scope and noted only as downstream / excluded.

Sources read:
- `Data/PlantSEED_v3/PlantSEED_Roles.json`
- `Curators/pelle283/Glucosinolates/*` (Aromatic_CYP79AB_Step1.tsv, CYP83AB_Step2.tsv, GSTF_Step3.tsv, GGP_Step4.tsv, SUR1_Step5.tsv, UGT_Step6.tsv, SOT_Step7.tsv, UpdatingReactionsGSL.tsv)
- `Curators/tjcontant/Glucosinolates/gls_enzymes` (rows 8-11 cover the secondary-modification CYP/IGMT enzymes)

## Curated step sequence (tryptophan → glucobrassicin)

| # | Substrate → product | EC | PlantSEED role | Reaction | A. thaliana genes |
|---|---|---|---|---|---|
| 1a | L-Tryptophan (`cpd00065`) + O₂ + NADPH → N-hydroxy-L-tryptophan (`cpd20964`) | 1.14.14.156 | **Tryptophan N-monooxygenase (EC 1.14.14.156)** | rxn16426 | CYP79B2 (AT4G39950), CYP79B3 (AT2G22330) |
| 1b | N-hydroxy-L-tryptophan (`cpd20964`) + O₂ + NADPH → N,N-dihydroxy-L-tryptophan (`cpd20965`) | 1.14.14.156 | same role | rxn16427 | same |
| 1c | N,N-dihydroxy-L-tryptophan (`cpd20965`) → 3-indoleacetaldoxime / IAOx (`cpd01880`) + CO₂ | 1.14.14.156 | same role | rxn16428 | same |
| 2 | 3-indoleacetaldoxime (`cpd01880`) → IAOx N-oxide / indole-3-acetonitrile oxide (`cpd17395` ≡ `cpd23386` by formula) | 1.14.14.45 | **Aromatic aldoxime N-monooxygenase (EC 1.14.14.45)** | rxn14107 | CYP83B1 (AT4G31500); CYP83A1 (AT4G13770) — but see Gap 3 |
| 3 | indole-3-acetonitrile oxide (`cpd23386`) + GSH → indole-3-acetohydroximoyl-glutathione (`cpd23387`) | 2.5.1.18 | **Glutathione S-transferase** | rxn21810 | GSTF11 (AT3G03190), GSTU20 (AT1G78370), GSTF9 (AT2G30860), GSTF10 (AT2G30870), GSTU7 (AT1G27130) |
| 4 | indole-3-acetohydroximoyl-glutathione (`cpd23387`) + H₂O → indole-3-acetohydroximoyl-cysteinylglycine (`cpd23388`) + γ-Glu | 3.4.19.16 | **Glucosinolate gamma-glutamyl hydrolase (EC 3.4.19.16)** | rxn21818 | GGP1 (AT4G30530), GGP2-6 (see report 02) |
| 4b | indole-3-acetohydroximoyl-cysteinylglycine (`cpd23388`) + H₂O → S-(indolylmethylthiohydroximoyl)-L-cysteine (`cpd16334`) + Gly | 3.4.13.23 | (no role) | **MISSING — see Gap 2** | — |
| 5 | S-(indolylmethylthiohydroximoyl)-L-cysteine (`cpd16334`) → indolylmethylthiohydroximate (`cpd16332`) + Pyr + NH₃ | 4.4.1.13 | **Alkylthiohydroximate C-S lyase (EC 4.4.1.13)** | rxn12019 | SUR1 (AT2G20610) |
| 6 | indolylmethylthiohydroximate (`cpd16332`) + UDP-Glc → indolylmethyl-desulfoglucosinolate (`cpd16333`) + UDP | 2.4.1.195 | **N-hydroxythioamide S-beta-glucosyltransferase (EC 2.4.1.195)** | rxn11701 | UGT74B1 (AT1G24100) |
| 7 | indolylmethyl-desulfoglucosinolate (`cpd16333`) + PAPS → **Glucobrassicin (`cpd03467`)** + PAP + H⁺ | 2.8.2.24 / 2.8.2.38 | **Aliphatic desulfoglucosinolate sulfotransferase (EC 2.8.2.38)** *(misclassified — see Gap 4)* | rxn11704 | SOT17 (AT1G18590), SOT18 (AT1G74090) |

**End-point: glucobrassicin** (`cpd03467`) — first fully formed indolic glucosinolate.

## Curation actions still pending (gaps / open items)

1. **No separate "Indolic glucosinolate biosynthesis" subsystem.** PlantSEED currently bundles indolic and phenolic GSL biosynthesis into one `Aromatic glucosinolate biosynthesis` subsystem. The two pathways share only the GST + GGP + (would-share) dipeptidase + C-S lyase + UGT + SOT roles; the entry-point CYPs are completely separate (CYP79B vs CYP79A2, CYP83B1 vs CYP83A1). Splitting into `Indolic glucosinolate biosynthesis` and `Benzenic glucosinolate biosynthesis` would match the MetaCyc PWY-601 / PWY-1187 separation and the historical PlantSEED v1 organisation (`Biosynthesis_of_benzenic_and_indolic_glucosinolates_in_plants_(core_structure_and_secondary_modifications)`, which `ricon001` is REMOVE-ing across his TSVs but no replacement has been ADDed).
2. **Step 4b (cysteinylglycine-S-conjugate dipeptidase) has no indolic reaction.** `pelle283/Glucosinolates/AOP2_StepX` adds the role with one reaction (rxn43940, aliphatic 4MTB track). The indolic substrate `cpd23388` (and the phenolic `cpd23385`) need analogous reactions in MS Biochem and addition to the role. Without this step, GGP's product is a dead-end in the curation — the C-S lyase substrate `cpd16334` has no producer.
3. **CYP83B1 (`AT4G31500`) only catalyses rxn14107 in PlantSEED.** `pelle283/Glucosinolates/CYP83AB_Step2.tsv` correctly assigns `AT4G31500` to the aromatic aldoxime N-monooxygenase role and REMOVE-s the previous (incorrect) gene set `AT5G57220, AT4G37400, AT4G37430` (those are now in a different cytochrome role per `tjcontant/gls_enzymes` row 10 — see Gap 5). The CYP83A1 / `AT4G13770` is also ADDed to this role, reflecting its broader substrate scope (catalyses both phenyl- and indolic-acetaldoxime → aci-nitro). Confirm the dual assignment landed.
4. **Step 7 (SOT for glucobrassicin) is held by the aliphatic role, not the aromatic role.** `rxn11704` (indolylmethyl-desulfo-GSL → glucobrassicin) is assigned to `Aliphatic desulfoglucosinolate sulfotransferase (EC 2.8.2.38)` (gene SOT17/AT1G18590, SOT18/AT1G74090). The `Aromatic desulfoglucosinolate sulfotransferase (EC 2.8.2.24)` role exists in PlantSEED_Roles.json but has `rxns=[]`. `pelle283/SOT_Step7.tsv` proposes the split: keep rxn14133 etc. on the aliphatic role; move rxn11704 + rxn02300 (glucotropeolin) to the aromatic role; remove `AT1G74100` from the aliphatic role and add to the aromatic role. The role definitions are in place; the reaction migration is the remaining edit.
5. **"Cytochrome 9450" placeholder role.** `tjcontant/gls_enzymes` row 8 records a role literally named **"Cytochrome 9450"** (likely a typo for CYP81F4 or a generic cytochrome P450) for rxn45715 (glucobrassicin + flavin → 1-hydroxyglucobrassicin), assigned to AT4G37410. The role is present in PlantSEED_Roles.json under the same imprecise name. Rename to the proper enzyme name (likely `Glucobrassicin 1-hydroxylase` or specific CYP family). This is a secondary-modification enzyme (excluded from "first fully formed" scope), but the literal "Cytochrome 9450" string is a bug.
6. **`pelle283/Aromatic_CYP79AB_Step1.tsv` UPDATE for the EC number.** Proposes renaming `Tryptophan N-monooxygenase (EC 1.14.13.125)` → `Tryptophan N-monooxygenase (EC 1.14.14.156)` (new EC) and same for Phe (EC 1.14.13.124 → 1.14.14.40). The role is already at the new EC in PlantSEED_Roles.json — UPDATE looks applied.
7. **No "Aromatic glucosinolate" GGP or GST sub-role.** GST and GGP roles list both `Aliphatic glucosinolate biosynthesis` and `Aromatic glucosinolate biosynthesis` in their subsystems list (good), but the role names don't indicate which substrate track they belong to — there's a single GST role serving all 8 chain-length tracks. Per `pelle283/GSTF_Step3.tsv` line 1, the proposed UPDATE renames the aromatic-specific role; cross-check whether the rename intent was to split into two roles or to consolidate. Currently consolidated; the GST features list (AT2G30860, AT2G30870, AT3G03190, AT1G27130, AT1G78370) doesn't separate indolic vs aliphatic specificities.

## Compound-identity check

`cpd17395` ("IAOx N-oxide", C10H10N2O2) and `cpd23386` ("indole-3-acetonitrile oxide", C10H10N2O2) have the same molecular formula and are likely the same chemical species under two different ModelSEED IDs (the aci-nitro form of the N-hydroxyimine). The pathway works because rxn14107 produces `cpd17395` and rxn21810 consumes `cpd23386` — but only if downstream reads `cpd17395` as equivalent to `cpd23386`. **The curation as written has a one-compound disconnect.** Either (a) merge the two compounds upstream in MS Biochem, or (b) add a tautomerisation/equivalence reaction. Worth raising with ModelSEED.

## Downstream / explicitly excluded (per request — derivatives of glucobrassicin)

- **CYP81F4 monooxygenase**: rxn23774, glucobrassicin → neoglucobrassicin (`cpd05335`). Excluded.
- **Monooxygenase, 4-hydroxylation of I3M to 4OH-I3M**: rxn23775, glucobrassicin → 4-hydroxyglucobrassicin (`cpd05333`). Excluded.
- **Indole glucosinolate methyltransferase**: rxn23776, rxn48396, rxn42934 — 4OH-I3M → 4-methoxy-I3M and 1OH-I3M → 1-methoxy-I3M conversions. Excluded.
- **"Cytochrome 9450"** (see Gap 5): rxn45715, glucobrassicin → 1-hydroxyglucobrassicin (`cpd32717`). Excluded.

## Cross-reference

- Steps 3 (GST), 4 (GGP), 6 (UGT), 7 (SOT) are shared with the phenolic glucosinolate pathway; see `04_phenolic_glucosinolate_biosynthesis.md` for the parallel reaction set. Step 5 (C-S lyase / SUR1) is also a shared role but uses the indolic-specific reaction rxn12019.
- Step 2 (CYP83B1 / `Aromatic aldoxime N-monooxygenase`) is shared with the phenolic pathway by role, but the role currently only has the indolic reaction (rxn14107) — see Gap 3 in `04_phenolic_glucosinolate_biosynthesis.md`.
