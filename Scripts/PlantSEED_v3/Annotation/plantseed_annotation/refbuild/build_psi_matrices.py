"""Per-orthogroup pairwise sequence identity for the bundle.

The computation itself already exists and is tested — `algorithms.psi` is the
port of Processing_v2's `Calculate_Pairwise_Sequence_Identity.py`, and it is
what the annotator reads at run time. This module is the refbuild side of the
same thing: run it over the pruned orthogroups and land the results inside the
bundle rather than in a scratch cache.

Reusing `ensure_psi_cache` rather than re-implementing matters beyond saving
code. The cache format is the annotator's read format; a second writer would
be a second definition of it, and the first divergence would show up as
subtly wrong identities rather than as an error.
"""

from __future__ import annotations

import os
import shutil

from ..algorithms import psi
from . import bundle

__all__ = ["build"]


def build(results_dir, bundle_dir, og_ids, n_workers=None, log=print) -> dict:
    """Write `<bundle_dir>/psi_matrices/<OG>.txt` for each id in `og_ids`.

    Returns a summary dict for the manifest. `og_ids` is taken as given —
    pruning is `prune.curated_orthogroups`, and keeping the two separate means
    a bundle can be rebuilt for a subset without re-deciding the selection.
    """
    out_dir = os.path.join(bundle.ensure_layout(bundle_dir), bundle.PSI_DIR)
    wanted = set(og_ids)
    log(f"[psi] {len(wanted)} orthogroups -> {out_dir}")

    # cache_dir is explicit, so this writes into the bundle rather than the
    # per-run scratch directory ensure_psi_cache defaults to.
    cache_dir, stats = psi.ensure_psi_cache(
        results_dir, cache_dir=out_dir, ogs=wanted, n_workers=n_workers, log=log,
    )
    # The same search path ensure_psi_cache used, so "where could a prebuilt
    # matrix be" is answered once, by psi, rather than guessed at here.
    _write_dir, read_dirs = psi.cache_search_path(results_dir, out_dir)

    # A bundle must be self-contained: it gets rsynced to KBase refdata and
    # mounted somewhere the OrthoFinder run does not exist. ensure_psi_cache
    # legitimately treats a prebuilt cache beside the run as a hit and computes
    # nothing -- correct for annotating in place, and it would leave the bundle
    # with an empty psi_matrices/. So adopt those files rather than point at
    # them. Copied byte-for-byte, so the bundle ships the reference's own
    # computation rather than our re-derivation of it.
    adopted = 0
    for og_id in sorted(wanted):
        target = os.path.join(out_dir, og_id + ".txt")
        if os.path.exists(target):
            continue
        for source_dir in read_dirs:
            candidate = os.path.join(source_dir, og_id + ".txt")
            if source_dir != out_dir and os.path.isfile(candidate):
                shutil.copyfile(candidate, target)
                adopted += 1
                break
    if adopted:
        log(f"[psi] adopted {adopted} prebuilt matrices into the bundle")

    written = sorted(n[:-4] for n in os.listdir(out_dir) if n.endswith(".txt"))
    missing = sorted(wanted - set(written))
    if missing:
        # Selected from Orthogroups.tsv but with neither an alignment to
        # compute from nor a prebuilt matrix to adopt: the run is incomplete.
        # Say so rather than shipping a bundle with holes.
        log(f"[psi] WARNING: {len(missing)} selected orthogroups have no PSI "
            f"and no alignment; first few: {missing[:5]}")
    return {
        "psi_dir": cache_dir,
        "og_requested": len(wanted),
        "og_written": len(written),
        "og_adopted": adopted,
        "og_missing": len(missing),
        "pairs_computed": sum(v for v in stats.values() if v),
    }
