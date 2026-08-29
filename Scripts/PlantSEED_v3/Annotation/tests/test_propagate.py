"""propagate — curated-feature index and function-string composition."""

import pytest

from plantseed_annotation.algorithms import propagate


# --- COMPARTMENT_MAPPING coverage --------------------------------------------
def test_compartment_mapping_covers_every_real_localization_key():
    """Every localization key used in current PlantSEED_Roles.json must map
    to a template compartment name — otherwise those roles silently lose
    their compartment tag and reconstruction defaults them to cytosol.

    Enumerated from a full walk of dev's Data/PlantSEED_v3/PlantSEED_Roles.json:
        c cd ce cm cv cx d de dy e g m mj n r v w x
    """
    real_keys = {"c", "cd", "ce", "cm", "cv", "cx", "d", "de", "dy",
                 "e", "g", "m", "mj", "n", "r", "v", "w", "x"}
    missing = real_keys - set(propagate.COMPARTMENT_MAPPING)
    assert not missing, f"COMPARTMENT_MAPPING missing keys: {missing}"


# --- build_curated_features --------------------------------------------------
def _mini_role(role, features, localization):
    """Compact factory for a fake role entry."""
    return {
        "role":          role,
        "features":      features,
        "localization":  localization,
        "reactions":     ["rxn00001"],
        "subsystems":    ["S"],
        "include":       True,
    }


def test_build_curated_features_single_role_single_feature():
    roles = [_mini_role(
        "Alpha (EC 1.1.1.1)",
        ["Athaliana_TAIR10||AT1G01050"],
        {"c": {"Athaliana_TAIR10||AT1G01050": ["ref"]}},
    )]
    curated = propagate.build_curated_features(roles_data=roles)
    key = ("Athaliana_TAIR10", "AT1G01050")
    assert key in curated
    entry = curated[key]
    assert entry["roles"] == ["Alpha (EC 1.1.1.1)"]
    assert entry["compartments"] == ["c"]
    assert entry["function"] == "Alpha (EC 1.1.1.1) # cytosol"


def test_build_curated_features_two_roles_merge_on_same_feature():
    """A feature hit by two role entries collects both roles."""
    roles = [
        _mini_role("Beta", ["Athaliana_TAIR10||AT2G00010"],
                   {"c": {"Athaliana_TAIR10||AT2G00010": []}}),
        _mini_role("Alpha", ["Athaliana_TAIR10||AT2G00010"],
                   {"c": {"Athaliana_TAIR10||AT2G00010": []}}),
    ]
    curated = propagate.build_curated_features(roles_data=roles)
    entry = curated[("Athaliana_TAIR10", "AT2G00010")]
    assert entry["roles"] == ["Alpha", "Beta"]     # sorted
    assert entry["function"] == "Alpha / Beta # cytosol"


def test_build_curated_features_multi_compartment_sorted():
    """A feature in multiple compartments emits them in single-letter
    sort order — matches fetch_plantseed_impl.fetch_features."""
    roles = [_mini_role(
        "Multi",
        ["Athaliana_TAIR10||AT3G00010"],
        {
            "d": {"Athaliana_TAIR10||AT3G00010": []},
            "c": {"Athaliana_TAIR10||AT3G00010": []},
            "m": {"Athaliana_TAIR10||AT3G00010": []},
        },
    )]
    curated = propagate.build_curated_features(roles_data=roles)
    entry = curated[("Athaliana_TAIR10", "AT3G00010")]
    assert entry["compartments"] == ["c", "d", "m"]
    assert entry["function"] == "Multi # cytosol # plastid # mitochondria"


def test_build_curated_features_dy_transport_maps_to_thylakoid():
    """dy localization (thylakoid lumen transport) must appear as
    'thylakoid' in the function string — this is the regression that
    fetch_plantseed_impl and the current kb_orthofinder both had until
    now."""
    roles = [_mini_role(
        "Thylakoider",
        ["Athaliana_TAIR10||AT4G00010"],
        {"dy": {"Athaliana_TAIR10||AT4G00010": []}},
    )]
    curated = propagate.build_curated_features(roles_data=roles)
    entry = curated[("Athaliana_TAIR10", "AT4G00010")]
    assert entry["function"] == "Thylakoider # thylakoid"


