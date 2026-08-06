"""Serialize a per-feature annotation to both the legacy string contract
and the new stable-ID form.

Legacy string (consumed by unchanged plant_fba.reconstruct_plant_metabolism
during the migration):
    `<role1> / <role2> # <compartment1> # <compartment2>`

Stable IDs (consumed by v2 reconstructor):
    ["PS_role_abc123", "PS_role_def456"]

The bundle's curation/ subdir provides the string <-> id mapping so both
forms can be emitted from a single top-ortholog record.
"""
