"""Build the curated-feature index from PlantSEED_Roles.json and turn a
top-ortholog record into an annotated-genome function string.

Ported from
    plantseed-v3/kb_orthofinder/lib/kb_orthofinder/core/fetch_plantseed_impl.py
into a standalone library callable that consumes the on-dev
`Data/PlantSEED_v3/PlantSEED_Roles.json` and produces the SAME
`role [ / role]* [# compartment]*` string contract that
`plantseed_model.reconstruct` and
`plant_fba.reconstruct_plant_metabolism` both consume today.
"""

import json

from .. import paths


# Compartment-code -> compartment-name mapping, mirroring the table in
# kb_orthofinder/core/fetch_plantseed_impl.py. Keys are the localization
# keys used in PlantSEED_Roles.json; values are the compartment 'name'
# strings the reconstructor expects.
COMPARTMENT_MAPPING = {
    "c":  "cytosol",
    "g":  "golgi",
    "w":  "cellwall",
    "n":  "nucleus",
    "r":  "endoplasm",
    "v":  "vacuole",
    "cv": "vacuole",
    "d":  "plastid",
    "cd": "plastid",
    "m":  "mitochondria",
    "cm": "mitochondria",
    "mj": "mitointer",
    "ce": "extracellular",
    "x":  "peroxisome",
    "cx": "peroxisome",
    "e":  "extracellular",
    "de": "plastid",
    "dy": "thylakoid",   # 43 role occurrences on dev — resolves via
                         # Transport_Compartment_Rules.yaml (`y` wins over `d`)
    "y":  "thylakoid",   # defensive; not currently used as a single-letter
                         # localization key in PlantSEED_Roles.json
}


def _parse_feature(feature_str):
    """PlantSEED_Roles feature strings are 'Species_id||gene_id' or
    just 'gene_id'. Return (species_or_None, gene_id)."""
    if "||" in feature_str:
        src, gid = feature_str.split("||", 1)
        return src, gid
    return None, feature_str


def build_curated_features(roles_data=None, include_uncurated=False):
    """Walk PlantSEED_Roles.json and return the curated-feature index.

    Shape:
        {
          (species, gene_id): {
              "roles":        [role_name, ...],       # sorted alphabetically
              "compartments": [compartment_key, ...], # sorted by single-letter id
              "function":     "role1 / role2 # cytosol # plastid",
          },
          ...
        }

    `roles_data` — optional pre-loaded list of role dicts; otherwise
    reads `paths.ROLES_FILE`.

    `include_uncurated` — if True, roles with `include: false` are still
    walked (matches the behaviour of fetch_plantseed_impl.fetch_features:
    the include filter is commented out on the roles side, so we mirror
    that today).
    """
    if roles_data is None:
        with open(paths.ROLES_FILE) as fh:
            roles_data = json.load(fh)

    per_feature = {}   # (species, gene) -> {'roles': [], 'compartments': []}
    for entry in roles_data:
        if not include_uncurated and entry.get("include") is False:
            pass  # fetch_plantseed_impl.fetch_features has this filter
                  # commented out today; leave the same behavior here.
        for feat_str in entry.get("features", []):
            key = _parse_feature(feat_str)
            bucket = per_feature.setdefault(
                key, {"roles": [], "compartments": []}
            )
            role_name = entry["role"]
            if role_name not in bucket["roles"]:
                bucket["roles"].append(role_name)
            # The compartment for this feature is the localization key
            # under which this feature appears in the role's localization dict.
            for cpt, cpt_features in entry.get("localization", {}).items():
                if isinstance(cpt_features, dict):
                    feature_list = list(cpt_features.keys())
                else:
                    feature_list = list(cpt_features)
                if feat_str in feature_list and cpt not in bucket["compartments"]:
                    bucket["compartments"].append(cpt)

    # Compose the final function string per feature.
    for key, data in per_feature.items():
        data["roles"] = sorted(data["roles"])
        data["compartments"] = sorted(data["compartments"])
        data["function"] = _compose_function_string(
            data["roles"], data["compartments"]
        )
    return per_feature


def _compose_function_string(sorted_roles, sorted_compartments):
    """`role1 / role2 # cpt-name1 # cpt-name2` — matches
    fetch_plantseed_impl.fetch_features's output. Unknown compartment
    keys are dropped silently after a stderr warning.

    Compartment NAMES are de-duped in append order because COMPARTMENT_MAPPING
    is many-to-one (`d` and `cd` both map to `plastid`, `m`/`cm` to
    `mitochondria`, `x`/`cx` to `peroxisome`, …). Direct callers pass in
    keys from a single feature and won't ever hit a duplicate today, but
    merge_functions() unions compartment lists across tied ortholog hits,
    where duplicates ARE reachable.
    """
    import sys
    role_str = " / ".join(sorted_roles)
    if not sorted_compartments:
        return role_str
    mapped = []
    for cpt in sorted_compartments:
        if cpt not in COMPARTMENT_MAPPING:
            print(f"WARNING: no compartment mapping for {cpt!r}", file=sys.stderr)
            continue
        name = COMPARTMENT_MAPPING[cpt]
        if name not in mapped:
            mapped.append(name)
    if not mapped:
        return role_str
    return role_str + " # " + " # ".join(mapped)


def merge_functions(feature_entries):
    """Merge curated-feature entries whose genes tied at the same PSI.

    Returns `(function_string, roles, compartments)` when the entries
    describe the same enzyme, or None when their role sets genuinely
    conflict.

    Two rules, both conservative:
      * identical role sets  -> merge, roles unchanged
      * nested role sets     -> merge on the INTERSECTION of the roles, so a
                                tie can never introduce a role (and therefore
                                a reaction) that only one candidate carried

    Compartments are always the UNION across the merged entries: a gene that
    is an equally good ortholog of a plastidial and a cytosolic copy of the
    same enzyme is evidence for both localisations, not for neither.

    Replaces the composed-string tie-break in psi_refined.annotate_query_gene
    that was porting kb_orthofinderImpl.propagate_annotation's substring
    comparison. See FIX_AMBHIT_ROLE_UNION_260812.md.
    """
    role_sets = [frozenset(e.get("roles") or ()) for e in feature_entries]
    if not role_sets or not all(role_sets):
        return None

    shared = frozenset.intersection(*role_sets)
    if len(set(role_sets)) != 1:
        # Nested case only: some entry must contribute exactly the shared roles.
        if not shared or not any(rs == shared for rs in role_sets):
            return None

    roles = sorted(shared)
    compartments = sorted({c for e in feature_entries
                           for c in (e.get("compartments") or ())})
    return _compose_function_string(roles, compartments), roles, compartments


def function_for_ortholog(top_ortholog, curated_features):
    """Look up the function string that should be propagated from
    `top_ortholog` (a (species, gene_id) tuple) to a query gene.

    Returns None if the ortholog isn't in the curated set."""
    return (curated_features.get(top_ortholog) or {}).get("function")


def curated_features_by_source_species(curated_features):
    """Group the curated feature index by source species.

    Returns `{species: {gene_id: feature_data}}` so callers can quickly
    check 'do we have any curated feature in species X?' without walking
    the full 1666-entry index every time."""
    by_spp = {}
    for (spp, gid), data in curated_features.items():
        by_spp.setdefault(spp, {})[gid] = data
    return by_spp
