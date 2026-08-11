# External dependencies

Three things PlantSEED needs that are **not** pip dependencies:

| name | what it is | source |
|---|---|---|
| `cobrakbase` | KBase workspace ↔ cobrapy object serialisers | `Fxe/cobrakbase` |
| `modelseedpy` | the Python modelling library — gapfilling, ATP correction, FBA | `cshenry/ModelSEEDpy` |
| `biochemistry` | the ModelSEED biochemistry **database** (reaction/compound data) | `ModelSEED/ModelSEEDDatabase` |

`modelseedpy` and `biochemistry` are different things despite the similar names.
Both are needed. Don't conflate them — the abbreviation "MSD" in this ecosystem
means the *database*.

## Why not pip

Two reasons, and the second is the harder constraint.

**They move far ahead of their PyPI registrations.** `cobrakbase` on PyPI is
0.3.0 from December 2022; the repo is years past it. `ModelSEEDpy` on PyPI is
0.4.2 from March 2025, while the fork that actually builds models for
modelseed.org is over a hundred commits further on. Pinning a PyPI version
would freeze us on code older than what production runs.

**A `git+` requirement would make PlantSEED un-publishable.** PyPI rejects any
distribution carrying a direct-reference dependency, so putting
`modelseedpy @ git+https://...` in `pyproject.toml` would cost us
`pip install plantseed` entirely. Keeping these out of the dependency metadata
is what lets the package be published at all.

So they are pinned by commit in `external.json` and fetched explicitly. Only
adapters and container builds need them; the science core does not, and
`Scripts/PlantSEED_v3/Core/tests/test_core_isolation.py` enforces that.

## Usage

```bash
python deps/fetch.py --list                    # show the pins
python deps/fetch.py                           # fetch all three into deps/src
python deps/fetch.py modelseedpy --install     # fetch one and pip install it
python deps/fetch.py --into /deps --install    # container layout
python deps/fetch.py --verify                  # fail if a checkout has drifted
```

Stdlib only, so it runs before anything is installed.

## Bumping a pin

Edit `commit` in `external.json` and say why in `pinned_because`. Never
automate it. Two of these pins have consequences beyond "newer is better":

- **`biochemistry`** is pinned to the commit immediately *before* the 2026-05-29
  reversibility refresh, so reaction directions match what the published
  templates were generated against. Moving it changes model directionality.
- **`modelseedpy`** is installed `--no-deps` deliberately, because the fork pins
  `scikit-learn==1.2.0`, which cannot build on Python 3.12. We use neither
  `modelseedpy/ml` nor `get_classifier`, so nothing needs sklearn.

## Two traps worth knowing

**ModelSEEDDatabase `dev` and `master` are structurally different branches.**
`dev` — which we pin, and which `modelseed-api` also uses — stores biochemistry
as 111 sharded JSON files (`Biochemistry/reaction_NN.json`,
`compound_NN.json`), with no `Templates/` directory and no `reactions.tsv` or
`compounds.tsv` at all. `master` has the classic single TSVs plus `Templates/`.
PlantSEED reads the sharded form; ModelSEEDpy's own loader expects the TSVs. One
checkout does not serve both.

**`git sparse-checkout` cone mode silently ignores file patterns.** Cone mode
understands directory prefixes only, so asking for individual files gets you
whole directories — and not the files you asked for. `fetch.py` uses
`--no-cone` for this reason.

## Upstream state, for context

Neither `modelseed-api` nor `KB-ModelSEEDReconstruction` pins any of these; both
track branch HEAD at image build time. `modelseed-api`'s own `docs/STANDALONE.md`
concedes it: *"the image always reflects HEAD of those repos at the time the
image was built. For reproducible builds against pinned commits, pin the
`--branch <ref>` ... to specific commit SHAs."* We pin because published numbers
depend on it. A consequence: modelseed.org and PlantSEED can disagree on
reaction directionality, since it follows the moving `dev` tip and we do not.
