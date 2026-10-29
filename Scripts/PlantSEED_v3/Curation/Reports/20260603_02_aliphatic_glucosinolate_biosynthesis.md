# Aliphatic glucosinolate biosynthesis — curation review

PlantSEED subsystem: **`Aliphatic glucosinolate biosynthesis`**

Scope: homomethionine (and its chain-elongated homologues di- through hexahomomethionine) → first fully formed aliphatic glucosinolate. The "first fully formed glucosinolate" is the desulfo-glucosinolate-O-sulfate product of the SOT step — for the C6 (homomethionine) branch that is **glucoiberverin** (`cpd05324`, 3-methylthiopropyl glucosinolate) coming from dihomomethionine, or **glucoerucin** (`cpd05321`, 4-methylthiobutyl glucosinolate) coming from trihomomethionine, etc. Secondary modifications (S-oxygenation, AOP cleavage, hydroxylation, benzoylation, sinapoylation) are out of scope and noted only as "downstream / excluded".

Sources read:
- `Data/PlantSEED_v3/PlantSEED_Roles.json`
- `Curators/pelle283/Glucosinolates/*` (Aliphatic_CYP79F_Step1.tsv, CYP83AB_Step2.tsv, GSTF_Step3.tsv, GGP_Step4.tsv, SUR1_Step5.tsv, UGT_Step6.tsv, SOT_Step7.tsv, UpdatingReactionsGSL.tsv, AOP2_StepX, GS_OX_StepX.tsv, NewStep_Spontaneous)
- Generic-cofactor edits in `samseaver/template_reaction_curation_260602/glucosinolate_chemistry.tsv` (monooxygenase block 4)

## Curated step sequence (homomethionine → first aliphatic glucosinolate)

The pathway has seven enzymatic steps. Each is repeated for every chain-length amino-acid substrate (homo → hexahomomethionine) — six parallel substrate tracks share the same seven roles.

| # | Substrate → product (homomethionine track shown) | EC | PlantSEED role | Reaction (homomet track) | A. thaliana genes |
|---|---|---|---|---|---|
| 1 | L-Homomethionine (`cpd17403`) → 4-methylthiobutanaldoxime (`cpd17431`) + CO₂ | 1.14.14.42 | **Homomethionine N-monooxygenase (EC 1.14.14.42)** | rxn13984 | CYP79F1 (AT1G16410); + CYP79F2 (AT1G16400) on long-chain track only |
| 2 | 4-methylthiobutanaldoxime (`cpd17431`) → 4-methylthiobutanonitrile oxide / aci-nitro (`cpd23389`) | 1.14.14.43 | **(Methylsulfanyl)alkanaldoxime N-monooxygenase (EC 1.14.14.43)** | rxn21796 | CYP83A1 (AT4G13770) |
| 3 | 4-methylthiobutanonitrile oxide (`cpd23389`) + GSH → 4-methylthiobutylhydroximoyl-glutathione (`cpd23390`) | 2.5.1.18 (GST family) | **Glutathione S-transferase** | rxn21811 | GSTF11 (AT3G03190), GSTU20 (AT1G78370), others (AT2G30860, AT2G30870, AT1G27130) |
| 4 | 4-methylthiobutylhydroximoyl-glutathione (`cpd23390`) + H₂O → 4-methylthiobutylhydroximoyl-cysteinylglycine (`cpd23391`) + γ-Glu | 3.4.19.16 | **Glucosinolate gamma-glutamyl hydrolase (EC 3.4.19.16)** | rxn21819 | GGP1 (AT4G30530), GGP3 (AT4G30550), GGP4 (AT4G30540), GGP5 (AT2G23960), GGP6 (AT2G23970), GGP2 (AT4G29210) |
| 4b | 4-methylthiobutylhydroximoyl-cysteinylglycine (`cpd23391`) + H₂O → 4-methylthiobutylhydroximoyl-cysteine (`cpd24789`) + Gly | 3.4.13.23 | **cysteinylglycine-S-conjugate dipeptidase (EC 3.4.13.23)** | rxn43940 | *no curated gene* (role marked NEW, no features) |
| 5 | 4-methylthiobutylhydroximoyl-cysteine (`cpd24789`) → 4-methylthiobutylthiohydroximate (`cpd17433`) + Pyr + NH₃ | 4.4.1.13 | **Alkylthiohydroximate C-S lyase (EC 4.4.1.13)** | rxn24582 | SUR1 (AT2G20610) |
| 6 | 4-methylthiobutylthiohydroximate (`cpd17433`) + UDP-Glc → 4-methylthiobutyl-desulfoglucosinolate (`cpd17434`) + UDP | 2.4.1.195 | **N-hydroxythioamide S-beta-glucosyltransferase (EC 2.4.1.195)** | rxn14074 | UGT74B1 (AT1G24100) |
| 7 | 4-methylthiobutyl-desulfoglucosinolate (`cpd17434`) + PAPS → **Glucoerucin (`cpd05321`)** + PAP + H⁺ | 2.8.2.38 | **Aliphatic desulfoglucosinolate sulfotransferase (EC 2.8.2.38)** | rxn14362 | SOT17 (AT1G18590), SOT18 (AT1G74090) |

