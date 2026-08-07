"""Turn the OrthoFinder results directory into a SHOOT database.

Wraps SHOOT's own tools:
    python create_shoot_db.py RESULTS_DIRECTORY full
    python bifurcating_trees.py RESULTS_DIRECTORY   # for EPA-ng compat

Output: `<BUNDLE_DIR>/shoot_db/`, ready for `shoot INPUT_FASTA SHOOT_DB`
(consumed by enrich_with_curated_proteins).

SHOOT deps: ete3, sklearn, biopython, DIAMOND, MAFFT, EPA-ng + gappa
(or IQ-TREE as substitute). See github.com/davidemms/SHOOT.

Filled in at Phase 1.
"""
