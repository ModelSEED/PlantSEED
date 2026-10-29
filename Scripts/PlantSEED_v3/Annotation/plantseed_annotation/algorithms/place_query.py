"""Place a query genome's proteins into the bundle's curated orthogroups.

Originally scoped (see the project plan) as a full OrthoFinder `-f -b`
insert-mode run against the enriched reference. Measured against the real
tool before building it: `-b` does not do a lightweight placement -- it
rebuilds fresh DIAMOND search databases from every reference species' ORIGINAL
sequence files, re-runs all-vs-all search including the query, and reruns the
full MCL clustering and tree-building over the WHOLE similarity graph, not
just the curated orthogroups. That needs the full per-species proteomes (not
the ~1.65 GB bundle, which only ships the pruned curated-OG alignments) and
costs minutes-to-tens-of-minutes per call, which does not fit either the
KBase refdata cap or an MCP tool call's realistic latency budget.

What this module does instead:

  1. Build (once per bundle, cached by content_id) a single DIAMOND database
     from the de-gapped sequences of every curated orthogroup already in
     `<bundle>/orthofinder_families/`. Each subject sequence is headered
     `<og_id>||<species>||<gene_id>` so the OG a hit belongs to survives
     DIAMOND's own output format with no side table.
  2. `diamond blastp` the query proteome against that one database.
  3. For each query gene, keep its single best-scoring hit's orthogroup as
     the placement (standard "best hit decides family membership" rule --
     the same first move OrthoFinder's own graph clustering makes before MCL
     ever runs on it).
  4. For every OG with >=1 placed query gene, realign the placed query
     sequences into that OG's existing alignment with
     `mafft --add --keeplength` -- adds rows without touching the existing
     columns, so the bundle's own cached PSI matrix (computed from those same
     columns) stays valid for every pair that doesn't involve the query.
  5. Compute PSI for query<->member pairs only (psi.compute_psi_for_query_members),
     NOT a full O(n^2) rescore of the whole orthogroup. The largest curated OG
     in the Sep09 reference carries 2,344 members; rescoring everyone against
     everyone took 17 minutes in earlier manual testing for a cost with no
     payoff, since none of the member-vs-member pairs are new.
  6. Emit the four structures `psi_refined.annotate_species` already
     consumes (`orthologues_dict`, `ogs`, `psi_by_og`, `sp_gene_to_og`) with
     the query folded in as an ordinary participant -- downstream code does
     not know or care that placement came from DIAMOND rather than a full
     OrthoFinder run.

IMPORTANT, and the reason the placement tag matters: DIAMOND's best-hit is
NOT OrthoFinder's reciprocal-cluster ortholog call. `psi_refined`'s O/PAM/PAH
tagging already treats "no OrthoFinder ortholog pair" as the normal case it
falls back from (see psi_refined.py's module docstring on PAH/fallback), so a
DIAMOND placement with no matching entry in `orthologues_dict` is handled
correctly by the existing machinery -- it is scored as a paralog candidate
against the per-OG baseline or the 0.5 fallback, exactly as a real OrthoFinder
run's non-reciprocal hits already are. Nothing downstream needed to change to
accommodate a DIAMOND-only placement.
"""

from __future__ import annotations

import glob
import os
import subprocess
import tempfile
from collections import defaultdict

from plantseed_core import runtime

from . import orthofinder_io as _oio
from . import psi as _psi

__all__ = [
    "DIAMOND_BIN", "MAFFT_BIN",
    "build_reference_db", "search", "best_hit_per_query_gene",
    "realign_and_score", "place",
]

#: External tool binaries. Overridable so a container or a dev machine with a
#: differently-named/versioned build still works -- same pattern as every
#: PLANTSEED_ANNOT_* path in paths.py, just for $PATH lookups instead of
#: filesystem locations.
DIAMOND_BIN = os.environ.get("PLANTSEED_ANNOT_DIAMOND_BIN", "diamond")
MAFFT_BIN = os.environ.get("PLANTSEED_ANNOT_MAFFT_BIN", "mafft")