**End-point: glucoerucin** (`cpd05321`) for the trihomomethionine (5C side-chain) track — the first fully formed aliphatic glucosinolate from this substrate. (Note: the homomethionine→Cn track that ends in glucoiberverin uses rxn14133.)

## Reaction coverage per chain-length track

The same seven roles cover six parallel tracks. Reactions per track:

| Track (start) | Step 1 (CYP79F) | Step 2 (CYP83A1) | Step 3 (GST) | Step 4 (GGP) | Step 5 (C-S lyase) | Step 6 (UGT) | Step 7 (SOT) → product |
|---|---|---|---|---|---|---|---|
| Homomethionine (`cpd17403`)→3MTP | rxn13984 | rxn21796 | rxn21811 | rxn21819 | **gap** | rxn14074 → cpd17434 | rxn14133 → **Glucoiberverin** (`cpd05324`) |
| Dihomomethionine (`cpd17407`)→4MTB | rxn13986 | rxn21798 | rxn21812 | rxn21820 | rxn24582 | (gap → cpd17437) | rxn14362 → **Glucoerucin** (`cpd05321`) |
| Trihomomethionine (`cpd17411`)→5MTP | rxn14285 | rxn21800 | rxn21813 | rxn21821 | **gap** | rxn37539 → cpd17437 †mislabel | rxn27056 → **Glucoberteroin** (`cpd05313`) |
| Tetrahomomethionine (`cpd17415`)→6MTH | rxn14305 | rxn21802 | rxn21814 | rxn21822 | **gap** | rxn37540 → cpd26624 | rxn27057 → **Glucolesquerellin** (`cpd17439`) |
| Pentahomomethionine (`cpd17419`)→7MTHp | rxn14237 | rxn21804 | rxn21815 | rxn21823 | **gap** | rxn37541 → cpd26641 | rxn27058 → **7-MTHp glucosinolate** (`cpd17441`) |
| Hexahomomethionine (`cpd17423`)→8MTO | rxn14161 | rxn21806 | rxn21816 | rxn21824 | **gap** | rxn37542 → cpd26642 | rxn27059 → **8-MTO glucosinolate** (`cpd17443`) |
| (+1 more UGT) | — | — | — | — | — | rxn37543 → cpd26643 | — |

The substrate naming on rxn37539 (UGT step, trihomomethionine track) appears mismatched: ModelSEED labels the substrate `cpd26636` as "5-methylthiopentylhydroximate" (C6, correct for trihomomethionine) but the product `cpd17437` is labelled "4-Methylthiobutyl-desulfoglucosinolate" (C5, wrong by one carbon). The downstream SOT (rxn27056) treats `cpd17437` as the C6-glucosinolate-precursor, so the wiring works but the compound name in MS Biochem is one chain length off. Worth flagging upstream to ModelSEED.

## Curation actions still pending (gaps / open items)

