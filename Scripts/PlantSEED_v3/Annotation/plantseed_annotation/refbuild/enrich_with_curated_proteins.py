"""SHOOT-place each non-Arabidopsis curated protein into its orthogroup.

**Deferred to the end of the refactor** -- see `refbuild/__init__.py`.

This is what puts sorghum dhurrin enzymes, taxol-pathway proteins and
Brassica MAMs into the reference, so a query genome can be annotated for
specialized pathways Arabidopsis does not have. It is the scientifically
interesting half of the bundle and it presumes the ordinary half works first.

Scope, from the current curation: **32 features** across the two spellings
`UniProt` (16) and `Uniprot` (16) in PlantSEED_Roles.json. Every other
curated feature is already in the reference run. That is a much smaller job
than "enrich the reference" suggests, and worth knowing before it is
scheduled.

Design notes carried forward: place with `shoot INPUT_FASTA SHOOT_DB`, insert
into the orthogroup's fasta + MSA + tree, and cache placements by UniProt id
plus sequence hash so a rebuild only re-places what changed. Each placed
protein gets a `curated_non_arabidopsis` entry in the manifest -- an array
that a v0 bundle carries as empty rather than absent, precisely so this step
is visible by its absence.
"""
