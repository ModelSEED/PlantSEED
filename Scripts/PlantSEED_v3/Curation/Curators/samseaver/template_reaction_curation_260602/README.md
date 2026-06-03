# Template-reaction curation — 2026-06-02

This batch captures every hard-coded stoichiometric / structural change that
currently lives at the bottom of `Scripts/PlantSEED_v3/Template/Generate_Core_ModelTemplate.py`
(roughly lines 484–622) and turns each one into a single curator-readable TSV row,
plus a proposed schema expansion to `Data/PlantSEED_v3/PlantSEED_Complexes.json`
so the Generate script can read these changes from data instead of code.

## Files

| File | What it covers | Source lines in Generate_Core_ModelTemplate.py |
|---|---|---|
| `photosynthesis_proton_pumps.tsv` | PS II + Cytochrome b6f proton motive force across the thylakoid | 505–524 |
| `glucosinolate_chemistry.tsv` | BCAT3 + monooxygenase compound replacements; IMDH NAD usage | 527–563 |
| `glucosinolate_transport.tsv` | 9 brand-new glucosinolate transport reactions (cytosol → stroma) | 568–622 |

## TSV schema

Same shape as the role-curation TSVs: tab-separated columns, lines starting
with `#` are comments, blank lines ignored.

```
<enzyme_or_role_name>  <action>  <field>  <value>  [<extra_1>  [<extra_2>]]
```

### Actions

| Action | Field | Columns 4+ | Existing? | Effect |
|---|---|---|---|---|
| `ASSIGN` | `direction` | `<dir>` (`>`, `<`, `=`) | yes | Set the catalysed reaction's direction. Lands in `complex.direction`. |
| `ASSIGN` | `name` | `"display name"` | proposed | Set a human-readable name on a `NEW` reaction. Lands in `complex.template_only.name`. |
| `UPDATE` | `stoichiometry` | `<cpd> <coeff>` | yes (matches `proline_chemistry.tsv`) | Upsert into `complex.stoichiometry[<cpd>] = <coeff>`. Coefficient `0` removes the reagent at apply time. |
| `ADD` | `reagent` | `<cpd> <coeff> [<cpt>]` | proposed | Append a brand-new reagent. Lands in a new `complex.reagent_additions` list (see below). Blank `<cpt>` = reaction's home compartment; cross-compartment reagents (e.g. lumen protons sourced from the stroma) require an explicit compartment. |
| `REPLACE` | `compound` | `<old_cpd> <new_cpd>` | proposed | Substitute one compound for another wherever it appears in the catalysed reaction(s). Coefficients and compartments are preserved. Lands in a new `complex.compound_replacements` dict. |
| `NEW` | `reaction` | `<synthetic_id> <home_cpt>` | proposed | Declare a brand-new template-only reaction with no underlying MS biochemistry. Lands in a new complex entry with `template_only: {...}`. Subsequent `ADD reagent` and `ASSIGN name` rows populate it. |

`UPDATE stoichiometry` does not have to be a NEW action — Sam's
`proline_chemistry.tsv` already used that exact shape, so the new actions
(`ADD reagent`, `REPLACE compound`, `NEW reaction`) are the only additions
the apply pipeline needs to understand.

## How each row lands in `PlantSEED_Complexes.json`

### 1. `ASSIGN direction <dir>` — already supported

Existing example near the bottom of the file (Proline dehydrogenase):

```json
"direction": ">"
```

### 2. `UPDATE stoichiometry <cpd> <coeff>` — already supported

Existing example (Proline dehydrogenase):

```json
"stoichiometry": {
    "cpd00015": "0",
    "cpd00982": "0",
    "cpd00067": "3"
}
```

### 3. `ADD reagent <cpd> <coeff> [<cpt>]` — new field

Coefficients keep the +/- sign of substrates/products. The optional
compartment is required only when the reagent's compartment differs from the
catalysed reaction's home compartment (the proton-pump case).

Proposed JSON for the **Photosystem II** complex (`PS_complex_385743`):

```json
{
    "kbase_id": "PS_complex_385743",
    "enzyme": "Photosystem II",
    "roles": [ ... existing 28 roles ... ],
    "compartments_reactions": {
        "y": {
            "reactions": ["rxn20632"],
            "reagents": "y",
            "exclude": false
        }
    },
    "reagent_additions": [
        { "compound": "cpd00067", "coefficient": -4.0, "compartment": "d" },
        { "compound": "cpd00067", "coefficient":  4.0, "compartment": "y" }
    ]
}
```

Proposed JSON for the **Cytochrome b6f** complex (`PS_complex_49f171`),
combining the existing `stoichiometry` change with a `reagent_additions`
entry:

```json
{
    "kbase_id": "PS_complex_49f171",
    "enzyme": "Cytochrome b6-f",
    "roles": [ ... existing 8 roles ... ],
    "compartments_reactions": { "y": { "reactions": ["rxn20595"], "reagents": "y", "exclude": false } },
    "stoichiometry": { "cpd00067": "-2.0" },
    "reagent_additions": [
        { "compound": "cpd00067", "coefficient": 4.0, "compartment": "y" }
    ]
}
```

### 4. `REPLACE compound <old_cpd> <new_cpd>` — new field

A flat compound-to-compound map. Coefficients and compartments stay the same.

Proposed JSON for the **BCAT3 transaminase** complex (`PS_complex_e65be5`):

```json
{
    "kbase_id": "PS_complex_e65be5",
    "enzyme": "2-oxo-5-methylthiopentanoate transaminase",
    "roles": ["2-oxo-5-methylthiopentanoate transaminase (EC 2.6.1.-)"],
    "compartments_reactions": {
        "d": {
            "reactions": ["rxn23780", "rxn27069", "rxn27070",
                          "rxn27071", "rxn27072", "rxn27073"],
            "reagents": "d", "exclude": false
        }
    },
    "compound_replacements": {
        "cpd22369": "cpd00023",
        "cpd21904": "cpd00024"
    }
}
```

The IMDH complex (`PS_complex_76f95b`) combines `stoichiometry` (proton
removal) and `reagent_additions` (NAD+/NADH pair) — no compartment column,
so the apply step uses each reaction's own compartment:

```json
{
    "kbase_id": "PS_complex_76f95b",
    "enzyme": "Methylthioalkylmalate dehydrogenase",
    "roles": ["Methylthioalkylmalate dehydrogenase (EC 1.1.1.-)"],
    "compartments_reactions": {
        "d": {
            "reactions": ["rxn14172","rxn14182","rxn13977","rxn14122","rxn14244","rxn13983"],
            "reagents": "d", "exclude": false
        }
    },
    "stoichiometry": { "cpd00067": "0" },
    "reagent_additions": [
        { "compound": "cpd00003", "coefficient": -1.0 },
        { "compound": "cpd00004", "coefficient":  1.0 }
    ]
}
```

### 5. `NEW reaction <id> <home_cpt>` — new top-level concept

A template-only reaction has no MS base reaction and no enzyme catalyst, but
it does need a stable place in the JSON to live so the Generate script can
discover it. Two reasonable shapes:

**(a) New `template_only` block on a complex entry** — keeps everything in
`PlantSEED_Complexes.json`, with a synthetic role and an explicit reagents
list. Example for `glucosinolates_1`:

```json
{
    "kbase_id": "PS_complex_glucosinolates_1",
    "enzyme": "Glucosinolate Transport",
    "roles": ["Glucosinolate Transport (cpd00869)"],
    "template_only": {
        "id": "glucosinolates_1",
        "home_compartment": "d",
        "name": "Glucosinolate Transport",
        "reagents": [
            { "compound": "cpd00869", "coefficient": -1.0, "compartment": "c" },
            { "compound": "cpd00869, "coefficient":  1.0, "compartment": "d" }
        ]
    }
}
```

The Generate script's main loop currently iterates `reactions_roles` (which
is built from `compartments_reactions`); a small change would be to also
iterate any complex that carries a `template_only` block and synthesise the
template reaction from that data instead of from `reactions_dict[base]`.

**(b) Sibling file `PlantSEED_Template_Reactions.json`** — cleaner if there
will be many of these in the future. Same structure, just outside the
complex JSON. Either way the TSV stays as-is; only the apply pipeline
decides where the record lands.

I'm leaning (a) because it keeps everything in one file and one curator
workflow, and there are only 9 such reactions today.

## Open questions / follow-ups

1. **rxn53279 has no role and no complex** — the monooxygenase
   compound-swap block in `Generate_Core_ModelTemplate.py` cannot fire today
   because the reaction never reaches the iteration. The placeholder anchor
   name in `glucosinolate_chemistry.tsv` should be replaced with the real
   role name once that reaction is assigned to a complex.
2. **rxn20632 is shared by two complexes** (Photosystem II and Cytochrome
   b559). The proton pump is a property of the *reaction* in compartment y,
   so the apply pipeline needs to choose: (i) record the additions on every
   owning complex (verbose but explicit), or (ii) record once and have
   Generate merge additions from all complexes touching the same template
   reaction. I drafted the row against the Photosystem II complex on the
   assumption that (ii) is preferable; happy to switch if you prefer (i).
3. **Block 5's proton removal** uses `UPDATE stoichiometry cpd00067 0`. The
   existing apply code in Generate already treats coefficient 0 as
   "remove" — no new logic needed, just confirming this is the right way
   to express "find and pop this reagent".
