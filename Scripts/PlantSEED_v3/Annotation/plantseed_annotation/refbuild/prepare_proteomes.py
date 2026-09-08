"""Prepare Phytozome proteomes for OrthoFinder, with recoverable identifiers.

Run OrthoFinder with `-X` on the output of this, and every downstream file
names a sequence `<species>||<transcript>` — parseable by splitting once on
`||`, from any tool, forever.

**Why this exists.** OrthoFinder without `-X` prepends the species itself, in
`orthologues.py`, by joining with `_` after rewriting every `.`:

    >CreinhardtiiCC_4532_707_v6_1_protein_Cre16.g651400_4532.1.p

There is no parse for that. The species name, the strain number and the gene
id are all `_`-separated and the original dots are gone, so you cannot tell
where one ends and the next begins — and for a genome whose gene ids are bare
integers there is not even a heuristic. The 2021 reference run did not have
this problem because its inputs were already prefixed; the convention was lost
when the 2025 run switched to raw Phytozome files.

**Why `||` and not something else.** Measured, not assumed: muscle 5.3,
iqtree2 2.4.0 and MAFFT 7.525 all round-trip it unchanged, iqtree2 including
inside the Newick treefile. `|` is absent from OrthoFinder's own
`_ILEGAL_NEWICK_CHARS`, and Phytozome, NCBI and UniProt accessions do not
contain it. EPA-ng is the one tool in the SHOOT path still unverified.

The characters OrthoFinder *does* destroy, for reference, are `: ; , ( ) [ ]
= .` and whitespace, across `util.py`, `newick.py` and `orthologues.py` — so a
separator drawn from that set would be silently rewritten.
"""

from __future__ import annotations

import os
import re

from ..algorithms.orthofinder_io import normalise_species

__all__ = ["SEPARATOR", "locus_of", "prepare_one", "prepare"]

SEPARATOR = "||"

#: Phytozome puts the gene this transcript belongs to in the header.
_LOCUS = re.compile(r"\blocus=(\S+)")


def locus_of(record_id, header=""):
    """The gene a transcript belongs to.

    Prefers Phytozome's `locus=` field, which is authoritative. Falling back to
    stripping a trailing `.<digits>` (optionally `.p`) is a guess that is right
    for Phytozome and Araport and wrong for anything whose ids merely end in a
    number — which is why the header is consulted first.
    """
    found = _LOCUS.search(header)
    if found:
        return found.group(1)
    base = record_id[:-2] if record_id.endswith(".p") else record_id
    left, _, right = base.rpartition(".")
    return left if right.isdigit() and left else record_id


def _records(path):
    """(record_id, full header line, [sequence lines]) in file order."""
    rid, header, seq = None, None, []
    with open(path) as fh:
        for line in fh:
            if line.startswith(">"):
                if rid is not None:
                    yield rid, header, seq
                header = line.rstrip("\n")
                rid = header[1:].split(None, 1)[0] if len(header) > 1 else ""
                seq = []
            elif rid is not None:
                seq.append(line)
    if rid is not None:
        yield rid, header, seq


def prepare_one(src, dest, species=None, primary_only=False, log=print) -> dict:
    """Rewrite one proteome's headers to `<species>||<transcript>`.

    Sequence lines are copied verbatim — only the header changes — so the
    output diffs cleanly against the input and the residues are provably
    untouched.
    """
    species = species or normalise_species(os.path.basename(src))
    if SEPARATOR in species:
        raise ValueError(f"species name {species!r} contains {SEPARATOR!r}, "
                         "which would make the header ambiguous")

    kept, seen, dropped = [], set(), 0
    best_by_locus: dict[str, int] = {}
    for rid, header, seq in _records(src):
        if SEPARATOR in rid:
            raise ValueError(
                f"{src}: sequence id {rid!r} already contains {SEPARATOR!r}; "
                "refusing to produce a header that cannot be split")
        if rid in seen:
            raise ValueError(f"{src}: duplicate sequence id {rid!r}")
        seen.add(rid)
        entry = (rid, seq)
        if not primary_only:
            kept.append(entry)
            continue
        # Longest sequence wins the locus. Ties go to the first seen, so the
        # choice does not depend on dict or filesystem ordering.
        key = locus_of(rid, header)
        length = sum(len(l.strip()) for l in seq)
        prev = best_by_locus.get(key)
        if prev is None:
            best_by_locus[key] = len(kept)
            kept.append(entry)
        elif length > sum(len(l.strip()) for l in kept[prev][1]):
            kept[prev] = entry
            dropped += 1
        else:
            dropped += 1

    with open(dest, "w") as out:
        for rid, seq in kept:
            out.write(f">{species}{SEPARATOR}{rid}\n")
            out.writelines(seq)

    log(f"[prep] {species:<34} {len(kept):>7} sequences"
        + (f"  ({dropped} non-primary dropped)" if primary_only else ""))
    return {"species": species, "sequences": len(kept), "dropped": dropped,
            "source": src, "dest": dest}


def prepare(src_dir, dest_dir, primary_only=False, log=print) -> dict:
    """Prepare every proteome in `src_dir` into `dest_dir`.

    `primary_only` keeps the longest transcript per locus. Off by default
    because it changes what OrthoFinder clusters, but worth considering: the
    2025 reference mixes conventions badly — 14 of its 21 proteomes carry all
    isoforms and 7 carry one per locus, ranging from 1.00 to 3.33 sequences
    per locus. That inconsistency weights the per-species-pair PSI mean by
    annotation style rather than by biology.
    """
    os.makedirs(dest_dir, exist_ok=True)
    sources = sorted(f for f in os.listdir(src_dir)
                     if f.endswith((".fa", ".fasta", ".faa")))
    if not sources:
        raise FileNotFoundError(f"no FASTA files in {src_dir}")

    reports, species_seen = [], {}
    for name in sources:
        report = prepare_one(os.path.join(src_dir, name),
                             os.path.join(dest_dir, name),
                             primary_only=primary_only, log=log)
        clash = species_seen.get(report["species"])
        if clash:
            raise ValueError(
                f"{name} and {clash} both normalise to species "
                f"{report['species']!r} — OrthoFinder would treat them as one")
        species_seen[report["species"]] = name
        reports.append(report)

    total = sum(r["sequences"] for r in reports)
    log(f"[prep] {len(reports)} proteomes, {total} sequences -> {dest_dir}")
    log(f"[prep] run OrthoFinder on this directory WITH -X, or it will "
        f"prefix the species a second time")
    return {"dest_dir": dest_dir, "proteomes": len(reports),
            "sequences": total, "primary_only": primary_only,
            "reports": reports}