#: diamond blastp defaults. Generous e-value and target count: the decision
#: that matters (which OG, if any) is made by best bitscore among whatever
#: comes back, and psi_refined's own hard floor (0.20 absolute PSI) is what
#: actually screens out a bad placement later -- this step only needs to not
#: miss a real hit, not to pre-filter one.
DEFAULT_EVALUE = "1e-5"
DEFAULT_MAX_TARGET_SEQS = 25


def _run(cmd, stdout_path=None):
    """subprocess.run with captured stderr folded into the exception message.

    DIAMOND and MAFFT write their real error (missing input, corrupt db,
    unreadable fasta) to stderr and exit non-zero; the default
    CalledProcessError message is just the exit code, which is useless from
    inside an MCP tool result.

    `stdout_path`, not a `stdout=` kwarg: MAFFT writes the alignment to
    stdout and its own log to stderr, and subprocess.run refuses to combine
    `capture_output` (which this needs for the stderr message above) with an
    explicit `stdout=` file handle. Redirecting via a temp path sidesteps the
    conflict without losing either stream.
    """
    result = subprocess.run(
        cmd, stdout=(open(stdout_path, "w") if stdout_path else subprocess.PIPE),
        stderr=subprocess.PIPE, text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr or ""
        raise RuntimeError(
            f"{cmd[0]} failed (exit {result.returncode}): "
            f"{' '.join(cmd)}\n--- stderr ---\n{stderr[-4000:]}"
        )
    return result


def _reference_fasta_header(og_id, gene_id):
    return f"{og_id}||{gene_id}"


def _parse_reference_header(header):
    """`<og_id>||<species>||<gene_id>` -> (og_id, gene_id_with_species_prefix).

    gene_id keeps its own `<species>||` prefix intact -- same "species stays
    part of the identity" rule orthofinder_io.split_id documents -- so the
    two-level split is on the FIRST `||` only.
    """
    og_id, _, gene_id = header.partition("||")
    return og_id, gene_id


def build_reference_db(bundle_dir, db_path=None, *, force=False, log=print):
    """Build (or reuse) the DIAMOND database for one bundle's curated families.

    Cached under `runtime.scratch_dir()`, keyed by the bundle's own
    directory path, NOT its content_id -- content_id requires reading and
    hashing the whole bundle, which is exactly the cost this cache exists to
    avoid paying on every call. A bundle rebuild changes its directory path
    (version-named, per reference.py) often enough in practice that this is
    sufficient; `force=True` rebuilds regardless.

    Returns the path to the `.dmnd` file (DIAMOND appends the extension
    itself if the given db_path doesn't already end with it).
    """
    import hashlib

    if db_path is None:
        key = hashlib.sha1(os.path.realpath(bundle_dir).encode()).hexdigest()[:16]
        cache_dir = runtime.scratch_dir(os.path.join("diamond_db", key))
        db_path = os.path.join(cache_dir, "reference")

    dmnd_path = db_path if db_path.endswith(".dmnd") else db_path + ".dmnd"
    if os.path.isfile(dmnd_path) and not force:
        log(f"[place_query] reusing DIAMOND db {dmnd_path}")
        return dmnd_path

    # Serialize concurrent builders. Measured need: three simultaneous
    # `annotate` calls against a never-before-built bundle each ran
    # `diamond makedb` into the SAME db_path at once -- one call's partial
    # write corrupted another's read of it mid-build, surfacing as a DIAMOND
    # segfault (exit -11) or "Unexpected end of input" in two of the three
    # calls. A warm cache (the common case once a bundle has been used once)
    # never hits this: the isfile() check above returns before the lock is
    # even touched. This only matters for the very first call against a
    # bundle after a container/worker restart.
    #
    # fcntl.flock rather than a lock file's mere existence: a crashed holder
    # (OOM-killed worker, etc.) releases an flock automatically when its fd
    # closes, where a bare "does this path exist" convention would leave a
    # bundle permanently wedged until someone notices and deletes it by hand.
    import fcntl

    os.makedirs(os.path.dirname(dmnd_path) or ".", exist_ok=True)
    lock_path = dmnd_path + ".build.lock"
    with open(lock_path, "w") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX)
        try:
            # Re-check now that the lock is held: the caller that built it
            # while we were waiting already did the work.
            if os.path.isfile(dmnd_path) and not force:
                log(f"[place_query] reusing DIAMOND db {dmnd_path} "
                    f"(built by a concurrent call while this one waited)")
                return dmnd_path

            families_dir = os.path.join(bundle_dir, "orthofinder_families")
            if not os.path.isdir(families_dir):
                raise FileNotFoundError(
                    f"no orthofinder_families/ under {bundle_dir} -- is this "
                    f"a plantseed-refbuild bundle?")

            fasta_fd, fasta_path = tempfile.mkstemp(suffix=".faa", prefix="plantseed_refdb_")
            n_seq = 0
            try:
                with os.fdopen(fasta_fd, "w") as out:
                    family_paths = sorted(glob.glob(os.path.join(families_dir, "*.fa")))
                    for msa_path in family_paths:
                        og_id = os.path.basename(msa_path)[:-3]
                        sequences = _oio.read_msa(msa_path)
                        for gene_id, aligned in sequences.items():
                            ungapped = aligned.replace("-", "")
                            if not ungapped:
                                continue
                            out.write(f">{_reference_fasta_header(og_id, gene_id)}\n{ungapped}\n")
                            n_seq += 1
                log(f"[place_query] building DIAMOND db from {n_seq} curated sequences")
                # Build to a private, PID-suffixed path and rename into
                # place: `diamond makedb --db X` writes X.dmnd in one shot
                # (no partial-file window for another LOCKED caller to see,
                # since they're all waiting on the same flock anyway) --
                # the rename is for crash-safety, not concurrency, in case
                # this process is killed mid-makedb.
                tmp_db_path = f"{db_path}.building.{os.getpid()}"
                _run([DIAMOND_BIN, "makedb", "--in", fasta_path, "--db", tmp_db_path])
                os.replace(f"{tmp_db_path}.dmnd", dmnd_path)
            finally:
                os.unlink(fasta_path)
        finally:
            fcntl.flock(lock_fh, fcntl.LOCK_UN)
    return dmnd_path