1. **Step 4b (cysteinylglycine-S-conjugate dipeptidase, EC 3.4.13.23) covers only the homomethionine (C5 side-chain) track.** `cysteinylglycine-S-conjugate dipeptidase` role has a single reaction `rxn43940` (substrate `cpd23391`, the 4-methylthiobutyl conjugate). The other five chain-length tracks (cpd23394, cpd23397, cpd23400, cpd23403, cpd23406) have no curated dipeptidase reaction connecting GGP product → C-S lyase substrate. The role exists (NEW, no features yet) — needs (a) reaction additions for the other five tracks, (b) Arabidopsis gene assignments (LCS1/LCS2 candidates per literature).
2. **Step 5 (Alkylthiohydroximate C-S lyase, EC 4.4.1.13) covers only 3 of 8 substrate tracks.** SUR1 has rxn24582 (4MTB-cysteine track, aliphatic), rxn14068 (phenylacetothio track, phenolic), rxn12019 (indolylmethyl track, indolic). The five longer-chain aliphatic substrate-to-product pairs need new reactions in MS Biochem and additions to the role.
3. **Step 7 (Aliphatic SOT) holds two phenolic/indolic reactions.** `rxn02300` (desulfoglucotropeolin → glucotropeolin, benzylic / phenolic) and `rxn11704` (indolylmethyl-desulfo-GSL → glucobrassicin, indolic) are currently in the aliphatic SOT role. PlantSEED already has a separate `Aromatic desulfoglucosinolate sulfotransferase (EC 2.8.2.24)` role — but it has `rxns=[]`. `pelle283/Glucosinolates/SOT_Step7.tsv` proposes the move: remove `Athaliana_TAIR10||AT1G74100` from the aliphatic role, create the aromatic role with that gene. The role definitions are partly in place; the reaction move is the remaining edit.
4. **CYP79F2 (`AT1G16400`) is curated only for the long-chain (10C-11C) sub-role.** `pelle283/Aliphatic_CYP79F_Step1.tsv` adds `AT1G16400` to the sub-role "Homomethionine N-monooxygenase, 10C-11C only" with reactions rxn14237 + rxn14161. The role exists; confirm whether the renaming UPDATE proposal (`Penta and hexahomomethionine N-hydroxylase (EC 1.14.13.n6)` → `Homomethionine N-monooxygenase, 10C-11C only (EC 1.14.14.42)`) has been applied to PlantSEED_Roles.json (the role appears under the new name — looks applied).
5. **CYP83A1 generic-hemoprotein edit not yet applied.** `samseaver/template_reaction_curation_260602/glucosinolate_chemistry.tsv` block 4 wants `cpd42231` → `cpd21035` (FADH2) and `cpd42232` → `cpd11630` (FAD) on rxn53279. **However rxn53279 is not in any aliphatic CYP83A1 reaction list above** — the role's six reactions are rxn21796-21806. Verify whether rxn53279 is a duplicate/obsolete or genuinely a separate monooxygenase that needs role assignment.
6. **Spontaneous Reaction role (rxn22371).** Currently lists `cpd14796 → cpd11229` (phenylacetaldoxime → N-benzylformamide) under *aliphatic* glucosinolate biosynthesis. The substrate is phenolic; either re-classify or split. This appears to be a phenolic side-reaction mis-classified — flag for re-subsystem assignment.
7. **`Benzoylated glucosinolates modification, unresolved step`** holds rxn21838, rxn21837, rxn23787 — secondary modifications (benzoylation of fully formed aliphatic GSLs). Excluded from "first fully formed glucosinolate" scope; noted here for completeness.
8. **`Sinapoylated glucosinolates modification, unresolved step`** holds rxn21839, rxn21840, rxn21835 — also secondary. Excluded.
9. **Transport from chloroplast to cytosol.** Sam's `glucosinolate_transport.tsv` defines nine c→d transport reactions (glucosinolates_1..9) covering both aliphatic intermediates (cpd00869, cpd17400, cpd17403, cpd17407, cpd17411, cpd17415, cpd17419, cpd17423) and γ-glutamylcysteine (cpd00506). All are `NEW reaction` rows waiting on apply-pipeline support.

## Downstream / explicitly excluded (per request — derivatives of first GSL)

- **Aliphatic glucosinolate S-oxygenase (EC 1.14.13.237)**: rxn41751 — methylthio → methylsulfinyl. Converts e.g. glucoiberverin (`cpd05324`) → glucoiberin (`cpd05323`). Excluded.
- **Aliphatic glucosinolate 2-oxoglutarate-dependent dioxygenase + Glucosinolate 2-oxoglutarate-dependent dioxygenase (EC 1.14.11.-)**: rxn27065, rxn23786, rxn27066, rxn23785. AOP-type alkenyl / hydroxyalkyl modifications (glucoraphanin → gluconapin, glucoiberin → sinigrin). Excluded.
- **3-butenylglucosinolate 2-hydroxylase**: rxn27067. Excluded.
- **Indole glucosinolate glucohydrolase (myrosinase)**: rxn23706. Catabolic, not biosynthetic. Excluded.

## Cross-reference

- Upstream substrate supply: see `01_homomethionine_biosynthesis.md`.
- Steps 3 (GST), 4 (GGP) and 5 (C-S lyase) are shared with the aromatic glucosinolate pathway; see notes in reports 03 and 04 for how the same roles cover indolic and phenolic substrates.
