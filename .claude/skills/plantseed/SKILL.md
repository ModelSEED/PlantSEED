---
name: plantseed
description: Query the curated PlantSEED model of plant primary metabolism, and reconstruct a metabolic model from an annotated plant genome. Use when a question involves plant metabolic reactions, enzymatic roles and their subcellular compartments, PlantSEED subsystems or PS_role_* / PS_complex_* identifiers, or when building or re-deriving a plant metabolic model. Not a general genome annotator and not for non-plant organisms.
---

# PlantSEED

**Audience note.** This file is for an *interactive* Claude Code session, where
the `Skill` tool exists. KIND\*AI cannot use it: those sessions run with
`setting_sources=None` and an `allowed_tools` list that omits `Skill`, so
`~/.claude/skills/` is neither discovered nor invocable there. The harness path
is the MCP server plus `Scripts/PlantSEED_v3/for-agents.md`, which this file
deliberately does not duplicate — read it for what PlantSEED is, what it
guarantees, and where it stops.

## How to call it here

From a checkout, with the package installed (`pip install -e ".[curate,mcp]"`):

```bash
plantseed capabilities            # what is declared, with when/guarantee
plantseed capabilities --json     # the manifest a harness would ingest
plantseed-reconstruct --genome <annotated_genome.json> --out model.json
```

The curation lookups are a Python import rather than a CLI:

```python
from plantseed_delivery import queries
queries.list_subsystems()                                   # call this first
queries.search_roles("subsystem:Calvin")
queries.get_role("PS_role_1cc588")
queries.subsystem_reactions("Calvin-Benson-Bassham_cycle")
```

Against the container instead of a checkout:

```bash
docker run --rm -v "$PWD:/input:ro" -v "$PWD/out:/output" \
    plantseed:dev reconstruct --genome /input/genome.json --out /output/model.json
```

`/output` is the only writable location besides `/tmp`; the image enforces
that rather than assuming it, so a path anywhere else is refused with a message
naming the permitted roots.

## Capabilities

<!-- generated from the capability declarations: do not edit -->

### `reconstruct`

Reconstruct a plant primary-metabolism model from a PlantSEED-annotated genome and a curated template. Deterministic, needs no network and no reference data — the template and compartments ship with the package.

**Reach for it when:** Before hand-building a plant metabolic model from an annotated genome, or re-deriving PlantSEED role-to-reaction mappings from the raw data files. Also reach for it to re-run an existing model against a newer curation release, since the run is deterministic and diffable.

**What it preserves that hand-rolling loses:** Curated subcellular compartments (a plant model is wrong without plastid / mitochondrion / peroxisome placement, and a generic gene-to-reaction mapping does not carry it), stable PS_role_* identities so two models can be diffed across curation versions, the conditional-spontaneous-reaction path the KBase copy of this algorithm lacks, and bit-identical output for the same inputs.

**Parameters:** `genome`, `template` (optional), `compartments` (optional), `model_id` (optional)

<!-- end generated -->

## Before you answer from this

`list_subsystems` first — the vocabulary is exact and a guessed subsystem name
matches nothing. A role absent from PlantSEED means no curator has added it,
not that the enzyme does not exist; say so that way. And a reconstruction comes
back as a path, not as JSON in the transcript.
