# PlantSEED Curation Tool — tests

Run from this directory:

```
pytest
```

Or from anywhere:

```
pytest Scripts/PlantSEED_v3/Curation/tests/
```

## Layout

- `conftest.py` — shared fixtures. The `tmp_db` fixture copies
  `fixtures/mini_roles.json` and `fixtures/mini_schema.yaml` into a temporary
  directory and sets `PLANTSEED_*` env vars so the library points at the copy
  instead of the real database.
- `test_constants.py` — sanity invariants on the action / field / compartment
  tables.
- `test_identity.py` — sanitizers, atomic write, curator registry.
- `test_schema.py` — schema loading, default-role construction, dependency
  validator.
- `test_search.py` — name / field-prefix / by-feature ranked search.
- `test_actions.py` — `validate_payload`, `build_tsv_rows`, `parse_tsv_text`
  edge cases.
- `test_apply_pipeline.py` — end-to-end TSV-to-JSON scenarios with
  every action type, plus the localization / classes / kbase_id cascades.
- `test_curator_files.py` — per-curator file I/O (atomic write, append with
  trailing newlines, list/delete).
- `test_dashboard_http.py` — spins up the dashboard in a background thread
  and exercises every API endpoint via urllib.
- `test_cli_scripted.py` — drives `Curation_Tool.py` with a scripted input
  iterator and asserts the resulting TSV equals what the dashboard's
  `/api/build` produces for the same payload.

## What protects the cross-interface contract

`test_cli_scripted.py::test_cli_and_dashboard_produce_identical_tsv` exists
specifically to detect drift between the CLI and dashboard. Both interfaces
funnel through `plantseed_curation.actions.build_tsv_rows`, so the test
fails the moment one of them starts shaping payloads differently.
