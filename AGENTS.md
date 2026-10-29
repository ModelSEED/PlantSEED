# PlantSEED agent instructions

- Never remove curation files that feed the database (curator TSVs under
  `Scripts/PlantSEED_v3/Curation/Curators/**`), even after they've been
  applied and the change is committed to `PlantSEED_Roles.json` /
  `PlantSEED_Complexes.json`. They are the provenance record for every
  change, not disposable scratch files — keep them even when re-running them
  is a no-op.
