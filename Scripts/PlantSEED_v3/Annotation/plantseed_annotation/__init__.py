"""plantseed_annotation — shared library for the plant genome annotator.

Mirrors the layout of the plantseed_curation package next door:
  - paths.py       — PLANTSEED_ANNOT_* env-var overrides for every file path
  - config.py      — tier presets (kbase / poplar / local) that pin CPU/RAM/refdata
  - reference.py   — locate + verify the versioned refdata bundle
  - refbuild/      — offline scripts that (re)build a bundle from PlantSEED_Roles.json
  - algorithms/    — pluggable annotation algorithms
  - dispatch.py    — pick algorithm(s) for a run based on tier + role phylum
  - genome_io.py   — KBase Genome  <->  standalone JSON adapters
  - emit.py        — write both `role # compartment` strings AND PS_role_* ids
  - cli.py         — `plantseed-annotate --genome ... --tier {kbase,poplar,local}`

Consumers (KBase SDK App, poplar celery worker, local Docker) all pip-install
this package and go through the public API re-exported below; no algorithm
code is duplicated in any wrapper.

Approved plan: ~/.claude/plans/ok-entirely-new-and-functional-tulip.md
"""

# Public API surface — filled in as each phase lands.
__all__ = []
