# Path to the Arabidopsis reconstruction that biosynthesises 22/29 glucosinolates

State captured 2026-09-18 on branch `glucosinolate-expansion-260915`.
**Nothing below is committed.** This file is the recipe for reproducing the
current `work/fba/model_a6.json` from a clean checkout of the branch.

## 0. Interpreters — no single one runs the whole pipeline

| stage | interpreter | why |
|---|---|---|
| curation (`Curation/*.py`) | system `python3` | needs `yaml`; bf-runtime lacks it |
| template + reconstruct | `/scratch/seaver/micromamba/envs/bf-runtime/bin/python` | needs `httpx` / `cobra`; system python3 lacks both |
| balance checker | system `python3` | stdlib only |

Worth fixing properly at some point. Until then, using the wrong one fails
loudly for the template scripts but has previously produced a *false* clean
run for curation (`grep -c ERROR` missed a `ModuleNotFoundError`).

```sh
PS=/scratch/seaver/Claude_Projects/plantseed-v3-curation/PlantSEED/Scripts/PlantSEED_v3
BF=/scratch/seaver/micromamba/envs/bf-runtime/bin/python
```

## 1. Apply the curator TSVs

Already-committed TSVs are baked into `PlantSEED_Roles.json` /
`PlantSEED_Complexes.json` on this branch — do NOT re-apply them. Only these
are new and uncommitted, in this order (later ones modify complexes created
by earlier ones):

```sh
cd $PS/Curation
for t in \
  Curators/pelle283/Glucosinolates/GS_OX_ChainLength_260915.tsv \
  Curators/pelle283/Glucosinolates/SCPL17_Acylation_260916.tsv \
  Curators/pelle283/Glucosinolates/Aliphatic_CS_Lyase_Dipeptidase_260916.tsv \
  Curators/samseaver/template_reaction_mods_260917/thylakoid_proton_pumps.tsv \
  Curators/samseaver/template_reaction_mods_260917/glucosinolate_generics.tsv \
  Curators/samseaver/indolic_glucosinolate_260917/indolic_unblock.tsv \
  Curators/samseaver/phenolic_glucosinolate_260917/phenolic_unblock.tsv \
  Curators/samseaver/indolic_derivatives_260917/indolic_derivatives.tsv \
  Curators/samseaver/methanesulfonate_sink_260917/methanesulfonate_sink.tsv \
  Curators/samseaver/aop3_hydroxyalkyl_260917/aop3_hydroxyalkyl.tsv ; do
    echo "== $t"; python3 ./Update_Enzymes_in_PlantSEED.py "$t" || break
done
```

Expect `0 error(s)`. Warnings are not benign here — the most common one is a
`CPX_*` row addressed by **role name** instead of `abstract_enzyme`. Those
differ when the role carries an `(no EC)` suffix, and the row is then skipped
with only a warning. That mistake was made twice.

## 2. Reconcile KBase IDs

```sh
cd $PS/Curation && python3 ./Prepare_PlantSEED_KBase.py
```

Rewrites `kbase_id` where roles/reactions changed. Use this, **not**
`Extract_PlantSEED_KBase_Complexes.py`, which emits two-letter compartments
and dies with `KeyError: 'ce'` (pre-existing, reproducible on pristine v2.5).

## 3. Re-annotate the genome — only if gene IDs changed

`work/fba/Athaliana_TAIR10_annotated_genome.json` (1481 features) is current
and can be reused as-is.

**Trap:** `$PS/Model/annotate-arabidopsis-genome.py` fetches
`PlantSEED_Roles.json` over HTTP from the `dev` branch (line 131). The
local-file path is commented out at lines 127-129. Run it unmodified and you
annotate against `dev`, silently discarding all local curation. Uncomment the
local path before running.

## 4. Template

```sh
cd $PS/Template
$BF ./Generate_Core_ModelTemplate.py
$BF ./Add_ModelTemplate_Biomass.py
```

Expect on stdout:
```
Including unbalanced reactions: rxn00689, rxn07579, rxn11700
INFO: rxn27065_c: admitted on curator stoichiometry override (deposited status MI:C:-1/H:-2/S:-1)
```