def test_build_curated_features_ignores_features_not_in_localization():
    """A feature listed on a role's features list but NOT under any
    localization key gets no compartment tag."""
    roles = [_mini_role(
        "OrphanFeature",
        ["Athaliana_TAIR10||AT5G00010"],
        {},   # empty localization dict
    )]
    curated = propagate.build_curated_features(roles_data=roles)
    entry = curated[("Athaliana_TAIR10", "AT5G00010")]
    assert entry["compartments"] == []
    assert entry["function"] == "OrphanFeature"


def test_build_curated_features_parses_source_and_gene():
    """Source prefix (Species_id||) is stripped into the key's first
    element; a feature without ||-prefix produces (None, gene_id)."""
    roles = [
        _mini_role("X", ["Athaliana_TAIR10||AT1"], {"c": {"Athaliana_TAIR10||AT1": []}}),
        _mini_role("Y", ["Uniprot||Q123"],         {"c": {"Uniprot||Q123": []}}),
        _mini_role("Z", ["bare_gene"],             {"c": {"bare_gene": []}}),
    ]
    curated = propagate.build_curated_features(roles_data=roles)
    assert ("Athaliana_TAIR10", "AT1") in curated
    assert ("Uniprot", "Q123") in curated
    assert (None, "bare_gene") in curated


# --- curated_features_by_source_species --------------------------------------
def test_group_by_source_species():
    roles = [
        _mini_role("A", ["Athaliana_TAIR10||AT1"], {"c": {"Athaliana_TAIR10||AT1": []}}),
        _mini_role("B", ["Sbicolor_v3.1.1||Sob1"], {"c": {"Sbicolor_v3.1.1||Sob1": []}}),
    ]
    curated = propagate.build_curated_features(roles_data=roles)
    by_spp = propagate.curated_features_by_source_species(curated)
    assert set(by_spp) == {"Athaliana_TAIR10", "Sbicolor_v3.1.1"}
    assert set(by_spp["Athaliana_TAIR10"]) == {"AT1"}
    assert set(by_spp["Sbicolor_v3.1.1"]) == {"Sob1"}


# --- function_for_ortholog ---------------------------------------------------
def test_function_for_ortholog_hit_and_miss():
    curated = {
        ("Athaliana_TAIR10", "AT1"): {"function": "Alpha # cytosol"},
    }
    assert propagate.function_for_ortholog(
        ("Athaliana_TAIR10", "AT1"), curated) == "Alpha # cytosol"
    assert propagate.function_for_ortholog(
        ("Athaliana_TAIR10", "MISSING"), curated) is None


# --- merge_functions (FIX_AMBHIT_ROLE_UNION_260812) --------------------------
def _e(roles, cpts):
    """Compact factory for a curated-feature-entry shape merge_functions expects."""
    return {"roles": list(roles), "compartments": list(cpts)}


def test_merge_functions_identical_role_sets_union_compartments():
    """Two entries with identical role sets merge cleanly. Compartments are
    the union so a cytosolic and a plastidial copy of the same enzyme
    together document both localisations."""
    merged = propagate.merge_functions([
        _e(["Alpha (EC 1.1.1.1)"], ["c"]),
        _e(["Alpha (EC 1.1.1.1)"], ["d"]),
    ])
    assert merged is not None
    fn, roles, cpts = merged
    assert roles == ["Alpha (EC 1.1.1.1)"]
    assert cpts == ["c", "d"]                # sorted union
    assert fn == "Alpha (EC 1.1.1.1) # cytosol # plastid"


