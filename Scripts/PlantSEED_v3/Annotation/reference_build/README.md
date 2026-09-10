# Building the PlantSEED reference OrthoFinder run

What produced `Results_Sep09`, the 23-species reference the Phase 1 bundle is
built from. `provenance_Sep09.json` records the exact run; this explains why
the settings are what they are, because none of them are OrthoFinder defaults
and all of them were arrived at by measurement.

## Files

| file | purpose |
|---|---|
| `Run_OF_PlantSEED.sh` | full rebuild from proteomes (search included, ~9 h) |
| `Run_OF_PlantSEED_resume.sh` | rebuild reusing a completed search via `-b` (~5 h) |
| `muscle_auto` | size-dispatching aligner wrapper, registered as an MSA method |
| `provenance_Sep09.json` | the run that is current |

`muscle_auto` needs a `muscle_auto` entry in `~/config_orthofinder_user.json`:

```json
"muscle_auto": { "program_type": "msa",
                 "cmd_line": "<abs path>/muscle_auto INPUT OUTPUT" }
```

and `iqtree2_1t` a copy of the `iqtree2` entry with `-nt 5` changed to `-nt 1`.
Both are additive; the stock `muscle` and `iqtree2` entries keep working, so
other projects sharing that config are unaffected.

## Why `-z` (no MSA trimming)

OrthoFinder trims alignments in place before tree inference
(`scripts_of/trees_msa.py`, `trim.py`): columns occupied by fewer than 10% of
members are deleted, with no floor on what any single sequence retains. It is
a tree-inference optimisation and a reasonable one — trimmed columns are
mostly gaps, and IQ-TREE compresses site patterns so the saving is real.

PlantSEED reuses those same MSAs to compute PSI, and there the rationale does
not transfer. PSI divides by the ungapped length *within the alignment*, so
deleting columns where a gene has residues but its partners have gaps — which
are, by construction, non-matching positions — shrinks the denominator faster
than the numerator and inflates identity. Measured on the curated set: 27.9%
of Arabidopsis curated transcripts lost residues, and 27.6% of curated PSI
pairs came out inflated.

In the extreme a sequence loses every residue and becomes an all-gap row.
IQ-TREE refuses those alignments outright; nine orthogroups had no gene tree
in `Results_Sep07` for this reason, and none do now.

Cost of `-z`, measured rather than assumed:

- tree inference **~2.2x** on the ~15% of orthogroups that were trimmed at all
- PSI build **11.5x** total work, and — the part that matters — a **~45 min
  serial critical path** on the largest curated orthogroup, since one
  orthogroup runs on one worker. `compute_psi_for_msa` wants parallelising
  inside an orthogroup before this becomes routine.
- bundle `orthofinder_families` 48 MB -> 154 MB

## Why `muscle_auto` rather than plain `-A muscle`

super5 is MUSCLE's approximate algorithm for inputs too large for PPP. It
clusters greedily (two UCLUST passes), aligns each cluster, then joins cluster
*profiles* — and a sequence never revisits its cluster assignment. Fragmentary
and partial gene models get separated on coverage rather than homology, land
in a small cluster, and are placed beside the main block instead of onto it.

Concretely, in a 96-sequence orthogroup a 207 aa Poplar fragment **76%
identical** to residues 66-273 of the Arabidopsis member sat in columns
occupied by 7 of 96 sequences under super5, and 56 of 96 under PPP. Combined
with trimming those columns were then deleted and the gene became all-gap.

`-z` alone does not fix this: the residues survive but stay misaligned, giving
falsely *low* PSI (median 0.000 vs 0.137 for the exiled fragments) — arguably
worse, since a plausible number is harder to notice than a missing one.

The threshold is 200 because PPP is faster *and* more accurate below roughly
that size, and becomes memory-prohibitive above it (39 GB on a 1,694-sequence
orthogroup). At 200, 514 of 110,579 orthogroups take the super5 path.

## Threading

Both muscle and IQ-TREE scale sublinearly, so on a fixed core budget many
single-threaded processes beat few heavily-threaded ones. Measured throughput
as `(cores / threads) / latency` on 336 cores:

```
muscle PPP, 96 seqs     1 thread  85.1 s -> 3.95 aln/s      default -> 0.34/s
IQ-TREE, 50 seqs        1 thread   0.43 s ->  781 trees/s    -nt 5   ->  158/s
IQ-TREE, 400 seqs       1 thread  26.6 s -> 12.6 trees/s     -nt 5   ->  4.8/s
```

Output is byte-identical at every thread count; this is purely scheduling.

**But this only holds when the scheduler keeps the cores fed.** OrthoFinder
processes orthogroups largest-first, and during that phase there are only a
few dozen tasks available, not hundreds. A first attempt with
`MUSCLE_AUTO_THREADS=1` *and* `MUSCLE_AUTO_THRESHOLD=500` put ~490-sequence
groups through PPP at one thread and spent 2.5 h per orthogroup on ~29 of 256
busy cores, projecting 171 h. It was killed and restarted. If you raise the
threshold, raise the thread count with it.

## Avoid `-nt AUTO`

IQ-TREE's AUTO mode benchmarks thread counts before inferring, and on small
alignments the benchmark dwarfs the work: **719 s to produce a 430 ms tree**.
It picks 1 anyway.

## Known wart

`OG0041473` has a 0-byte MSA file: muscle truncated the output before refusing
the two 23,898 aa Chlamydomonas proteins, and OrthoFinder copied the empty
file through. An absent file would be cleaner — any `OG*.fa` glob skips it,
whereas a 0-byte one parses to an empty alignment.
