"""Constants shared between the CLI, dashboard, and apply pipeline.

These mirror the dashboard's prior single-file definitions and the parser
table in Update_Enzymes_in_PlantSEED.py — kept in one place so the three
interfaces cannot drift.
"""


# Fields filled automatically by other parts of the pipeline; required-empty
# warnings should ignore them.
AUTO_POPULATED_FIELDS = {"role", "include", "type", "is_transporter", "curators"}


# ModelSEED plant compartment IDs (Plant/Compartments.tsv "id" minus the
# trailing 0). Letters skipped: h, o, p, q.
COMPARTMENTS = [
    ("a", "Carboxysome"),         ("b", "Plasma Membrane"),
    ("c", "Cytosol"),             ("d", "Stroma"),
    ("e", "Extracellular"),       ("f", "ER Membrane"),
    ("g", "Golgi"),               ("i", "Mitochondria outer membrane"),
    ("j", "Mitochondria intermembrane"), ("k", "Mitochondria inner membrane"),
    ("l", "Lysosome"),            ("m", "Mitochondria"),
    ("n", "Nucleus"),             ("r", "Endoplasmic Reticulum"),
    ("s", "Plastidial outer membrane"), ("t", "Plastidial intermembrane"),
    ("u", "Plastidial inner membrane"), ("v", "Vacuole"),
    ("w", "Cell Wall"),           ("x", "Peroxisome"),
    ("y", "Thylakoid"),           ("z", "Thylakoid Lumen"),
]
COMPARTMENT_IDS = {c for c, _ in COMPARTMENTS}
DEFAULT_COMPARTMENT = "c"
DEFAULT_LOC_SOURCE = "Assumed"


# Curator-facing action vocabulary.
ACTION_OPTIONS = ["ADD", "ASSIGN", "CHANGE", "RELOCATE", "REMOVE", "UPDATE", "NEW"]
ACTION_DESCRIPTIONS = {
    "ADD":      "Append entries to a list/dict field. For features/reactions, the extra column is optional — compartment defaults to 'c' (cytosol) with source 'Assumed'.",
    "ASSIGN":   "Set a scalar field (include, type).",
    "CHANGE":   "Set a scalar field (abstract_enzyme, include).",
    "RELOCATE": "Rekey an entry inside a dict field (localization, compartmentalization).",
    "REMOVE":   "Drop entries from a list/dict field.",
    "UPDATE":   "Rename an enzyme. Triggers a kbase_id rehash.",
    "NEW":      "Create a brand-new enzyme entry with schema defaults.",
}

# Bug fix #2: localization/classes removed from ADD — they are cascade-only
# (populated automatically from features/subsystems ADDs). Letting a curator
# ADD them directly would mis-initialize the dict-typed field as a list.
ACTION_FIELDS = {
    "ADD":      ["features", "publications", "reactions", "subsystems"],
    "ASSIGN":   ["include", "type", "subcomplex_of"],
    "CHANGE":   ["abstract_enzyme", "include"],
    "RELOCATE": ["localization", "compartmentalization"],
    "REMOVE":   ["features", "publications", "reactions", "subsystems", "localization", "classes"],
}

# Fields with an optional (or required) "extra" column on ADD rows.
MULTI_COL_FIELDS = {
    "features": {
        "primary_label":  "feature ID (e.g. Athaliana_TAIR10||AT3G30775)",
        "extra_label":    "compartment:source (e.g. c:PPDB)",
        "extra_optional": True,
        "extra_kind":     "compartment_source",
    },
    "reactions": {
        "primary_label":  "reaction ID (e.g. rxn00001)",
        "extra_label":    "compartment letter (e.g. c, p, d)",
        "extra_optional": True,
        "extra_kind":     "compartment_only",
    },
    "subsystems": {
        "primary_label":  "subsystem name (e.g. Methionine_and_cysteine_metabolism)",
        "extra_label":    "class name (e.g. Amino acids)",
        "extra_optional": False,
        "extra_kind":     "freeform",
    },
}

# Scalar fields whose curator-supplied string value needs to be coerced.
SCALAR_TYPES = {
    "include":         "bool",
    "is_transporter":  "bool",
    "type":            "str",
    "abstract_enzyme": "str",
    "subcomplex_of":   "str",
}

# Per-action minimum column count for a TSV line to parse (action included).
ACTION_MIN_COLS = {
    "UPDATE": 3, "NEW": 2, "ADD": 4, "REMOVE": 4,
    "RELOCATE": 5, "CHANGE": 4, "ASSIGN": 4,
}

TYPE_MAP = {"str": str, "bool": bool, "list": list, "dict": dict, "int": int, "float": float}

BOOL_TRUE = {"true", "t", "yes", "y", "1"}
BOOL_FALSE = {"false", "f", "no", "n", "0"}

EXIT_SHORTCUT = "!!"


def coerce_bool_str(v):
    """Map curator-typed boolean strings to canonical 'True'/'False' or None
    when the value isn't recognised."""
    s = (v or "").strip().lower()
    if s in BOOL_TRUE:
        return "True"
    if s in BOOL_FALSE:
        return "False"
    return None
