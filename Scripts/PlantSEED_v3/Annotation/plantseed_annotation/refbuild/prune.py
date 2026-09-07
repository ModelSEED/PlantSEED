"""Choose which orthogroups the bundle keeps.

The full OrthoFinder run over 15 Phytozome species is 31,196 orthogroups; the
KBase tier allows 10 GB of refdata for the whole tool. Almost all of that is
orthogroups no curated PlantSEED role touches, and the annotator never reads
them: propagation starts from a curated gene and walks outward, so an
orthogroup with no curated member can never produce an annotation.

Selection is therefore "does this orthogroup contain a curated gene, in any
species". Any species matters — the curation deliberately includes sorghum
dhurrin, taxol-pathway and Brassica MAM proteins precisely because
Arabidopsis lacks those pathways, and keying on Arabidopsis alone would prune
away the specialized metabolism the reference exists to carry.

Output is sorted and deduplicated so the bundle is byte-reproducible; see
`bundle`.
"""

from __future__ import annotations

import os

from ..algorithms import orthofinder_io, propagate

__all__ = ["curated_orthogroups", "prune_report", "write_families"]


def curated_orthogroups(ogs, curated_features=None, species=None):
    """Sorted list of OG ids containing at least one curated gene.

    `ogs` — as returned by `orthofinder_io.load_orthogroups`.
    `curated_features` — the index from `propagate.build_curated_features`;
    read from `paths.ROLES_FILE` when omitted.
    `species` — optional restriction to one species, for a targeted run. The
    default of "any species" is the one a bundle wants.

    Orthogroups.tsv cells are transcript ids and the curation is gene-level,
    so each transcript is normalised with `transcript_to_gene` before lookup;
    matching them raw silently finds nothing for species whose transcripts
    carry a `.1` suffix.
    """
    if curated_features is None:
        curated_features = propagate.build_curated_features()
    by_species = propagate.curated_features_by_source_species(curated_features)
    if species is not None:
        by_species = {species: by_species.get(species, {})}

    to_gene = orthofinder_io.transcript_to_gene
    selected = set()
    for (spp, transcript_id), og_id in orthofinder_io.species_gene_to_og_index(ogs).items():
        genes = by_species.get(spp)
        if genes and to_gene(transcript_id) in genes:
            selected.add(og_id)
    return sorted(selected)


def prune_report(ogs, selected) -> dict:
    """What the pruning kept and dropped, for the manifest and the log.

    Worth recording rather than just counting: a bundle that suddenly keeps
    half as many orthogroups has almost certainly lost a species prefix
    somewhere, and the ratio is the cheapest place to notice.
    """
    total = len(ogs)
    kept = len(selected)
    return {
        "og_total": total,
        "og_kept": kept,
        "og_dropped": total - kept,
        "kept_fraction": round(kept / total, 4) if total else 0.0,
    }


def write_families(results_dir, bundle_dir, og_ids, log=print) -> dict:
    """Copy the selected orthogroups' alignments into the bundle.

    Copied, not symlinked: the bundle is rsynced to KBase refdata and mounted
    read-only in two containers, and a symlink into someone's OrthoFinder
    output directory resolves to nothing on the other side of that.

    Byte-for-byte, via shutil.copyfile rather than re-serialising the fasta,
    so the family files in the bundle hash to the same thing as their source
    and a rebuild is checkably identical.
    """
    import shutil

    from . import bundle as _bundle

    out_dir = os.path.join(_bundle.ensure_layout(bundle_dir), _bundle.FAMILIES_DIR)
    wanted = set(og_ids)
    seen = set()
    for og_id, msa_path in sorted(orthofinder_io.list_alignments(results_dir)):
        if og_id not in wanted:
            continue
        shutil.copyfile(msa_path, os.path.join(out_dir, os.path.basename(msa_path)))
        seen.add(og_id)
    missing = sorted(wanted - seen)
    if missing:
        log(f"[families] WARNING: {len(missing)} selected orthogroups have no "
            f"alignment on disk; first few: {missing[:5]}")
    log(f"[families] copied {len(seen)} alignments -> {out_dir}")
    return {"families_dir": out_dir, "copied": len(seen), "missing": len(missing)}
