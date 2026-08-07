"""Read OrthoFinder result directories.

A standard OrthoFinder-2 results directory has this shape:

    Results_MonAug06/
      Orthogroups/Orthogroups.tsv             — one row per OG, one col per species
      Orthologues/                            — pairwise ortholog assignments
        Orthologues_<A>/                        (nested by species)
          <A>__v__<B>.tsv                       (one line per OG containing genes from both)
      MultipleSequenceAlignments/OG*.fa       — per-OG protein MSA (input to PSI)
      Gene_Trees/OG*_tree.txt                 — per-OG ML gene tree

We only touch the first three at annotation time. Gene trees are used later
(Phase 1d) by SHOOT-based reference enrichment.
"""

import itertools
import os


def _strip_species_prefix(gene_id, species):
    """OF cell entries in this repo carry a redundant '<species>||' prefix
    (Sam's fasta headers were built that way; see Print_JSON_Genome_to_FASTA.pl).
    Strip it so callers can compare against curated ids that don't carry the
    prefix. Genes without the prefix pass through unchanged."""
    prefix = species + "||"
    return gene_id[len(prefix):] if gene_id.startswith(prefix) else gene_id


def _strip_species_prefix_any(gene_id):
    """Strip whatever '<anything>||' prefix is present (for MSA headers,
    where the species varies per row)."""
    return gene_id.split("||", 1)[1] if "||" in gene_id else gene_id


def transcript_to_gene(tid):
    """Collapse a transcript-level id back to its gene-level id by stripping
    a trailing '.<digits>' suffix.

        'AT1G01050.1'       -> 'AT1G01050'
        'Sobic.001G234700.1' -> 'Sobic.001G234700'
        'Potri.001G067600.1' -> 'Potri.001G067600'
        'AT1G01050'         -> 'AT1G01050'         (no change)
        'Sobic.001G234700'  -> 'Sobic.001G234700'  (no change; last segment isn't digits)

    Used to match transcript-level OF ids against gene-level curated ids in
    PlantSEED_Roles.json."""
    if "." not in tid:
        return tid
    left, right = tid.rsplit(".", 1)
    return left if right.isdigit() else tid


# --- Orthogroups.tsv ---------------------------------------------------------
def load_orthogroups(orthogroups_tsv):
    """Parse Orthogroups.tsv → {og_id: {species: [gene_id, ...]}}.

    Cell entries have their redundant '<species>||' prefix stripped so
    callers can compare directly against curated gene ids.
    Species with no gene in an OG get an empty list. Splits on ', ' the way
    OrthoFinder writes multi-gene cells.
    """
    ogs = {}
    with open(orthogroups_tsv) as fh:
        header = fh.readline().rstrip("\n").split("\t")
        species = header[1:]
        for line in fh:
            row = line.rstrip("\n").split("\t")
            og_id = row[0]
            entry = {}
            for i, spp in enumerate(species):
                cell = row[i + 1] if i + 1 < len(row) else ""
                genes = [g for g in cell.split(", ") if g] if cell else []
                entry[spp] = [_strip_species_prefix(g, spp) for g in genes]
            ogs[og_id] = entry
    return ogs, species


def og_containing_gene(ogs, species, gene_id):
    """Return the og_id containing (species, gene_id), or None."""
    for og_id, entry in ogs.items():
        if gene_id in entry.get(species, []):
            return og_id
    return None


def species_gene_to_og_index(ogs):
    """Build a `{(species, gene_id): og_id}` reverse index for O(1) lookup.
    Cheaper than repeatedly calling og_containing_gene."""
    idx = {}
    for og_id, entry in ogs.items():
        for spp, genes in entry.items():
            for gene in genes:
                idx[(spp, gene)] = og_id
    return idx


# --- Orthologues/<A>__v__<B>.tsv ---------------------------------------------
def orthologues_path(results_dir, spp_a, spp_b):
    """Return the path to `Orthologues/Orthologues_<A>/<A>__v__<B>.tsv`, or
    None if the file doesn't exist."""
    candidate = os.path.join(
        results_dir, "Orthologues", f"Orthologues_{spp_a}",
        f"{spp_a}__v__{spp_b}.tsv",
    )
    return candidate if os.path.isfile(candidate) else None


def load_orthologues(orthologues_tsv):
    """Parse an `<A>__v__<B>.tsv` file.

    Each row: og_id \\t genes-in-A (', '-joined) \\t genes-in-B (', '-joined).
    Species names are taken from the header line (column 1 = species A,
    column 2 = species B); the '<species>||' prefix is stripped from every
    gene id at parse time so callers see clean ids.

    Returns two dicts, both keyed by gene id:
      {a_gene: {'og': og_id, 'orthologs': [b_gene, ...]}}
      {b_gene: {'og': og_id, 'orthologs': [a_gene, ...]}}
    """
    a_to_b = {}
    b_to_a = {}
    with open(orthologues_tsv) as fh:
        header = fh.readline().rstrip("\n").split("\t")
        spp_a = header[1] if len(header) > 1 else ""
        spp_b = header[2] if len(header) > 2 else ""
        for line in fh:
            row = line.rstrip("\n").split("\t")
            if len(row) < 3:
                continue
            og_id = row[0]
            a_genes = [_strip_species_prefix(g, spp_a)
                       for g in row[1].split(", ") if g]
            b_genes = [_strip_species_prefix(g, spp_b)
                       for g in row[2].split(", ") if g]
            for a in a_genes:
                bucket = a_to_b.setdefault(a, {"og": og_id, "orthologs": []})
                for b in b_genes:
                    if b not in bucket["orthologs"]:
                        bucket["orthologs"].append(b)
            for b in b_genes:
                bucket = b_to_a.setdefault(b, {"og": og_id, "orthologs": []})
                for a in a_genes:
                    if a not in bucket["orthologs"]:
                        bucket["orthologs"].append(a)
    return a_to_b, b_to_a


# --- MultipleSequenceAlignments/OG*.fa ---------------------------------------
def alignments_dir(results_dir):
    return os.path.join(results_dir, "MultipleSequenceAlignments")


def list_alignments(results_dir):
    """Yield (og_id, absolute_path) for each `OG*.fa` MSA."""
    ad = alignments_dir(results_dir)
    if not os.path.isdir(ad):
        return
    for name in sorted(os.listdir(ad)):
        if not name.endswith(".fa"):
            continue
        og_id = name[: -len(".fa")]
        yield og_id, os.path.join(ad, name)


def read_msa(fasta_file):
    """Parse a FASTA (MSA-style) into {gene_id: aligned_sequence}.

    Strips the redundant '<species>||' prefix from each header so lookups
    line up with Orthogroups.tsv / Orthologues/* / PSI cache."""
    sequences = {}
    with open(fasta_file) as fh:
        faiter = (x[1] for x in itertools.groupby(fh, lambda line: line[0] == ">"))
        for header in faiter:
            hdr = next(header)[1:].strip().split(None, 1)[0]
            seq = "".join(s.strip() for s in next(faiter))
            sequences[_strip_species_prefix_any(hdr)] = seq.upper()
    return sequences


# --- Species discovery -------------------------------------------------------
def species_from_orthogroups(orthogroups_tsv):
    """Return the ordered list of species in the OF run (header of Orthogroups.tsv)."""
    with open(orthogroups_tsv) as fh:
        return fh.readline().rstrip("\n").split("\t")[1:]