def search(query_fasta, dmnd_path, *, evalue=DEFAULT_EVALUE,
          max_target_seqs=DEFAULT_MAX_TARGET_SEQS, n_workers=None, log=print):
    """diamond blastp query_fasta against dmnd_path.

    Returns {query_gene: [(ref_header, pident, evalue, bitscore), ...]},
    sorted by DECREASING bitscore within each query -- `best_hit_per_query_gene`
    relies on index 0 being the best hit.
    """
    out_fd, out_path = tempfile.mkstemp(suffix=".tsv", prefix="plantseed_diamond_")
    os.close(out_fd)
    try:
        cmd = [
            DIAMOND_BIN, "blastp",
            "--query", query_fasta, "--db", dmnd_path, "--out", out_path,
            "--outfmt", "6", "qseqid", "sseqid", "pident", "evalue", "bitscore",
            "--evalue", str(evalue), "--max-target-seqs", str(max_target_seqs),
            "--quiet",
        ]
        if n_workers:
            cmd += ["--threads", str(n_workers)]
        _run(cmd)
        hits = defaultdict(list)
        with open(out_path) as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) != 5:
                    continue
                qseqid, sseqid, pident, ev, bitscore = parts
                hits[qseqid].append((sseqid, float(pident), float(ev), float(bitscore)))
    finally:
        os.unlink(out_path)
    for q in hits:
        hits[q].sort(key=lambda row: -row[3])
    log(f"[place_query] {len(hits)} query gene(s) with >=1 DIAMOND hit")
    return dict(hits)


