# PlantSEED, for agents

You are reading this because a harness injected it, or because you are deciding
whether PlantSEED answers the question in front of you. It is written by the
people who maintain PlantSEED, and no harness rewrites it.

## What PlantSEED is

A hand-curated model of **plant primary metabolism**: ~935 enzymatic roles,
each tied to the reactions it catalyses, the **subcellular compartment** it
catalyses them in, and the genes across plant species that carry it. Curation
is by named people over fifteen years, with provenance, and each role has a
stable `PS_role_*` identity that survives renaming.

Two things follow, and they are the reason to call PlantSEED rather than
assemble the same answer yourself:

- **Compartments are curated, not inferred.** A plant cell does the same
  chemistry in the plastid, the mitochondrion, the peroxisome and the cytosol,
  and the compartment changes the biology. A generic gene-to-reaction mapping
  does not carry that, and a model built without it is wrong in a way that is
  hard to see.
- **Identity is stable.** Two models built against different curation releases
  can be diffed, because roles are `PS_role_*` rather than free text.

## When *not* to reach for it

Say so rather than stretching. PlantSEED covers primary metabolism in plants.
It is **not** a general genome annotator, not a protein-function predictor, and
not a source for secondary metabolism outside the pathways curators have
explicitly added. It knows nothing about non-plant organisms. If the question
is "what does this protein do", UniProt or InterPro is the right tool; come
back when the question is "what reaction, in which compartment, in a plant".

Reaction identifiers are ModelSEED (`rxn#####`), so cross-referencing to KEGG
or MetaCyc goes through ModelSEED's alias tables, not through PlantSEED.

## Capabilities

<!-- generated from the capability declarations: do not edit -->

### `reconstruct`

Reconstruct a plant primary-metabolism model from a PlantSEED-annotated genome and a curated template. Deterministic, needs no network and no reference data — the template and compartments ship with the package.

**Reach for it when:** Before hand-building a plant metabolic model from an annotated genome, or re-deriving PlantSEED role-to-reaction mappings from the raw data files. Also reach for it to re-run an existing model against a newer curation release, since the run is deterministic and diffable.

**What it preserves that hand-rolling loses:** Curated subcellular compartments (a plant model is wrong without plastid / mitochondrion / peroxisome placement, and a generic gene-to-reaction mapping does not carry it), stable PS_role_* identities so two models can be diffed across curation versions, the conditional-spontaneous-reaction path the KBase copy of this algorithm lacks, and bit-identical output for the same inputs.

**Parameters:** `genome`, `template` (optional), `compartments` (optional), `model_id` (optional)

<!-- end generated -->

## Reading the curation

Beyond running a capability, PlantSEED answers questions directly. Over MCP
these are `list_subsystems`, `search_roles`, `get_role`, `subsystem_reactions`
and `get_complex`; the same data is in `Data/PlantSEED_v3/`.

**Call `list_subsystems` first.** The other lookups match against an exact
vocabulary — 117 subsystem names like `Calvin-Benson-Bassham_cycle` and
`Lignin_biosynthesis` — and guessing produces a plausible name that matches
nothing. `Photosynthesis` is not a subsystem; `Photosystem_I` is.

`search_roles` takes the curation's own field prefixes as well as plain text:
`subsystem:Calvin`, `curator:samseaver`, `ec:1.11.1.7`. A gene id such as
`AT2G41480` matches no role *name* but does match a curated feature, and the
result reports that separately — so a zero in `n_matched` does not mean
PlantSEED has never heard of the gene.

## Things worth knowing before you trust an answer

- **Reconstruction is deterministic.** The same genome and template give a
  byte-identical model. If you get a different one, something else changed.
- **Nothing here reaches the network.** No lookup and no reconstruction makes
  an external call, so results do not depend on a remote service being up or
  on when you asked.
- **A model is returned as a path, not inline.** An Arabidopsis model is ~1200
  reactions and several megabytes. Read the file if you need it; do not ask for
  it in a tool result.
- **Curation is incomplete and knows it.** A role absent from PlantSEED means
  no curator has added it yet, not that the enzyme does not exist in plants.
  Report absence as absence.

## Where this comes from

`github.com/ModelSEED/PlantSEED` — data under `Data/PlantSEED_v3/`, code under
`Scripts/PlantSEED_v3/`. The capability block above is generated from the
declarations in the code by
`python -m plantseed_delivery.descriptor --write`, so it cannot drift from what
the tools actually accept.