def test_merge_functions_identical_role_sets_and_compartments_are_idempotent():
    """Two identical entries collapse to that entry (compartments un-duplicated)."""
    e = _e(["R1"], ["c"])
    merged = propagate.merge_functions([e, e])
    assert merged is not None
    fn, roles, cpts = merged
    assert roles == ["R1"]
    assert cpts == ["c"]
    assert fn == "R1 # cytosol"


def test_merge_functions_nested_role_sets_merges_on_intersection():
    """Nested case: one entry's roles are exactly the shared roles. Merge
    keeps only the intersection so the tie can't introduce a role (and
    therefore a reaction) that only one candidate carried."""
    merged = propagate.merge_functions([
        _e(["BCAA aminotransferase"], ["d"]),
        _e(["BCAA aminotransferase", "MAM (EC 2.6.1.-)"], ["d"]),
    ])
    assert merged is not None
    fn, roles, cpts = merged
    assert roles == ["BCAA aminotransferase"]   # intersection only
    assert "MAM" not in fn


def test_merge_functions_conflicting_role_sets_returns_none():
    """Two entries with disjoint role sets have no meaningful shared enzyme;
    the caller must fall back to AMB_HIT."""
    merged = propagate.merge_functions([
        _e(["Alpha (EC 1.1.1.1)"], ["c"]),
        _e(["Beta (EC 2.2.2.2)"],  ["d"]),
    ])
    assert merged is None


def test_merge_functions_overlapping_but_neither_nested_returns_none():
    """Neither {A, B} is a superset of the other (they overlap on A);
    intersection isn't equal to any entry's role set, so bail out."""
    merged = propagate.merge_functions([
        _e(["A", "B"], ["c"]),
        _e(["A", "C"], ["c"]),
    ])
    assert merged is None


def test_merge_functions_empty_role_set_returns_none():
    """Entry with no roles (rare — usually uncurated) can't participate."""
    merged = propagate.merge_functions([
        _e([], ["c"]),
        _e(["R1"], ["c"]),
    ])
    assert merged is None
    merged = propagate.merge_functions([])
    assert merged is None


def test_merge_functions_three_way_identical_role_sets():
    """Three entries all with the same role set — merges, compartments unioned."""
    merged = propagate.merge_functions([
        _e(["Alpha (EC 1.1.1.1)"], ["c"]),
        _e(["Alpha (EC 1.1.1.1)"], ["d"]),
        _e(["Alpha (EC 1.1.1.1)"], ["m"]),
    ])
    assert merged is not None
    fn, roles, cpts = merged
    assert roles == ["Alpha (EC 1.1.1.1)"]
    assert cpts == ["c", "d", "m"]


def test_merge_functions_three_way_nested_requires_intersection_to_be_a_role_set():
    """Rule 2 admits nested only when one entry IS the intersection.
    {A} + {A, B} + {A, C}: intersection = {A}, but no entry equals {A}."""
    merged = propagate.merge_functions([
        _e(["A", "B"], ["c"]),
        _e(["A", "C"], ["c"]),
    ])
    assert merged is None

    # Add a plain {A} entry — now the intersection {A} matches an entry.
    merged = propagate.merge_functions([
        _e(["A", "B"], ["c"]),
        _e(["A", "C"], ["c"]),
        _e(["A"],      ["c"]),
    ])
    assert merged is not None
    fn, roles, _ = merged
    assert roles == ["A"]


# --- compartment-name dedupe in _compose_function_string ---------------------
def test_compose_function_string_dedupes_compartment_names():
    """COMPARTMENT_MAPPING is many-to-one — e.g. `d` and `cd` both -> `plastid`.
    _compose_function_string dedupes so a merge_functions union doesn't
    produce `# plastid # plastid`."""
    # `d` and `cd` both map to `plastid`; result should contain plastid once.
    out = propagate._compose_function_string(["R1"], ["cd", "d"])
    assert out == "R1 # plastid"
    # `m` and `cm` both map to `mitochondria`; `c` maps to `cytosol`.
    out = propagate._compose_function_string(["R1"], ["c", "cm", "m"])
    assert out == "R1 # cytosol # mitochondria"
