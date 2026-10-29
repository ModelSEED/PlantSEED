# Upstream ModelSEEDDatabase issues found during glucosinolate curation

Found while curating PlantSEED's glucosinolate pathways (PR #56, merged to `dev`
2026-09-30). None of these block PlantSEED — each was worked around on the
PlantSEED side (reaction swap, curator stoichiometry override, or picking the
non-duplicate compound). Filing here so ModelSEEDDatabase can fix the root
cause and the PlantSEED-side workarounds can eventually be retired.

## Duplicate compounds

All three pairs share a formula; InChIKey confirms identity for two of the
three.

| Pair | Formula | InChIKey | Note |
|---|---|---|---|
| `cpd00026` (UDP-glucose) / `cpd28293` (UDP-GLUCOSE) | C15H21N2O17P2 both | `HSCJRCZFDFQWRP-JZMIEXBBSA-K` vs `HSCJRCZFDFQWRP-RDKQLNKOSA-K` (differ only in stereo layer) | Mass also disagrees: 564.0 vs 566.0 for an identical formula. `cpd00026` is used in 22 PlantSEED reactions, `cpd28293` in none — recommend deprecating `cpd28293` in favor of `cpd00026` and relinking any reactions that reference it (e.g. `rxn27046`, see below). |
| `cpd17432` (S-(4-Methylthiobutylthiohydroximoyl)-L-cysteine) / `cpd24789` (S-(4-methylthiobutylhydroximoyl)-L-cysteine) | C8H16N2O3S2 both | `RHJXZAWQBJGJJP-FQUWQITNSA-N` both — **exact match** | `cpd17432` has `mass=null`; `cpd24789` has `mass=252.0` and is actually used (via `rxn24582`). Recommend deprecating `cpd17432`. |
| `cpd23386` (indole-3-acetonitrile oxide) / `cpd17395` (IAOx N-oxide) | C10H9N2O2 both | `NQEXWLFOCGZKAD-UHFFFAOYSA-N` both — **exact match** | Same molecule under two names/IDs. This duplication breaks the indolic glucosinolate pathway: `rxn14107` (CYP83B1 step) produces `cpd17395`, but `rxn21810` (the following GST step) consumes `cpd23386`. PlantSEED's workaround (`Curators/pelle283/Glucosinolates/Indolic_Unblock_260917.tsv`) repoints `rxn21810` onto `cpd17395`, scoped to that one reaction only (an enzyme-wide repoint corrupted the aliphatic C4 GST reaction sharing the same role — see that TSV's rationale). Recommend merging the two compound IDs upstream and then dropping the PlantSEED override. |

## Duplicate / near-duplicate reactions

| Pair | Status | Equation | Note |
|---|---|---|---|
| `rxn21793` / `rxn21794` | both `OK` | identical: `H2O + NADP + (Z)-phenylacetaldehyde oxime <=> NADPH + 3H+ + 2-phenylacetonitrile oxide` | Byte-identical stoichiometry under two reaction IDs. PlantSEED assigned `rxn21793` (see `Curators/pelle283/Glucosinolates/Phenolic_Unblock_260917.tsv`); `rxn21794` is an unused duplicate. Recommend deprecating one. |
| `rxn23775` / `rxn28263` | both `MI:O:1` | identical: `Glucobrassicin <= 4-Hydroxyglucobrassicin` | Both carry the same oxygen-count imbalance. Not currently assigned in PlantSEED (secondary modification, out of scope for this curation pass), but worth fixing/merging upstream regardless. |
| `rxn27046` vs `rxn37539` | `rxn27046` uses `cpd28293` (UDP-GLUCOSE duplicate); `rxn37539` uses `cpd00026` (UDP-glucose) | otherwise identical: `UDP-glucose/UDP-GLUCOSE + 5-methylthiopentylhydroximate <=> UDP + 4-Methylthiobutyl-desulfoglucosinolate` | PlantSEED built the trihomomethionine-track UGT step on `rxn37539` specifically to avoid the duplicate compound. Resolves itself once `cpd28293` is merged into `cpd00026`. |

## Unbalanced reactions, repaired on the PlantSEED side

| Reaction | MetaCyc ID | Status as deposited | PlantSEED fix |
|---|---|---|---|
| `rxn23786` | RXN-2223 | `MI:C:-1/H:-2/S:-1` (missing H2O, O2, H+, methanesulfonate) | Not used — PlantSEED swapped to `rxn44212`, the already-correctly-written form of the same MetaCyc reaction (status `OK`). |
| `rxn27065` | RXNQT-4340 | `MI:C:-1/H:-2/S:-1` — same defect class as `rxn23786`/RXN-2223, but with **no balanced twin to swap to** | PlantSEED added the same four reagents (`H2O -1, O2 -1, H+ +1, methanesulfonate +1`) via a `CPX_ADD` curator override (`Curators/pelle283/Glucosinolates/AOP3_Hydroxyalkyl_Balance_260917.tsv`). Verified to balance exactly (atoms `{}`, charge 0) once added. **Recommend writing RXNQT-4340 with the same four reagents RXN-2223 already carries** — at which point the PlantSEED override becomes redundant and can be dropped. |
| `rxn17379` | — | `MI:C:-6/H:-11/O:-5\|CI:-1` (UDP-GLUCOSE <=> UDP, missing the glucosyl leaving group) | Not used by PlantSEED's glucosinolate curation; flagged only because it surfaced during the `cpd28293` duplicate investigation. Recommend repair or deprecation alongside the `cpd28293` cleanup. |

## The phenolic CYP83 dead end (`rxn53279`)

`rxn53279` — (E)-phenylacetaldoxime + O2 + reduced `[NADPH--hemoprotein
reductase]` → 2-phenylacetonitrile oxide + oxidized `[NADPH--hemoprotein
reductase]` — carries status `CPDFORMERROR`. The generic hemoprotein-reductase
pair (`cpd42231`/`cpd42232`) has no computable formula, so the reaction can
never pass a balance check as deposited.

This is the "correct" substrate-level reaction for the phenolic CYP83 step
(it consumes the (E) isomer that CYP79A2 actually produces), but it cannot be
assigned without either (a) giving the generic hemoprotein-reductase pair a
real formula, or (b) substituting a concrete cofactor pair (e.g. flavins or
NAD(P)H) as was done for other monooxygenases in this pathway.

PlantSEED's actual fix uses a different reaction, `rxn21793`, which is
chemically parallel but requires a substrate isomer swap ((Z)→(E) accepted
because the nitrile-oxide product is achiral — see
`Curators/samseaver/phenolic_glucosinolate_260917/` for the chemistry). That
avoids the `rxn53279` cofactor problem entirely, but `rxn53279` itself remains
broken upstream and unusable as deposited. Recommend giving the generic
`[NADPH--hemoprotein reductase]` pair (or this specific reaction) a resolvable
formula.

## Compound naming off-by-one-carbon (worth a second look, not urgent)

`rxn37539` (trihomomethionine-track UGT step): ModelSEED labels the substrate
`cpd26636` "5-methylthiopentylhydroximate" (C6, correct for the
trihomomethionine track) but the product `cpd17437` "4-Methylthiobutyl-
desulfoglucosinolate" (C5 — one carbon short of what the substrate implies).
The downstream SOT reaction (`rxn27056`) treats `cpd17437` as the correct
C6-chain-length glucosinolate precursor regardless, so the network wiring
works, but the compound name in ModelSEED Biochemistry is one chain length
off from its actual role. Flagging for a naming cleanup, not a blocker.
