#!/usr/bin/env python3
"""Build poplar_test_500.faa: a deployment smoke-test proteome for `annotate`.

250 Populus trichocarpa v4.1 proteins that a refdata bundle annotates, plus
250 drawn at random from genes with no Poplar member in any curated
orthogroup. A healthy service annotates all of the first 250 and close to
none of the second (expected_plantseed_genes.txt lists the first 250).

The first half is selected by running the annotator, not just by curated-OG
membership: 600 random curated-OG transcripts were annotated against the
bundle and 250 of the annotated genes were sampled, one transcript each.
That guarantees the "should annotate" half really does.

Usage (needs diamond + mafft on PATH and the plantseed package installed):
    make_poplar_test_set.py <bundle_dir> <Ptrichocarpa_533_v4.1.protein.fa> <out_dir>

Built 2026-10-29 from the Sep09 bundle (b_sep09, content_id 557fcac8...)
and /scratch1/seaver/PlantSEED_OF_Rebuild_2609/Ptrichocarpa_533_v4.1.protein.fa
with SEED below; the committed files are this script's output. Result via
the plantseed:dev annotate tool: 272 of 500 placed, 251 annotated (250/250
expected + Potri.017G001700, ADP-glucose pyrophosphorylase, from the random
half: its gene has no Poplar member in a curated orthogroup but DIAMOND
places it into one).
"""

import glob
import os
import random
import re
import sys

SPECIES = "Ptrichocarpa_v4.1"
SEED = 20261029
N_EACH = 250
N_CANDIDATES = 600


def gene_of(transcript):
    t = transcript[:-2] if transcript.endswith(".p") else transcript
    return re.sub(r"\.\d+$", "", t)


def read_fasta(path):
    seqs, cur = {}, None
    with open(path) as fh:
        for line in fh:
            if line.startswith(">"):
                cur = line[1:].split()[0].split("||", 1)[-1]
                seqs[cur] = []
            elif cur:
                seqs[cur].append(line.strip())
    return {k: "".join(v) for k, v in seqs.items()}


def write_fasta(path, ids, seqs):
    with open(path, "w") as fh:
        for t in ids:
            fh.write(f">{SPECIES}||{t}\n{seqs[t]}\n")


def main(bundle_dir, proteome, out_dir):
    from plantseed_annotation import dispatch

    in_og = set()
    for fa in glob.glob(os.path.join(bundle_dir, "orthofinder_families", "*.fa")):
        with open(fa) as fh:
            for line in fh:
                if line.startswith(f">{SPECIES}||"):
                    in_og.add(line[1:].strip().split("||", 1)[1])

    seqs = read_fasta(proteome)
    og_genes = {gene_of(t) for t in in_og}
    rnd = random.Random(SEED)

    pool = sorted(in_og & set(seqs))
    rnd.shuffle(pool)
    non = rnd.sample(sorted(t for t in seqs if gene_of(t) not in og_genes), N_EACH)

    os.makedirs(out_dir, exist_ok=True)
    candidates = os.path.join(out_dir, "candidates.faa")
    write_fasta(candidates, pool[:N_CANDIDATES], seqs)
    genome = dispatch.annotate(candidates, bundle_dir, SPECIES, "Athaliana_TAIR10",
                               None, log=lambda m: None)
    annotated = {f["id"] for f in genome["features"]}

    by_gene = {}
    for t in pool[:N_CANDIDATES]:
        if gene_of(t) in annotated:
            by_gene.setdefault(gene_of(t), []).append(t)
    genes = rnd.sample(sorted(by_gene), N_EACH)
    pick = [sorted(by_gene[g])[0] for g in genes]

    write_fasta(os.path.join(out_dir, "poplar_test_500.faa"), pick + non, seqs)
    with open(os.path.join(out_dir, "expected_plantseed_genes.txt"), "w") as fh:
        fh.write("\n".join(sorted(genes)) + "\n")
    os.remove(candidates)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
