"""Build a SHOOT database from the baseline OrthoFinder run.

**Deferred to the end of the refactor.** Together with
`enrich_with_curated_proteins` this is what turns a v0 bundle into v1; see
`refbuild/__init__.py` for why that moved after the annotator rather than
before it.

Not blocked on anything but sequencing: SHOOT is GPL-3 and the KBase apps are
MIT, but everything involved is open source and the two are kept apart simply
by invoking SHOOT as a subprocess rather than importing it -- which is also
how kb_orthofinder already treats OrthoFinder.

When it lands: `create_shoot_db.py ... full`, then `bifurcating_trees.py` for
EPA-ng compatibility. Records its build id in the manifest's
`sources.shoot_db_build_id`, which is empty in a v0 bundle.
"""
