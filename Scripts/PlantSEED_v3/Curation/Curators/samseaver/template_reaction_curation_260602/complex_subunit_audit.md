# Multi-subunit complex audit — 2026-06-02

Comparing `Data/PlantSEED_v3/PlantSEED_Complexes.json` (curator intent) with
`Scripts/PlantSEED_v3/Template/PlantSEED_Neutral_Template.json` (Generate
script output) to see whether multi-subunit complexes survive the template
generation with their subunit structure intact.

## Headline numbers

- **41 of 767** complexes in the source JSON have >1 role (i.e. are intended
  to be multi-subunit GPRs).
- Of those 41:
  - **34 intact** — every subunit role appears under the right complex in
    the template.
  - **4 partial** — at least one subunit was filtered out.
  - **3 fully dropped** — every subunit was filtered out, so the complex
    doesn't appear in the template at all.
- **26 subunit roles** were dropped in total.

## Every drift case (intent → template)

All drops trace to one of the role-exclusion filters in
`Generate_Core_ModelTemplate.py`:
`include=false`, the vacuolar ATP synthase rule (rxn08173 + compartment v),
or a missing `kbase_id`.

| Complex (kbase_id) | Intended | Kept | Lost | Dropped subunits → reason |
|---|---:|---:|---:|---|
| `PS_complex_dcc1fd` V-type ATP synthase | 8 | 0 | 8 | All eight subunits (A–H) flagged `include=false` AND match the rxn08173+v rule |
| `PS_complex_385743` Photosystem II | 28 | 18 | 10 | PsbS, PsbO, PsbP, PsbQ, Psb28, PsbN, PsbX, PsbY, HCF136/Ycf48, Ycf39 — all `include=false` |
| `PS_complex_dcc1fd` V-type ATP synthase | 8 | 0 | 8 | (same as above) |
| `PS_complex_57087d` Phosphatidylinositol 4-kinase | 2 | 0 | 2 | α and β polypeptides `include=false` |
| `PS_complex_68a25b` Phosphatidylinositol-4-phosphate 3-kinase | 2 | 0 | 2 | α and β polypeptides `include=false` |
| `PS_complex_ba2de1` Photosystem I | 22 | 20 | 2 | Ycf3, Ycf4 assembly factors `include=false` |
| `PS_complex_49f171` Cytochrome b6-f | 8 | 7 | 1 | PetL `include=false` |
| `PS_complex_19f1c6` Nicotinamidase | 2 | 1 | 1 | "Nicotinamidase of PncA family, nonfunctional" `include=false` |

### Quick reading of the drops

- **V-ATP synthase, PI-4-K, PI-4-P-3-K** — entire complexes are gone from the
  template. This is presumably intentional (the V-ATPase pumps protons into
  the vacuole, which causes FBA issues; the PI kinases produce signalling
  lipids irrelevant to metabolic flux) but it does mean those GPRs are
  unavailable to FBA at all.
- **PS II and PS I** — assembly factors, OEC subunits, and small accessory
  proteins are dropped. The catalytic core remains, so the reactions are
  still gated by a credible subset of subunits, but the GPR strictly under-
  represents what's biologically required.
- **Cytochrome b6f and Nicotinamidase** — single-subunit losses; minor.

## Reactions with multiple complex GPRs in the template

There are **31** template reactions with >1 complex ref (29 with 2 complexes,
2 with 3). Classified:

- **27 independent enzymes** — genuinely different proteins able to catalyse
  the same reaction. Examples: `rxn00001_c` Pyrophosphate-energized proton
  pump vs Inorganic pyrophosphatase; `rxn00275_d` Glutamate-glyoxylate
  aminotransferase vs L-alanine:glyoxylate aminotransferase. These are the
  expected "isoenzyme OR" structure and need no curation.
- **2 isoenzymes** (same EC bracket, different sub-specificities) —
  `rxn14161_c` and `rxn14237_c` (penta-/hexahomomethionine N-hydroxylases).
- **2 split-subunit complexes** — the case you asked about, where one
  complex looks like it was carved out of a larger one rather than being a
  truly independent enzyme:
  - **`rxn20632_y`** (PS II water-splitting): Photosystem II (18 kept of 28)
    + Cytochrome b559 (2). b559 is a structural subunit of PS II.
  - **`rxn00908_m`** (glycine cleavage): Glycine cleavage system (3 roles —
    P/H/L proteins) + Aminomethyltransferase (1 role — the T-protein).
    The T-protein *is* a subunit of the glycine cleavage system; carving it
    out into its own complex gives FBA a false "either-or" choice.

## The structural question

The two split-subunit cases (`rxn20632_y`, `rxn00908_m`) have the same
shape: a smaller subunit set has been pulled into its own complex entry,
which the template then represents as an OR-joined GPR. KBase FBA would
treat any one of:

- the 18-role PS II complex alone, OR
- the 2-role Cytochrome b559 complex alone

as sufficient to catalyse `rxn20632_y`. Biochemically, both are required
together, so the model can spuriously catalyse water-splitting given just
PsbE+PsbF and none of the other 28 subunits.

The cleanest fixes are mutually exclusive:

1. **Merge the subunit complex back into the parent** — drop
   `PS_complex_743fd8` and add PsbE+PsbF as roles on `PS_complex_385743`.
   Same for the T-protein in the glycine cleavage system. GPR becomes a
   single AND over all subunits, which is what KBase expects.
2. **Keep them separate but mark as required subcomplexes** — would need a
   new field in the complex JSON (e.g. `subcomplex_of`) and a Generate
   script change to emit an AND-joined GPR instead of OR.

(1) is a 4-line JSON edit; (2) is a small schema/code change but preserves
the curator intent of "these proteins are a structurally distinct
sub-assembly."

## Suggested next steps

Pick whichever resonates:

- **A.** I'll merge PsbE/PsbF into PS II and the T-protein into the glycine
  cleavage system in `PlantSEED_Complexes.json`, then re-run the test on
  `rxn20632_y` and `rxn00908_m` to confirm the GPR collapses to a single
  complex ref.
- **B.** I'll add `subcomplex_of: "<parent_kbase_id>"` to the carve-out
  complexes (b559, aminomethyltransferase) and patch `Generate_Core_ModelTemplate.py`
  to emit those as AND-joined extensions rather than separate complexes.
- **C.** I look for other carve-out cases in the broader complexes JSON (my
  heuristic only flagged 2; there may be more once we look at reactions with
  a SINGLE complex but where the role list looks like an obvious sub-assembly).
- **D.** Inspect the 10 dropped PS II accessory roles (`include=false`) and
  decide whether any should be flipped back to `include=true` so the GPR
  better reflects biology.