def best_hit_per_query_gene(hits):
    """{query_gene: (og_id, ref_header)} from search()'s per-query hit lists.

    "Best hit decides orthogroup membership" -- the standard first move any
    similarity-based family assignment makes (it's also OrthoFinder's own
    first cut, before MCL refines cluster boundaries). One OG per query gene:
    a query cannot be placed in two families at once by this method, which is
    a real simplification relative to full OrthoFinder (where a gene can be a
    member of exactly one orthogroup too, for what it's worth -- OGs are a
    partition there as well).
    """
    placement = {}
    for q_gene, ranked in hits.items():
        if not ranked:
            continue
        best_header = ranked[0][0]
        og_id, ref_gene = _parse_reference_header(best_header)
        placement[q_gene] = (og_id, ref_gene)
    return placement


def _read_query_fasta(path):
    return _oio.read_msa(path) if path.endswith((".fa", ".fasta", ".faa")) else _read_plain_fasta(path)


def _read_plain_fasta(path):
    """Unaligned FASTA reader -- orthofinder_io.read_msa works fine on
    unaligned sequences too (it just joins wrapped lines), but is named and
    documented for the aligned case; this alias keeps callers honest about
    which kind of file they're handing in."""
    return _oio.read_msa(path)


def realign_and_score(query_sequences_by_og, bundle_dir, *, n_workers=None, log=print):
    """For each OG with placed query genes: mafft --add --keeplength, then
    PSI between the added query rows and the OG's existing members only.

    `query_sequences_by_og`: {og_id: {query_gene: ungapped_sequence}}.

    Returns:
      psi_rows_by_og: {og_id: [(query_gene, member_gene, id_q, id_m, psi), ...]}
      ogs_query_members: {og_id: [query_gene, ...]} -- placed query genes that
                          actually survived realignment (mafft can drop an
                          all-gap row; psi.degenerate_members screens the rest).
    """
    families_dir = os.path.join(bundle_dir, "orthofinder_families")
    psi_rows_by_og = {}
    ogs_query_members = {}

    for og_id, query_seqs in sorted(query_sequences_by_og.items()):
        msa_path = os.path.join(families_dir, f"{og_id}.fa")
        if not os.path.isfile(msa_path):
            log(f"[place_query] WARNING: {og_id} placed by DIAMOND but has no "
                f"alignment in the bundle -- skipping")
            continue

        q_fd, q_path = tempfile.mkstemp(suffix=".faa", prefix=f"plantseed_{og_id}_q_")
        try:
            with os.fdopen(q_fd, "w") as out:
                for gene_id, seq in sorted(query_seqs.items()):
                    out.write(f">{gene_id}\n{seq}\n")

            added_fd, added_path = tempfile.mkstemp(
                suffix=".fa", prefix=f"plantseed_{og_id}_added_")
            os.close(added_fd)
            try:
                cmd = [MAFFT_BIN, "--add", q_path, "--keeplength"]
                if n_workers:
                    cmd += ["--thread", str(n_workers)]
                cmd.append(msa_path)
                _run(cmd, stdout_path=added_path)
                combined = _oio.read_msa(added_path)
            finally:
                os.unlink(added_path)
        finally:
            os.unlink(q_path)

        member_genes = {g for g in combined if g not in query_seqs}
        query_genes_here = {g for g in combined if g in query_seqs}
        if not query_genes_here:
            log(f"[place_query] WARNING: {og_id} -- every placed query row "
                f"was dropped by alignment (likely all-gap)")
            continue

        member_aligned = {g: combined[g] for g in member_genes}
        query_aligned = {g: combined[g] for g in query_genes_here}
        rows = _psi.compute_psi_for_query_members(query_aligned, member_aligned)
        psi_rows_by_og[og_id] = rows
        ogs_query_members[og_id] = sorted(query_genes_here)

    return psi_rows_by_og, ogs_query_members


