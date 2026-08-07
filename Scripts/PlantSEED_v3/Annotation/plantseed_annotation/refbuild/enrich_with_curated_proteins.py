"""SHOOT-place each non-Arabidopsis PlantSEED-curated UniProt protein into
its OrthoFinder gene tree, then insert it into the corresponding OG's
fasta + MSA + tree.

This is the step that puts sorghum dhurrin enzymes, taxol-pathway
proteins, Brassica MAMs, and other non-Arabidopsis specialists into the
reference — without it, downstream genomes can never be annotated for
specialized metabolic pathways Arabidopsis lacks.

Incremental caching: only re-SHOOTs proteins whose UniProt ID + sequence
hash is new since the previous bundle version. Cached placements are
carried over from vN-1. This is what makes the Phase 6 GitHub-Action-driven
bundle rebuild fast enough to run on every merge.

Filled in at Phase 1.
"""
