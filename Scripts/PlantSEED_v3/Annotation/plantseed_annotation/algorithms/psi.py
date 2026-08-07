"""Compute pairwise sequence identity (PSI) from an OrthoFinder MSA.

Ported from ~/Seq_Home/PlantSEED_Processing_v2/Calculate_Pairwise_Sequence_Identity.py.

PSI for a pair of aligned sequences (X, Y) is:
    n_match  = count of positions where X[k] == Y[k] and neither is a gap
    id_x     = n_match / len(X without gaps)
    id_y     = n_match / len(Y without gaps)
    psi      = (id_x + id_y) / 2

Cached per-OG under `<OF_RESULTS>/Pairwise_Sequence_Identity/<OG>.txt` so a
user who runs the annotator repeatedly against the same OF results only pays
the PSI cost once. File format matches the Processing_v2 script:
    OG_id \\t gene1:id1 \\t gene2:id2 \\t psi
"""

import itertools
import multiprocessing as mp
import os

from . import orthofinder_io


PSI_CACHE_DIRNAME = "Pairwise_Sequence_Identity"


def _fmt(x):
    return f"{x:.2f}"


def compute_psi_for_msa(sequences):
    """Compute PSI for every pair in `sequences` (a {gene_id: aligned_seq} dict).

    Returns a list of tuples (gene1, gene2, id1, id2, psi) with the standard
    sort order used by the cache (gene1 < gene2)."""
    features = sorted(sequences.keys())
    out = []
    for i in range(len(features) - 1):
        seq_i = sequences[features[i]]
        for j in range(i + 1, len(features)):
            seq_j = sequences[features[j]]
            n_match = 0
            for k in range(len(seq_i)):
                a, b = seq_i[k], seq_j[k]
                if a == "-" or b == "-":
                    continue
                if a == b:
                    n_match += 1
            len_i = len(seq_i) - seq_i.count("-")
            len_j = len(seq_j) - seq_j.count("-")
            id_i = (n_match / len_i) if len_i > 0 else 0.0
            id_j = (n_match / len_j) if len_j > 0 else 0.0
            psi = (id_i + id_j) / 2.0
            out.append((features[i], features[j], id_i, id_j, psi))
    return out


def write_cache_file(cache_path, og_id, rows):
    """Write one cached PSI file. Format matches
    Processing_v2's Calculate_Pairwise_Sequence_Identity.py:

        <og_id>\\t<g1>:<id1>\\t<g2>:<id2>\\t<psi>\\n
    """
    with open(cache_path, "w") as fh:
        for (g1, g2, id1, id2, psi) in rows:
            fh.write("\t".join([og_id, f"{g1}:{_fmt(id1)}",
                                f"{g2}:{_fmt(id2)}", _fmt(psi)]) + "\n")


def read_cache_file(cache_path):
    """Load one cached PSI file → list of (gene1, gene2, id1, id2, psi)."""
    rows = []
    with open(cache_path) as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            _og, a_field, b_field, psi_s = parts[0], parts[1], parts[2], parts[3]
            g1, id1 = a_field.rsplit(":", 1)
            g2, id2 = b_field.rsplit(":", 1)
            rows.append((g1, g2, float(id1), float(id2), float(psi_s)))
    return rows


def _worker(args):
    og_id, msa_path, cache_path = args
    sequences = orthofinder_io.read_msa(msa_path)
    rows = compute_psi_for_msa(sequences)
    write_cache_file(cache_path, og_id, rows)
    return og_id, len(rows)


def ensure_psi_cache(results_dir, cache_dir=None, ogs=None,
                    n_workers=None, log=print):
    """Compute PSI for every OG MSA in `results_dir` that isn't already cached.

    Cache defaults to `<results_dir>/Pairwise_Sequence_Identity/`. Pass
    `cache_dir` to place it elsewhere (useful when results_dir is read-only,
    e.g., NFS-mounted refdata).

    `ogs` — optional set of og_ids to restrict to (skip work on the ~90 % of
    OGs that don't touch PlantSEED-curated genes).

    Returns (cache_dir, {og_id: n_pairs_computed_or_cached}).
    """
    cache_dir = cache_dir or os.path.join(results_dir, PSI_CACHE_DIRNAME)
    os.makedirs(cache_dir, exist_ok=True)
    already = {n[:-len(".txt")] for n in os.listdir(cache_dir) if n.endswith(".txt")}

    todo = []
    kept_from_cache = {}
    for og_id, msa_path in orthofinder_io.list_alignments(results_dir):
        if ogs is not None and og_id not in ogs:
            continue
        cache_path = os.path.join(cache_dir, og_id + ".txt")
        if og_id in already:
            kept_from_cache[og_id] = None
            continue
        todo.append((og_id, msa_path, cache_path))

    log(f"PSI: {len(kept_from_cache)} cached, {len(todo)} to compute "
        f"(cache dir: {cache_dir})")
    if not todo:
        return cache_dir, {og: 0 for og in kept_from_cache}

    n_workers = n_workers or max(1, (os.cpu_count() or 2) - 1)
    log(f"PSI: computing with {n_workers} workers")

    computed = {}
    if n_workers == 1:
        for args in todo:
            og_id, n = _worker(args)
            computed[og_id] = n
    else:
        with mp.Pool(n_workers) as pool:
            for og_id, n in pool.imap_unordered(_worker, todo, chunksize=32):
                computed[og_id] = n
    result = {og: 0 for og in kept_from_cache}
    result.update(computed)
    return cache_dir, result


def load_psi_for_ogs(cache_dir, og_ids):
    """Load PSI rows for every OG in `og_ids`.

    Returns `{og_id: {(g1, g2): psi}}` with (g1, g2) sorted so lookup is
    order-independent."""
    out = {}
    for og_id in og_ids:
        cache_path = os.path.join(cache_dir, og_id + ".txt")
        if not os.path.isfile(cache_path):
            continue
        pair_psi = {}
        for (g1, g2, _id1, _id2, psi) in read_cache_file(cache_path):
            key = (g1, g2) if g1 < g2 else (g2, g1)
            pair_psi[key] = psi
        out[og_id] = pair_psi
    return out


def psi_lookup(psi_by_og, og_id, gene_a, gene_b):
    """Return the cached PSI for (gene_a, gene_b) in og_id, or None."""
    key = (gene_a, gene_b) if gene_a < gene_b else (gene_b, gene_a)
    return psi_by_og.get(og_id, {}).get(key)