def place(query_fasta, bundle_dir, query_species, *, dmnd_path=None,
         evalue=DEFAULT_EVALUE, max_target_seqs=DEFAULT_MAX_TARGET_SEQS,
         n_workers=None, log=print):
    """End-to-end: query proteome -> DIAMOND placement -> realignment -> PSI.

    `query_fasta`: path to the query proteome, headers `<query_species>||<gene>`
    (same convention orthofinder_io uses everywhere else in this package --
    callers that have bare headers should prefix them before calling this).

    Returns a dict with the four structures `psi_refined.annotate_species`
    consumes, ready to merge with whatever else populates them for other
    species already in the bundle (there normally isn't any -- a bundle only
    ships curated-species alignments, so the query is usually the only
    "other" species in play):

        {
          "ogs": {og_id: {query_species: [gene, ...], <curated_species>: [...]}},
          "psi_by_og": {og_id: {(g1, g2): psi}},
          "orthologues_dict": {},   # DIAMOND makes no reciprocal ortholog
                                    # call -- see the module docstring. Always
                                    # empty; psi_refined's O/PAM/PAH logic
                                    # falls back to PAH/PRH for every pair,
                                    # which is the correct, already-tested
                                    # behaviour for "no OF ortholog exists".
          "sp_gene_to_og": {(query_species, gene): og_id, ...},
          "n_query_genes_searched": int,
          "n_query_genes_placed": int,
          "n_query_genes_scored": int,  # survived realignment
        }
    """
    if dmnd_path is None:
        dmnd_path = build_reference_db(bundle_dir, log=log)

    query_sequences = _read_query_fasta(query_fasta)
    log(f"[place_query] {len(query_sequences)} query protein(s) in {query_fasta}")

    hits = search(query_fasta, dmnd_path, evalue=evalue,
                 max_target_seqs=max_target_seqs, n_workers=n_workers, log=log)
    placement = best_hit_per_query_gene(hits)
    log(f"[place_query] {len(placement)}/{len(query_sequences)} query protein(s) "
        f"placed in a curated orthogroup")

    query_sequences_by_og = defaultdict(dict)
    for q_gene, (og_id, _ref_gene) in placement.items():
        ungapped = query_sequences.get(q_gene, "").replace("-", "")
        if ungapped:
            query_sequences_by_og[og_id][q_gene] = ungapped

    psi_rows_by_og, ogs_query_members = realign_and_score(
        query_sequences_by_og, bundle_dir, n_workers=n_workers, log=log)

    ogs = defaultdict(lambda: defaultdict(list))
    psi_by_og = {}
    sp_gene_to_og = {}
    n_scored = 0
    for og_id, rows in psi_rows_by_og.items():
        pair_map = {}
        for q_gene, m_gene, _id_q, _id_m, psi_val in rows:
            key = (q_gene, m_gene) if q_gene < m_gene else (m_gene, q_gene)
            pair_map[key] = psi_val
        psi_by_og[og_id] = pair_map

        for q_gene in ogs_query_members[og_id]:
            ogs[og_id][query_species].append(q_gene)
            sp_gene_to_og[(query_species, q_gene)] = og_id
            n_scored += 1

        member_species_genes = defaultdict(list)
        for _q, m_gene, *_rest in rows:
            spp, _bare = _oio.split_id(m_gene)
            if m_gene not in member_species_genes[spp]:
                member_species_genes[spp].append(m_gene)
        for spp, genes in member_species_genes.items():
            existing = set(ogs[og_id][spp])
            for g in genes:
                if g not in existing:
                    ogs[og_id][spp].append(g)
                    existing.add(g)

    log(f"[place_query] {n_scored} query gene(s) realigned and PSI-scored "
        f"across {len(psi_by_og)} orthogroup(s)")

    return {
        "ogs": {og: dict(per_spp) for og, per_spp in ogs.items()},
        "psi_by_og": psi_by_og,
        "orthologues_dict": {},
        "sp_gene_to_og": sp_gene_to_og,
        "n_query_genes_searched": len(query_sequences),
        "n_query_genes_placed": len(placement),
        "n_query_genes_scored": n_scored,
    }
