"""Compute pairwise sequence identity (PSI) from an OrthoFinder MSA.

Ported from ~/Seq_Home/PlantSEED_Processing_v2/Calculate_Pairwise_Sequence_Identity.py.

PSI for a pair of aligned sequences (X, Y) is:
    n_match  = count of positions where X[k] == Y[k] and neither is a gap
    id_x     = n_match / len(X without gaps)
    id_y     = n_match / len(Y without gaps)
    psi      = (id_x + id_y) / 2

Cached per-OG as `<cache_dir>/<OG>.txt` so a user who runs the annotator
repeatedly against the same OF results only pays the PSI cost once. File
format matches the Processing_v2 script and is location-independent:
    OG_id \\t gene1:id1 \\t gene2:id2 \\t psi

The cache used to default to `<OF_RESULTS>/Pairwise_Sequence_Identity/`, which
is a subdirectory of this module's own input. On poplar that is ordinary
writable disk; on KBase and CTS it is the refdata mount, bound read-only, so
the `makedirs` fails in exactly the two places that are hardest to re-run. See
`cache_search_path` for what replaced it — one writable directory, several
readable ones.
"""

import getpass
import hashlib
import itertools
import multiprocessing as mp
import os
import re

from plantseed_core import runtime

from . import orthofinder_io


PSI_CACHE_DIRNAME = "Pairwise_Sequence_Identity"


def _run_fingerprint(results_dir):
    """A name that identifies one OrthoFinder run's cache, and no other.

    Living inside `results_dir` scoped the cache to its run for free. A shared
    scratch root gives that up: OrthoFinder numbers orthogroups from OG0000000
    in every run, so an unscoped `<scratch>/Pairwise_Sequence_Identity` would
    hand one run's PSI values to another run's identically-named OGs — wrong
    answers, silently, with a warm cache. The user goes into the digest too,
    because `gettempdir()` is shared on a login node.
    """
    resolved = os.path.realpath(results_dir)
    try:
        user = getpass.getuser()
    except Exception:                       # no passwd entry: some containers
        user = str(getattr(os, "getuid", lambda: "nouser")())
    digest = hashlib.sha1(f"{user}\0{resolved}".encode()).hexdigest()[:8]
    base = os.path.basename(resolved.rstrip(os.sep)) or "results"
    return f"{re.sub(r'[^A-Za-z0-9._-]', '_', base)[:40]}-{digest}"


def cache_search_path(results_dir, cache_dir=None):
    """Return `(write_dir, read_dirs)` for one OrthoFinder run's PSI cache.

    `write_dir` is the only directory this module creates or writes into:
    `cache_dir` when the caller names one, otherwise a per-run subdirectory of
    `plantseed_core.runtime.scratch_dir()`. It never defaults inside
    `results_dir`, and the choice does not depend on whether `results_dir`
    happens to be writable — probing would make the behaviour differ between
    poplar and a container, which is the failure mode being removed.

    `read_dirs` is the ordered search path for an already-computed file:
    `write_dir` first, then `<results_dir>/Pairwise_Sequence_Identity/` if it
    exists. That second tier is consulted, never created. It covers the caches
    already sitting beside OrthoFinder results on poplar — which stay valid,
    since the file format carries no path — and it is the intended production
    shape, where refdata ships PSI computed once at image-build time and
    mounted read-only.

    Pure: safe to call more than once per run.
    """
    legacy = os.path.join(results_dir, PSI_CACHE_DIRNAME)
    if cache_dir:
        write_dir = os.fspath(cache_dir)
    else:
        write_dir = os.fspath(runtime.scratch_dir(
            os.path.join(PSI_CACHE_DIRNAME, _run_fingerprint(results_dir)),
            create=False,
        ))
    read_dirs = [write_dir]
    if (os.path.isdir(legacy)
            and os.path.realpath(legacy) != os.path.realpath(write_dir)):
        read_dirs.append(legacy)
    return write_dir, tuple(read_dirs)


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
    cache_path = runtime.enforce_writable(cache_path)
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

    Writes to `cache_dir` if given, otherwise to a per-run scratch directory;
    reads from that plus any prebuilt cache beside the OrthoFinder results.
    See `cache_search_path`, which decides both and which callers should use
    to get the read path for `load_psi_for_ogs`.

    `ogs` — optional set of og_ids to restrict to (skip work on the ~90 % of
    OGs that don't touch PlantSEED-curated genes).

    Returns (write_dir, {og_id: n_pairs_computed_or_cached}).
    """
    cache_dir, read_dirs = cache_search_path(results_dir, cache_dir)
    os.makedirs(cache_dir, exist_ok=True)
    already = set()
    for d in read_dirs:
        if os.path.isdir(d):
            already |= {n[:-len(".txt")] for n in os.listdir(d)
                        if n.endswith(".txt")}

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
        f"(writing to {cache_dir})")
    for d in read_dirs[1:]:
        log(f"PSI: also reading prebuilt cache at {d}")
    scratch_root = os.fspath(runtime.scratch_dir(create=False))
    if runtime.SCRATCH_ENV not in os.environ and cache_dir.startswith(scratch_root):
        log(f"PSI: this cache is under the system temp dir and is not durable "
            f"— set {runtime.SCRATCH_ENV} or --psi-cache-dir to keep it")
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


def load_psi_for_ogs(cache_dirs, og_ids):
    """Load PSI rows for every OG in `og_ids`.

    `cache_dirs` is a single directory or an ordered search path of them, as
    returned by `cache_search_path`; for each OG the first directory holding
    its file wins. Returns `{og_id: {(g1, g2): psi}}` with (g1, g2) sorted so
    lookup is order-independent."""
    if isinstance(cache_dirs, (str, bytes, os.PathLike)):
        cache_dirs = (cache_dirs,)
    out = {}
    for og_id in og_ids:
        for d in cache_dirs:
            cache_path = os.path.join(d, og_id + ".txt")
            if os.path.isfile(cache_path):
                break
        else:
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