Biochemistry is pinned by `MSD_PINNED_COMMIT = 465b7116c1...` (2026-05-06) and
cached in `Template/Biochem_Cache/*.pickle`. Delete the pickles to refetch.
Do not bump the pin casually — it freezes reaction directions.

## 5. Reconstruct

```sh
cd /scratch/seaver/Claude_Projects/plantseed-v3-curation
PYTHONPATH=$PS/Annotation:$PS/Model $BF -m plantseed_annotation.reconstruct_cli \
  --genome   work/fba/Athaliana_TAIR10_annotated_genome.json \
  --template $PS/Template/PlantSEED_Biomass_Template.json \
  --compartments PlantSEED/Data/PlantSEED_v3/Compartments/PlantSEED_Compartments.json \
  --model-id Athaliana_TAIR10_model \
  --out      work/fba/model_a6.json
```

Expect **1331 model compounds, 1246 model reactions**.

## 6. Verify

```sh
cd $PS/Template && python3 ./Check_Template_Reaction_Balance.py
```
Expect `ERROR=0  WARN=5  KNOWN=5  GATED=0  STALE=0  NOTE=86  OK=1164`, exit 0.
`ERROR` is the only failing class: it means a curator stoichiometry override
claims to balance a reaction and does not.

FBA sweep: 22 of 29 glucosinolates carry flux to a demand reaction.

## What is producible (22)

Glucotropeolin, 3-hydroxypropyl-GSL, Glucoiberverin, 4-hydroxybutyl-GSL,
Glucoerucin, Glucoiberin, Sinigrin, Glucoberteroin, Glucoraphanin, Gluconapin,
Glucolesquerellin, Glucobrassicin, Glucoalyssin, 7-methylthioheptyl-GSL,
6-methylsulfinylhexyl-GSL, 1-hydroxyglucobrassicin, 4-hydroxyglucobrassicin,
8-methylthiooctyl-GSL, 7-methylsulfinylheptyl-GSL, Neoglucobrassicin,
4-methoxyglucobrassicin, Glucohirsutin.

## What is still blocked (7), and why

All seven are acylated or hydroxylated derivatives. **Not a PlantSEED gap.**

- `cpd22000`, `cpd23416`, `cpd23419`, `cpd23421` — benzoyl/sinapoyl esters of
  the two OH-GSLs. Both acceptors carry flux; both acyl donors (`cpd00401`
  Benzoyl-CoA, `cpd00326` Sinapoyl-CoA) are dead ends with nothing producing
  them. The acyltransferase roles are correctly curated and included, with
  `AT3G12203` (SCPL17) assigned to both.
- `cpd26644`, `cpd23420`, `cpd23422` — the 2-hydroxy-3-butenyl series, blocked
  upstream of acylation on the GSL-OH route.

**Do not unblock these by adding `rxn01590` / `rxn01035`.** Those are the
sinapate- and benzoate-CoA ligases, and they encode a superseded pathway.
Lee et al. 2012 (doi:10.1111/j.1365-313X.2012.05096.x) show SCPL17 transfers
both acyl groups from **1-O-acyl-glucose** donors, not CoA thioesters, and
that BZO1's in vivo role is making cinnamoyl-CoA rather than benzoyl-CoA
(superseding doi:10.1111/j.1365-313X.2007.03205.x).

Closing this correctly requires upstream ModelSEEDDatabase work:
1-O-benzoyl-beta-D-glucose does not exist in MSD in any spelling, and zero MSD
reactions acylate a glucosinolate from a glucose ester. Encouragingly
`cpd00422` Cinnamoyl-CoA and `cpd00333` (E)-Cinnamate are already in the model.

## Open items unrelated to the above

- Role renames: `Alkylthiohydroximate C-S lyase` and `Aliphatic desulfo-
  glucosinolate sulfotransferase` are named aliphatic-only but serve all three
  branches; `metabolizining` typo; `Cytochrome 9450` -> CYP81F4, which collides
  with the existing empty `CYP81F4 monooxygenase` role.
- Upstream MSD report: `cpd12458` stearoyl-ACP is one H short (`C29H55` ->
  `C29H56`), reaching 29 reactions; `cpd06227` "THF-L-glutamate" carries two
  glutamates while `rxn00689` adds one; 77 MSD reactions have a stored status
  claiming mass-clean that recomputation contradicts.
