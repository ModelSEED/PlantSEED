#!/bin/bash
# PlantSEED v3 reference rebuild — 23 species.
#
# Separate from Run_OF.sh because that script's OF_ROOT points at the Brassica
# Oct2023 project, and its flags are that project's. Nothing here is shared.
#
# Differences from the Sep07 run this supersedes:
#   -A muscle_auto   PPP (-align) at <=500 seqs, super5 above. Sep07 used
#                    super5 for everything, which exiled fragment sequences
#                    into private low-occupancy columns.
#   -z               Don't trim MSAs. OrthoFinder's trimmer is a tree-inference
#                    optimisation; PlantSEED reuses the same MSAs for PSI, where
#                    dropping columns shrinks the denominator and inflates
#                    identity. Measured cost of -z: ~2.2x tree time on the ~15%
#                    of orthogroups that were trimmed at all.
#   -T iqtree2_1t    -nt 1 instead of -nt 5. IQ-TREE scales sublinearly, so on a
#                    fixed core budget 1 thread/process wins at every size
#                    tested (781 vs 158 trees/s at 50 seqs; 12.6 vs 4.8 at 400).
#   -t 336 -a 42     -a per OrthoFinder's README (-t/8); Sep07 used -a 80.
#
# Unchanged from Sep07 and load-bearing:
#   -X               Don't add species names to sequence IDs. Required for the
#                    <species>||<transcript> header scheme to round-trip.
#   -I 1.5           MCL inflation. The code default is 1.2 (README says 1.5 and
#                    is wrong); 1.2 would give ~40.9k orthogroups, not ~56.3k.
set -euo pipefail

OF_ROOT=/scratch1/seaver/PlantSEED_OF_Rebuild_2609
STAMP=$(date +%Y%m%d-%H%M%S)
LOG=${OF_ROOT}.${STAMP}

[ -d "$OF_ROOT" ] || { echo "missing input dir: $OF_ROOT" >&2; exit 1; }
n=$(ls "$OF_ROOT"/*.fa 2>/dev/null | wc -l)
[ "$n" -eq 23 ] || { echo "expected 23 proteomes in $OF_ROOT, found $n" >&2; exit 1; }

# mmseqs / iqtree2 / muscle live in the micromamba env and are NOT on PATH
# by default; without this the run dies at OrthoFinder's dependency check.
export PATH=/scratch/seaver/micromamba/envs/orthofinder/bin:$PATH
export OMP_NUM_THREADS=80
export MUSCLE_BIN=/scratch/seaver/micromamba/envs/orthofinder/bin/muscle
export MUSCLE_AUTO_THRESHOLD=500
export MUSCLE_AUTO_THREADS=1
export MUSCLE_AUTO_LOG=${LOG}.aligner.tsv

cd /scratch/seaver/Projects/OF-process

date | tee "${LOG}.date"
./OrthoFinder/orthofinder.py \
    -S mmseqs -t 256 -a 32 \
    -M msa -A muscle_auto -T iqtree2_1t \
    -X -I 1.5 -z \
    -f "${OF_ROOT}/" > "${LOG}.out" 2> "${LOG}.err"
date | tee -a "${LOG}.date"
