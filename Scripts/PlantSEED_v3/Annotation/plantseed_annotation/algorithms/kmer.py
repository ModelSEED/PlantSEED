"""8-mer signature match — fast-path annotation, ported from ProbModelSEED's
lib/Bio/ModelSEED/ProbModelSEED/ProbModelSEEDHelper.pm::annotate_plant_genome_kmers.

Optional follow-up to the primary place_query + psi_refined + propagate
pipeline. Useful on the KBase tier when the bundle's SHOOT/OrthoFinder
data would blow the 10 GB refdata cap; the kmer index is tiny and
comfortably fits in 22 GB / 2 cores.

Kmer length = 8, threshold = 1, tie-break by top count — matches the
ProbModelSEED implementation.
"""
