"""Genome format adapters.

Two shapes the annotator has to accept and emit:

  - KBase `KBaseGenomes.Genome` object (dict-of-dicts JSON with features,
    mrnas, cdss arrays and protein_translation on each). What the SDK App
    wrapper hands in and the reconstructor consumes.

  - Standalone protein FASTA (what poplar celery gets from a website upload
    or a local user runs from a checkout).

genome_io.load() returns a normalized {feature_id: protein_seq} dict;
genome_io.write_annotations() writes annotations back into the source
shape (feature['functions'] arrays for KBase Genome; a `.functions.tsv`
sidecar for standalone FASTA).
"""
