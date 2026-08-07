# plantseed_annotation — tests

Run from this directory:

```
pytest
```

Or from anywhere:

```
pytest Scripts/PlantSEED_v3/Annotation/tests/
```

## Layout

Mirrors `plantseed_curation/tests/`. Each test that mutates state uses
the `tmp_bundle` fixture from `conftest.py`, which creates a temp bundle
directory and sets `PLANTSEED_ANNOT_*` env vars so the library points at
it (never at `/kb/data`).

- `conftest.py` — shared fixtures (`tmp_bundle`, future genome fixtures).
- `test_scaffold.py` — scaffold sanity: every module imports, tmp_bundle
  fixture wires paths correctly, tier config exposes the expected values,
  bundle manifest schema parses. This is the only test file the scaffold
  ships with; every following Phase adds its own test file.

## Planned test files (per phase)

- `test_refbuild_*.py` (Phase 1) — bundle-build steps against a mini SHOOT
  db + Arabidopsis-only OrthoFinder fixture
- `test_algorithms_*.py` (Phase 2) — psi_refined, propagate, kmer
- `test_dispatch.py` (Phase 2) — algorithm chain selection per tier / phylum
- `test_cli_scripted.py` (Phase 3) — CLI end-to-end, scripted invocation
- `tests/benchmarks/specialized_pathways/` (Phase 4) — publication benchmark
  suite: dhurrin in *Zea mays*, taxol in *Taxus wallichiana*, homomethionine in
  *Thlaspi arvense*, aliphatic glucosinolate in *Brassica rapa*, photosynthesis
  in a monocot
