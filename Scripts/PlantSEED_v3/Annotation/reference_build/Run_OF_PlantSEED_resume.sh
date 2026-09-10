#!/bin/bash
# PlantSEED v3 reference rebuild — resume from the completed mmseqs search.
#
# The 2026-09-09 00:02 run completed its 529-way search (3h20m) and reproduced
# Sep07's 56,253 orthogroups exactly, then bogged down in the alignment phase:
# PPP on 481-496-sequence orthogroups at -threads 1 was taking >2.5h each while
# only ~29 of 256 cores were busy. Projected 171h. Killed at 08:43.
#
# Two changes from that attempt, everything else identical:
#   MUSCLE_AUTO_THRESHOLD 500 -> 200
#       Caps PPP at a size where it is genuinely cheap (3.5s at n=200 with
#       default threading). 514 orthogroups go to super5 instead of 83.
#   MUSCLE_AUTO_THREADS 1 -> unset
#       -threads 1 maximises throughput ONLY when the scheduler supplies enough
#       concurrent tasks to fill the cores. OrthoFinder processes orthogroups
#       largest-first and does not, so 1 thread just made each task ~28x slower
#       on idle cores. Unset restores muscle's default, which is what the
#       successful Sep07 run used.
#
# -t 80 matches Sep07's proven setting rather than pushing 256.
set -euo pipefail

BLAST=/scratch1/seaver/PlantSEED_OF_Rebuild_2609/OrthoFinder/Results_Sep09/WorkingDirectory
# NB: -o is rejected with -b; results nest at $BLAST/OrthoFinder/Results_<date>/
STAMP=$(date +%Y%m%d-%H%M%S)
LOG=/scratch1/seaver/PlantSEED_OF_Rebuild_2609.resume-${STAMP}

n=$(ls "$BLAST"/Blast*.gz 2>/dev/null | wc -l)
[ "$n" -eq 529 ] || { echo "expected 529 Blast files in $BLAST, found $n" >&2; exit 1; }
[ -f "$BLAST/SpeciesIDs.txt" ] && [ -f "$BLAST/SequenceIDs.txt" ] || {
    echo "missing SpeciesIDs.txt / SequenceIDs.txt in $BLAST" >&2; exit 1; }

export PATH=/scratch/seaver/micromamba/envs/orthofinder/bin:$PATH
export OMP_NUM_THREADS=80
export MUSCLE_BIN=/scratch/seaver/micromamba/envs/orthofinder/bin/muscle
export MUSCLE_AUTO_THRESHOLD=200
unset MUSCLE_AUTO_THREADS
export MUSCLE_AUTO_LOG=${LOG}.aligner.tsv

cd /scratch/seaver/Projects/OF-process

date | tee "${LOG}.date"
./OrthoFinder/orthofinder.py \
    -b "$BLAST" \
    -t 80 -a 16 \
    -M msa -A muscle_auto -T iqtree2_1t \
    -X -I 1.5 -z > "${LOG}.out" 2> "${LOG}.err"
date | tee -a "${LOG}.date"
