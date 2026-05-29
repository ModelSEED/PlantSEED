#!/usr/bin/env python3
"""
PlantSEED Curation Tool — Web Dashboard
=======================================
Single-file web replacement for the interactive CLIs:
  - Curation_Tool.py             (produces TSV curation rows)
  - Update_Enzymes_in_PlantSEED.py (applies TSV rows to PlantSEED_Roles.json)

Run with nothing more than Python installed:
    python3 Curation_Tool_Dashboard.py

PyYAML is the only third-party dependency and is auto-installed on first run.
Use Ctrl-C to stop.

CLI flags:
  --host 0.0.0.0   listen on all interfaces (default 127.0.0.1)
  --port 9000      specific port (default 8765, auto-fallback if taken)
  --no-browser     don't open a browser tab
"""

import os
import sys
import subprocess


# --- Lightweight bootstrap: auto-install PyYAML if missing -------------------
# Sam Seaver's constraint: the dashboard should work for anyone with just Python
# installed. PyYAML is the only third-party module; install it on first run.
def _bootstrap_pyyaml():
    try:
        import yaml  # noqa: F401
        return
    except ImportError:
        pass
    print("PyYAML not found — installing for your user (one-time setup)...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--user", "--quiet", "pyyaml"]
        )
    except Exception as e:
        print(f"\nAutomatic install failed: {e}")
        print("Please run:  pip install --user pyyaml")
        sys.exit(1)
    try:
        import yaml  # noqa: F401
    except ImportError:
        print("PyYAML installed but still not importable — please restart Python.")
        sys.exit(1)
_bootstrap_pyyaml()


import argparse
import copy
import hashlib
import html
import json
import re
import socket
import socketserver
import ssl
import tempfile
import threading
import traceback
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler

import yaml


# ----------------------------------------------------------------------------
# Paths and constants
# ----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROLES_FILE = os.path.normpath(os.path.join(
    BASE_DIR, "..", "..", "..", "Data", "PlantSEED_v3", "PlantSEED_Roles.json"
))
SCHEMA_FILE = os.path.join(BASE_DIR, "PlantSEED_Schema.yaml")
CURATORS_DIR = os.path.join(BASE_DIR, "Curators")
CURATOR_REGISTRY = os.path.join(CURATORS_DIR, "curator_registry.json")
ENZYME_DAT_URL = "https://ftp.expasy.org/databases/enzyme/enzyme.dat"
ENZYME_DAT_CACHE = os.path.join(tempfile.gettempdir(), "plantseed_enzyme.dat")

AUTO_POPULATED_FIELDS = {"role", "include", "type", "is_transporter", "curators"}

# ModelSEED plant compartments (Plant/Compartments.tsv "id" minus the trailing 0).
# Used both as a legend and to validate the localization extra column.
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
DEFAULT_LOC_SOURCE  = "Assumed"

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
ACTION_FIELDS = {
    "ADD":      ["features", "publications", "reactions", "subsystems", "localization", "classes"],
    "ASSIGN":   ["include", "type"],
    "CHANGE":   ["abstract_enzyme", "include"],
    "RELOCATE": ["localization", "compartmentalization"],
    "REMOVE":   ["features", "publications", "reactions", "subsystems", "localization", "classes"],
}
# Per Sam: extras for features/reactions are OPTIONAL. The Update script defaults
# missing compartments to 'c' (cytosol) and warns. Subsystems still need a class.
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

SCALAR_TYPES = {
    "include":         "bool",
    "is_transporter":  "bool",
    "type":            "str",
    "abstract_enzyme": "str",
}

ACTION_MIN_COLS = {
    "UPDATE": 3, "NEW": 2, "ADD": 4, "REMOVE": 4,
    "RELOCATE": 5, "CHANGE": 4, "ASSIGN": 4,
}
TYPE_MAP = {"str": str, "bool": bool, "list": list, "dict": dict, "int": int, "float": float}


# ----------------------------------------------------------------------------
# Helper utilities
# ----------------------------------------------------------------------------
def sanitize_filename(name):
    name = os.path.basename(name or "")
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def sanitize_username(name):
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def _run(cmd, timeout=5):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def get_git_username():
    r = _run(["git", "config", "user.name"])
    return r.stdout.strip() if (r and r.returncode == 0 and r.stdout.strip()) else ""


def get_git_email():
    r = _run(["git", "config", "user.email"])
    return r.stdout.strip() if (r and r.returncode == 0 and r.stdout.strip()) else ""


def get_gh_username_gh():
    r = _run(["gh", "api", "user", "--jq", ".login"])
    return r.stdout.strip().lower() if (r and r.returncode == 0 and r.stdout.strip()) else None


def get_gh_username_from_remote():
    r = _run(["git", "remote", "get-url", "origin"])
    if r and r.returncode == 0:
        m = re.search(r"(?:git@github\.com:|https?://github\.com/)([^/@]+)/", r.stdout.strip())
        if m:
            return m.group(1).lower()
    return None


def load_curator_registry():
    if os.path.exists(CURATOR_REGISTRY):
        try:
            with open(CURATOR_REGISTRY) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_curator_registry(registry):
    os.makedirs(CURATORS_DIR, exist_ok=True)
    atomic_write(CURATOR_REGISTRY, json.dumps(registry, indent=2))


def detect_github_username(display_name):
    """Return {"username": str, "source": str, "candidates": [...]}.
    Source-of-truth precedence: saved registry by email → gh CLI → git remote →
    git user.name sanitized."""
    email = get_git_email()
    registry = load_curator_registry()
    candidates = []  # (label, value)
    if email:
        for gh_user, info in registry.items():
            if info.get("github_email") == email:
                candidates.append(("registry", gh_user))
                break
    gh_user = get_gh_username_gh()
    if gh_user:
        candidates.append(("gh CLI", gh_user))
    gh_user = get_gh_username_from_remote()
    if gh_user:
        candidates.append(("git remote", gh_user))
    fallback = sanitize_username(display_name) or "user"
    candidates.append(("git user.name", fallback))
    return {
        "username": candidates[0][1],
        "source":   candidates[0][0],
        "candidates": [{"source": s, "value": v} for s, v in candidates],
    }


def normalize_existing_dirname(username):
    if os.path.isdir(CURATORS_DIR):
        for d in os.listdir(CURATORS_DIR):
            dp = os.path.join(CURATORS_DIR, d)
            if (os.path.isdir(dp) and d.lower() == username.lower()
                    and d.lower() != "curators"):
                return d
    return username


def confirm_curator_registry(username, display_name, email):
    registry = load_curator_registry()
    if username and username not in registry:
        registry[username] = {"display_name": display_name or "", "github_email": email or ""}
        save_curator_registry(registry)


def atomic_write(path, content):
    """Write to <path>.tmp then os.replace — never leaves a half-written file."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(content)
    os.replace(tmp, path)


# ----------------------------------------------------------------------------
# DataStore — thread-safe in-memory cache
# ----------------------------------------------------------------------------
class DataStore:
    def __init__(self):
        self.lock = threading.RLock()
        self.roles = []
        self.roles_mtime = None
        self.schema_raw = {}
        self.schema_normalized = {}
        self.ec_entries = []
        self.ec_status = "idle"
        self.ec_error = ""
        self.role_index = {}
        self.facet_subsystems = []
        self.facet_types = []
        self.facet_curators = []

    def load_roles(self, force=False):
        with self.lock:
            try:
                mtime = os.path.getmtime(ROLES_FILE)
            except OSError:
                return
            if force or self.roles_mtime != mtime:
                with open(ROLES_FILE) as f:
                    self.roles = json.load(f)
                self.roles_mtime = mtime
                self._reindex()

    def _reindex(self):
        self.role_index = {r["role"]: r for r in self.roles}
        subs, types, curators = set(), set(), set()
        for r in self.roles:
            for s in r.get("subsystems", []) or []:
                subs.add(s)
            t = r.get("type")
            if t:
                types.add(t)
            for cu in r.get("curators", []) or []:
                curators.add(cu)
        self.facet_subsystems = sorted(subs)
        self.facet_types      = sorted(types)
        self.facet_curators   = sorted(curators)

    def load_schema(self):
        with self.lock:
            if self.schema_normalized:
                return
            if not os.path.exists(SCHEMA_FILE):
                return
            with open(SCHEMA_FILE) as f:
                self.schema_raw = yaml.safe_load(f) or {}
            normalized = {}
            for key, rules in self.schema_raw.items():
                normalized[key] = {
                    "type":       TYPE_MAP.get(rules.get("type"), str),
                    "type_name":  rules.get("type"),
                    "default":    rules.get("default"),
                    "required":   rules.get("required", False),
                    "depends_on": rules.get("depends_on"),
                }
            self.schema_normalized = normalized

    def find_role(self, name):
        with self.lock:
            r = self.role_index.get(name)
            return copy.deepcopy(r) if r else None

    def all_roles_summary(self):
        with self.lock:
            out = []
            for r in self.roles:
                out.append({
                    "role":         r.get("role"),
                    "type":         r.get("type", ""),
                    "include":      r.get("include", True),
                    "n_features":   len(r.get("features", []) or []),
                    "n_reactions":  len(r.get("reactions", []) or []),
                    "subsystems":   list(r.get("subsystems", []) or [])[:3],
                    "curators":     list(r.get("curators", []) or []),
                    "is_transporter": r.get("is_transporter", False),
                })
            return out

    def facets(self):
        with self.lock:
            return {
                "subsystems": self.facet_subsystems,
                "types":      self.facet_types,
                "curators":   self.facet_curators,
            }

    def start_load_expasy(self):
        with self.lock:
            if self.ec_status in ("loading", "loaded"):
                return
            self.ec_status = "loading"
        threading.Thread(target=self._load_expasy_thread, daemon=True).start()

    def _load_expasy_thread(self):
        try:
            entries = fetch_enzyme_dat()
            with self.lock:
                self.ec_entries = entries
                self.ec_status = "loaded" if entries else "error"
                self.ec_error = "" if entries else "no entries parsed"
        except Exception as e:
            with self.lock:
                self.ec_status = "error"
                self.ec_error = str(e)

    def expasy_status(self):
        with self.lock:
            return {"status": self.ec_status, "count": len(self.ec_entries),
                    "error": self.ec_error}


def fetch_enzyme_dat():
    if not os.path.exists(ENZYME_DAT_CACHE) or os.path.getsize(ENZYME_DAT_CACHE) == 0:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(ENZYME_DAT_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=60) as response, \
                open(ENZYME_DAT_CACHE, "wb") as out_file:
            out_file.write(response.read())
    entries = []
    with open(ENZYME_DAT_CACHE, encoding="latin-1") as f:
        text = f.read()
    for block in text.split("\n//\n"):
        ec_id = ""
        de_lines = []
        for line in block.strip().split("\n"):
            if line.startswith("ID   "):
                ec_id = line[5:].strip()
            elif line.startswith("DE   "):
                de_lines.append(line[5:].strip())
        if ec_id and de_lines:
            de_full = " ".join(de_lines)
            if de_full:
                de_full = de_full[0].upper() + de_full[1:]
            de_full = de_full.rstrip(".")
            entries.append({"label": f"{de_full} (EC {ec_id})", "ec": ec_id})
    return entries


# ----------------------------------------------------------------------------
# Search: ranked, no result cap, field-prefix queries, and feature-substring.
# ----------------------------------------------------------------------------
FIELD_PREFIXES = {
    "ec":         {"role_field": None, "match": "ec"},
    "feature":    {"role_field": "features"},
    "feat":       {"role_field": "features"},
    "rxn":        {"role_field": "reactions"},
    "reaction":   {"role_field": "reactions"},
    "subsystem":  {"role_field": "subsystems"},
    "sub":        {"role_field": "subsystems"},
    "class":      {"role_field": "classes_keys"},
    "curator":    {"role_field": "curators"},
    "type":       {"role_field": "type_scalar"},
}


def parse_query(q):
    q = (q or "").strip()
    if ":" in q:
        head, _, tail = q.partition(":")
        head = head.strip().lower()
        if head in FIELD_PREFIXES:
            return "field", head, tail.strip()
    return "name", None, q


def _score_name(role_name, q_lower):
    rn = role_name.lower()
    if rn == q_lower: return 1000
    if rn.startswith(q_lower): return 700
    for token in re.split(r"[^A-Za-z0-9]+", rn):
        if token.startswith(q_lower):
            return 500
    if q_lower in rn: return 300
    return 0


def search_features(store, q_lower, exclude_roles):
    """Roles whose features substring-match the query. Returns [(role, matched_feature), ...]"""
    out, seen = [], set()
    for r in store.roles:
        role = r.get("role")
        if role in exclude_roles or role in seen:
            continue
        feats = r.get("features", []) or []
        if not isinstance(feats, list):
            continue
        for f in feats:
            if q_lower in str(f).lower():
                seen.add(role)
                out.append((role, str(f)))
                break
    return out


def ranked_search(store, query):
    mode, field, value = parse_query(query)
    if not value or (mode == "name" and len(value) < 2):
        return {"name": [], "expasy": [], "by_feature": [],
                "totals": {"name": 0, "expasy": 0, "by_feature": 0},
                "mode": mode, "field": field, "expasy_status": store.expasy_status()["status"]}

    q_lower = value.lower()
    name_matches, ec_matches = [], []

    with store.lock:
        if mode == "name":
            for r in store.roles:
                s = _score_name(r["role"], q_lower)
                if s:
                    name_matches.append((s - len(r["role"]) / 100, r["role"]))
            if store.ec_status == "loaded":
                for e in store.ec_entries:
                    s = _score_name(e["label"], q_lower)
                    if re.match(r"^[0-9.\-]+$", q_lower) and q_lower in e["ec"]:
                        s = max(s, 800 if e["ec"].startswith(q_lower) else 500)
                    if s:
                        ec_matches.append((s - len(e["label"]) / 100, e["label"]))

        elif mode == "field":
            cfg = FIELD_PREFIXES[field]
            rf = cfg.get("role_field")
            ec_field = cfg.get("match") == "ec"
            for r in store.roles:
                if ec_field:
                    if q_lower in r["role"].lower():
                        name_matches.append((400, r["role"]))
                    continue
                if rf == "type_scalar":
                    if q_lower in (r.get("type", "") or "").lower():
                        name_matches.append((400, r["role"]))
                    continue
                if rf == "classes_keys":
                    for k in (r.get("classes") or {}).keys():
                        if q_lower in k.lower():
                            name_matches.append((400, r["role"]))
                            break
                    continue
                items = r.get(rf, []) or []
                if isinstance(items, list):
                    for item in items:
                        if q_lower in str(item).lower():
                            name_matches.append((400, r["role"]))
                            break
                elif isinstance(items, dict):
                    for k in items.keys():
                        if q_lower in str(k).lower():
                            name_matches.append((400, r["role"]))
                            break
            if ec_field and store.ec_status == "loaded":
                for e in store.ec_entries:
                    if q_lower in e["ec"].lower():
                        ec_matches.append((900 if e["ec"].startswith(q_lower) else 400,
                                           e["label"]))

    name_matches.sort(key=lambda t: -t[0])
    ec_matches.sort(key=lambda t: -t[0])
    name_only = [n for _, n in name_matches]
    ec_only   = [n for _, n in ec_matches]

    # Always also run a feature-substring search for plain-text queries
    # (Sam's request: a gene ID like AT3G30775 should surface its roles).
    by_feature_pairs = []
    if mode == "name":
        by_feature_pairs = search_features(store, q_lower, exclude_roles=set(name_only))

    return {
        "name":       name_only,
        "expasy":     ec_only,
        "by_feature": [{"role": r, "feature": f} for r, f in by_feature_pairs],
        "totals": {
            "name":       len(name_only),
            "expasy":     len(ec_only),
            "by_feature": len(by_feature_pairs),
        },
        "mode":          mode,
        "field":         field,
        "expasy_status": store.expasy_status()["status"],
    }


# ----------------------------------------------------------------------------
# Cross-reference helpers
# ----------------------------------------------------------------------------
def find_exact_match(full_roles, field, value, exclude=None):
    out = []
    for entry in full_roles:
        role = entry.get("role")
        if role == exclude: continue
        items = entry.get(field, [])
        if isinstance(items, list) and value in items: out.append(role)
        elif isinstance(items, dict) and value in items: out.append(role)
    return out


def find_substring_match(full_roles, field, substring, exclude=None):
    out = []
    t = (substring or "").lower()
    for entry in full_roles:
        role = entry.get("role")
        if role == exclude: continue
        items = entry.get(field, [])
        if isinstance(items, list):
            for item in items:
                if t in str(item).lower():
                    out.append(role); break
        elif isinstance(items, dict):
            for item in items.keys():
                if t in str(item).lower():
                    out.append(role); break
    return out


# ----------------------------------------------------------------------------
# Validation + TSV row construction.
# Per Sam: localization extras for features/reactions are OPTIONAL. We surface
# warnings (not errors) when they're empty.
# ----------------------------------------------------------------------------
BOOL_TRUE  = {"true",  "t", "yes", "y", "1"}
BOOL_FALSE = {"false", "f", "no",  "n", "0"}


def _coerce_bool_str(v):
    s = (v or "").strip().lower()
    if s in BOOL_TRUE:  return "True"
    if s in BOOL_FALSE: return "False"
    return None


def validate_payload(action, enzyme, payload, store):
    errors, warnings = [], []
    if not enzyme or not enzyme.strip():
        return [{"field": "enzyme", "message": "Enzyme name is required"}], warnings
    action = action.upper()
    if action not in ACTION_OPTIONS:
        return [{"field": "action", "message": f"Unknown action '{action}'"}], warnings

    if action == "NEW":
        if enzyme in store.role_index:
            errors.append({"field": "enzyme",
                "message": f"'{enzyme}' already exists — choose UPDATE or pick a different name"})
        return errors, warnings

    if action == "UPDATE":
        new_name = (payload.get("new_name") or "").strip()
        if not new_name:
            errors.append({"field": "new_name", "message": "New enzyme name is required"})
        elif new_name == enzyme:
            warnings.append("UPDATE: new name is identical to current name")
        elif new_name in store.role_index:
            errors.append({"field": "new_name",
                "message": f"'{new_name}' already exists in the database"})
        if enzyme not in store.role_index:
            warnings.append(f"UPDATE: '{enzyme}' is not in the current database — the row will be skipped on apply")
        return errors, warnings

    field = (payload.get("field") or "").strip()
    if not field:
        return [{"field": "field", "message": "Field is required"}], warnings
    if action in ACTION_FIELDS and field not in ACTION_FIELDS[action]:
        return [{"field": "field",
            "message": f"{action} field '{field}' is not valid (allowed: {', '.join(ACTION_FIELDS[action])})"}], warnings

    role_entry = store.role_index.get(enzyme)

    if action == "ADD":
        entries = payload.get("entries") or []
        if not entries:
            errors.append({"field": "entries", "message": "At least one entry is required"})
        for i, entry in enumerate(entries):
            value = (entry.get("value") or "").strip()
            extra = (entry.get("extra") or "").strip()
            if not value:
                errors.append({"field": f"entries[{i}].value", "message": "Empty entry"})
                continue
            cfg = MULTI_COL_FIELDS.get(field)
            if cfg:
                if not extra:
                    if not cfg.get("extra_optional", True):
                        errors.append({"field": f"entries[{i}].extra",
                            "message": f"Extra is required ({cfg['extra_label']})"})
                    elif cfg["extra_kind"] in ("compartment_source", "compartment_only"):
                        warnings.append(
                            f"ADD {field} '{value}': no localization given — compartment "
                            f"will be assumed '{DEFAULT_COMPARTMENT}' (cytosol) on apply"
                        )
                elif cfg["extra_kind"] == "compartment_source":
                    if ":" not in extra:
                        errors.append({"field": f"entries[{i}].extra",
                            "message": f"Expected 'compartment:source' (e.g. c:PPDB). Got '{extra}'"})
                    else:
                        cpt = extra.split(":", 1)[0]
                        if cpt not in COMPARTMENT_IDS:
                            errors.append({"field": f"entries[{i}].extra",
                                "message": f"'{cpt}' is not a known ModelSEED plant compartment"})
                elif cfg["extra_kind"] == "compartment_only":
                    if extra not in COMPARTMENT_IDS:
                        errors.append({"field": f"entries[{i}].extra",
                            "message": f"'{extra}' is not a known compartment letter"})
            if role_entry:
                existing = role_entry.get(field, [])
                if isinstance(existing, list) and value in existing:
                    warnings.append(f"ADD {field}: '{value}' is already on this role (will be a no-op)")
                elif isinstance(existing, dict) and value in existing:
                    warnings.append(f"ADD {field}: '{value}' is already on this role (will be a no-op)")
        return errors, warnings

    if action == "REMOVE":
        entries = payload.get("entries") or []
        if not entries:
            errors.append({"field": "entries", "message": "At least one entry is required"})
        for i, entry in enumerate(entries):
            value = (entry.get("value") or "").strip()
            if not value:
                errors.append({"field": f"entries[{i}].value", "message": "Empty entry"})
                continue
            if role_entry:
                existing = role_entry.get(field, [])
                present = (isinstance(existing, list) and value in existing) or \
                          (isinstance(existing, dict) and value in existing)
                if not present:
                    warnings.append(f"REMOVE {field}: '{value}' is not currently on this role")
        return errors, warnings

    if action == "RELOCATE":
        old = (payload.get("old") or "").strip()
        new = (payload.get("new") or "").strip()
        if not old: errors.append({"field": "old", "message": "Old key is required"})
        if not new: errors.append({"field": "new", "message": "New key is required"})
        if old and new and old == new:
            errors.append({"field": "new", "message": "Old and new keys are identical"})
        if role_entry and old:
            existing = role_entry.get(field, {})
            if isinstance(existing, dict) and old not in existing:
                warnings.append(f"RELOCATE {field}: '{old}' is not currently a key in this role")
        return errors, warnings

    if action in ("CHANGE", "ASSIGN"):
        value = (payload.get("value") or "").strip()
        if not value:
            return [{"field": "value", "message": "Value is required"}], warnings
        if SCALAR_TYPES.get(field) == "bool":
            if _coerce_bool_str(value) is None:
                errors.append({"field": "value",
                    "message": f"'{field}' must be a boolean (true/false/yes/no)"})
        return errors, warnings

    return errors, warnings


def build_tsv_rows(action, enzyme, payload, store):
    errors_struct, warnings = validate_payload(action, enzyme, payload, store)
    if errors_struct:
        return [], errors_struct, warnings
    rows = []
    action = action.upper()
    if action == "NEW":
        rows.append(f"{enzyme}\tNEW")
    elif action == "UPDATE":
        rows.append(f"{enzyme}\tUPDATE\t{(payload['new_name'] or '').strip()}")
    elif action == "ADD":
        field = payload["field"]
        for entry in payload["entries"]:
            value = (entry.get("value") or "").strip()
            extra = (entry.get("extra") or "").strip()
            if extra:
                rows.append(f"{enzyme}\tADD\t{field}\t{value}\t{extra}")
            else:
                rows.append(f"{enzyme}\tADD\t{field}\t{value}")
    elif action == "REMOVE":
        field = payload["field"]
        for entry in payload["entries"]:
            value = (entry.get("value") or "").strip()
            rows.append(f"{enzyme}\tREMOVE\t{field}\t{value}")
    elif action == "RELOCATE":
        field = payload["field"]
        rows.append(f"{enzyme}\tRELOCATE\t{field}\t{payload['old'].strip()}\t{payload['new'].strip()}")
    elif action in ("CHANGE", "ASSIGN"):
        field = payload["field"]
        value = (payload["value"] or "").strip()
        if SCALAR_TYPES.get(field) == "bool":
            coerced = _coerce_bool_str(value)
            if coerced is not None:
                value = coerced
        rows.append(f"{enzyme}\t{action}\t{field}\t{value}")
    return rows, [], warnings


def required_empty_fields(role_entry, schema):
    out = []
    if not schema or not role_entry: return out
    for field, rules in schema.items():
        if not rules["required"] or field in AUTO_POPULATED_FIELDS: continue
        actual = role_entry.get(field)
        default = rules["default"]
        if isinstance(default, (list, dict)) and actual == default:
            out.append(field)
        elif isinstance(default, str) and actual == default == "":
            out.append(field)
    return out


# ============================================================================
# Apply pipeline — in-process equivalent of Update_Enzymes_in_PlantSEED.py.
# Mirrors Sam's defaulting: when features/reactions have no extra,
# compartment falls back to 'c' (cytosol) with source 'Assumed' and a warning.
# ============================================================================
class IssueCollector:
    def __init__(self):
        self.warnings, self.errors, self.info = [], [], []
    def warn(self, m):  self.warnings.append(m)
    def error(self, m): self.errors.append(m)
    def log(self, m):   self.info.append(m)


def parse_tsv_text(text, schema=None, issues=None):
    actions = {"replace": {}, "new": [], "add": {}, "rem": {}, "key": {}, "change": {}, "assign": {}}
    def _check_field(field, lineno):
        if schema is not None and field not in schema and issues is not None:
            issues.warn(f"line {lineno}: field '{field}' is not in the schema — proceeding anyway")
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip("\r\n")
        if line.startswith("#") or not line.strip(): continue
        tmp_lst = line.split("\t")
        if len(tmp_lst) < 2:
            if issues is not None:
                hint = " — looks space-separated; columns must be TAB-separated" if len(line.split()) > 1 else ""
                issues.warn(f"line {lineno}: fewer than 2 columns{hint} — skipped")
            continue
        enzyme = tmp_lst[0]
        action = tmp_lst[1].upper()
        if action not in ACTION_MIN_COLS:
            if issues is not None: issues.warn(f"line {lineno}: unknown action '{tmp_lst[1]}' — skipped")
            continue
        if len(tmp_lst) < ACTION_MIN_COLS[action]:
            if issues is not None:
                issues.warn(f"line {lineno}: action {action} requires at least "
                            f"{ACTION_MIN_COLS[action]} columns, got {len(tmp_lst)} — skipped")
            continue
        if action == "UPDATE":
            actions["replace"][enzyme] = tmp_lst[2]
        elif action == "NEW":
            actions["new"].append(enzyme)
            if issues is not None: issues.log(f"NEW enzyme queued: {enzyme}")
        elif action == "ADD":
            field, entry = tmp_lst[2], tmp_lst[3]
            _check_field(field, lineno)
            actions["add"].setdefault(enzyme, {}).setdefault(field, {})
            actions["add"][enzyme][field][entry] = 1
            if len(tmp_lst) > 4:
                actions["add"][enzyme][field][tmp_lst[3]] = tmp_lst[4]
        elif action == "REMOVE":
            field, entry = tmp_lst[2], tmp_lst[3]
            _check_field(field, lineno)
            actions["rem"].setdefault(enzyme, {}).setdefault(field, []).append(entry)
        elif action == "RELOCATE":
            field, entry, new_entry = tmp_lst[2], tmp_lst[3], tmp_lst[4]
            _check_field(field, lineno)
            actions["key"].setdefault(enzyme, {}).setdefault(field, {})[entry] = new_entry
        elif action == "CHANGE":
            field, entry = tmp_lst[2], tmp_lst[3]
            _check_field(field, lineno)
            actions["change"].setdefault(enzyme, {})[field] = entry
        elif action == "ASSIGN":
            field, entry = tmp_lst[2], tmp_lst[3]
            _check_field(field, lineno)
            actions["assign"].setdefault(enzyme, {})[field] = entry
    return actions


def default_role_from_schema(schema):
    return {k: copy.deepcopy(rules["default"])
            for k, rules in schema.items() if rules["required"]}


def seed_new_entries(roles_list, new_list, schema, actions=None, issues=None):
    existing = {entry["role"] for entry in roles_list}
    collisions = [new for new in new_list if new in existing]
    if collisions:
        for c in collisions:
            if issues is not None: issues.error(f"NEW role already present in database: '{c}'")
        return False
    for new in new_list:
        new_role = default_role_from_schema(schema)
        new_role["role"] = new
        new_role["abstract_enzyme"] = new.split(" (EC")[0]
        explicit_abstract = actions is not None and (
            "abstract_enzyme" in actions.get("change", {}).get(new, {})
            or "abstract_enzyme" in actions.get("assign", {}).get(new, {})
        )
        if not explicit_abstract and issues is not None:
            issues.warn(
                f"NEW role '{new}': abstract_enzyme not provided — defaulting to "
                f"'{new_role['abstract_enzyme']}'. Set it explicitly with ASSIGN if a different value is wanted."
            )
        roles_list.append(new_role)
    return True


def apply_actions(roles_list, actions, curator, issues=None):
    replace_dict = actions["replace"]
    add_dict     = actions["add"]
    rem_dict     = actions["rem"]
    key_dict     = actions["key"]
    change_dict  = actions["change"]
    assign_dict  = actions["assign"]
    touched, rename_map = set(), {}

    def coerce_value(field, val):
        if SCALAR_TYPES.get(field) == "bool":
            s = str(val).strip().lower()
            if s in BOOL_TRUE:  return True
            if s in BOOL_FALSE: return False
        return val

    for entry in roles_list:
        updated_role = False

        if entry["role"] in replace_dict:
            old_name = entry["role"]
            entry["role"] = replace_dict[old_name]
            rename_map[old_name] = entry["role"]
            updated_role = True

        if entry["role"] in add_dict:
            for field in add_dict[entry["role"]]:
                if field not in entry:
                    entry[field] = []
                for input_value in add_dict[entry["role"]][field]:
                    if isinstance(entry[field], list) and input_value not in entry[field]:
                        entry[field].append(input_value)

                    if field == "features":
                        raw = add_dict[entry["role"]][field][input_value]
                        if raw == 1:
                            # Sam: default missing localization to compartment 'c'.
                            cpt, code = DEFAULT_COMPARTMENT, DEFAULT_LOC_SOURCE
                            issues and issues.warn(
                                f"feature '{input_value}' on '{entry['role']}': "
                                f"no localization — defaulted to '{cpt}:{code}'")
                            entry.setdefault("localization", {})
                            if cpt in entry["localization"]:
                                entry["localization"][cpt][input_value] = [code]
                            else:
                                entry["localization"][cpt] = {input_value: [code]}
                        elif ":" not in str(raw):
                            issues and issues.warn(
                                f"feature '{input_value}' for role '{entry['role']}': "
                                f"localization '{raw}' missing ':' (expected 'compartment:source-code')"
                            )
                        else:
                            cpt, code = str(raw).split(":", 1)
                            entry.setdefault("localization", {})
                            if cpt in entry["localization"]:
                                entry["localization"][cpt][input_value] = [code]
                            else:
                                entry["localization"][cpt] = {input_value: [code]}

                    if field == "subsystems":
                        sys_cls = add_dict[entry["role"]][field][input_value]
                        if sys_cls != 1:
                            entry.setdefault("classes", {})
                            entry["classes"].setdefault(sys_cls, {})[input_value] = []

                    if field == "reactions":
                        v = add_dict[entry["role"]][field][input_value]
                        if v == 1:
                            cpt = DEFAULT_COMPARTMENT
                            issues and issues.warn(
                                f"reaction '{input_value}' on '{entry['role']}': "
                                f"no compartment — defaulted to '{cpt}'")
                        else:
                            cpt = v
                        entry.setdefault("localization", {}).setdefault(cpt, {})[input_value] = ["Assumed"]
            updated_role = True

        if entry["role"] in assign_dict:
            for field, val in assign_dict[entry["role"]].items():
                entry[field] = coerce_value(field, val)
            updated_role = True

        if entry["role"] in key_dict:
            for field in key_dict[entry["role"]]:
                for old_entry in key_dict[entry["role"]][field]:
                    new_entry = key_dict[entry["role"]][field][old_entry]
                    if old_entry not in entry.get(field, {}):
                        if issues is not None:
                            issues.warn(f"RELOCATE on '{entry['role']}': old entry '{old_entry}' "
                                        f"not found in field '{field}'")
                        continue
                    entry[field][new_entry] = entry[field][old_entry]
                    del entry[field][old_entry]
                    if old_entry in entry.get("compartmentalization", {}):
                        new_hash = copy.deepcopy(entry["compartmentalization"][old_entry])
                        new_hash["reaction"] = new_entry
                        for kbid in new_hash.get("kbase_ids", {}):
                            for rxn_idx in range(len(new_hash["kbase_ids"][kbid])):
                                rxn = new_hash["kbase_ids"][kbid][rxn_idx]
                                rxn = rxn.replace("_" + old_entry, "_" + new_entry)
                                new_hash["kbase_ids"][kbid][rxn_idx] = rxn
                        entry["compartmentalization"][new_entry] = new_hash
                        del entry["compartmentalization"][old_entry]
                    updated_role = True

        if entry["role"] in rem_dict:
            for field in rem_dict[entry["role"]]:
                for input_value in rem_dict[entry["role"]][field]:
                    fv = entry.get(field)
                    if isinstance(fv, list) and input_value in fv:
                        fv.remove(input_value)
                    elif isinstance(fv, dict) and input_value in fv:
                        del fv[input_value]
                    if field == "features":
                        delete_cpts = []
                        for cpt in entry.get("localization", {}):
                            if input_value in entry["localization"][cpt]:
                                del entry["localization"][cpt][input_value]
                            if len(entry["localization"][cpt]) == 0:
                                delete_cpts.append(cpt)
                        for cpt in delete_cpts:
                            del entry["localization"][cpt]
            updated_role = True

        if entry["role"] in change_dict:
            for field, val in change_dict[entry["role"]].items():
                entry[field] = coerce_value(field, val)
            updated_role = True

        if updated_role:
            entry.setdefault("curators", [])
            if curator and curator not in entry["curators"]:
                entry["curators"].append(curator)
            touched.add(entry["role"])

    return touched, rename_map


def ensure_schema_defaults(entry, schema):
    msgs = []
    role_name = entry.get("role", "<unnamed>")
    for key, rules in schema.items():
        if rules["required"] and key not in entry:
            entry[key] = copy.deepcopy(rules["default"])
            msgs.append(f"[DEFAULT FILLED] '{key}' missing in '{role_name}' — set to default")
    return msgs


def validate_dependencies(entry, schema):
    msgs = []
    role_name = entry.get("role", "<unnamed>")
    for key, rules in schema.items():
        dep = rules.get("depends_on")
        if not dep or key not in entry: continue
        value = entry[key]
        if not isinstance(value, dict): continue
        if "keys_from" in dep:
            allowed = set()
            for source_field in dep["keys_from"]:
                allowed.update(entry.get(source_field, []))
            for k in value.keys():
                if k not in allowed:
                    msgs.append(f"[DEP] '{key}' key '{k}' in '{role_name}' "
                                f"not present in {dep['keys_from']}")
        if "inner_keys_from" in dep:
            allowed = set()
            for source_field in dep["inner_keys_from"]:
                allowed.update(entry.get(source_field, []))
            for outer_k, inner in value.items():
                if not isinstance(inner, dict): continue
                for k in inner.keys():
                    if k not in allowed:
                        msgs.append(f"[DEP] '{key}.{outer_k}' inner key '{k}' in "
                                    f"'{role_name}' not present in {dep['inner_keys_from']}")
    return msgs


def assign_kbase_id(entry, existing_ids, renamed_from=None, issues=None):
    role_name = entry.get("role", "<unnamed>")
    if not entry.get("role") or not entry.get("reactions") or not entry.get("subsystems"):
        if renamed_from is not None or "kbase_id" not in entry:
            issues and issues.warn(
                f"Missing role/reactions/subsystems for '{role_name}' — cannot create unique KBase Role ID")
        return False
    if "kbase_id" in entry and renamed_from is None:
        return False
    old_id = entry.get("kbase_id")
    role_str = entry["role"] + entry["reactions"][0] + entry["subsystems"][0]
    entry_id = "PS_role_" + hashlib.sha256(role_str.encode("utf-8")).hexdigest()[:6]
    pool = set(existing_ids)
    if old_id in pool: pool.discard(old_id)
    while entry_id in pool:
        entry_id = "PS_role_" + hashlib.sha256(entry_id.encode("utf-8")).hexdigest()[:6]
    if entry_id == old_id: return False
    entry["kbase_id"] = entry_id
    if old_id: existing_ids.discard(old_id)
    existing_ids.add(entry_id)
    if renamed_from is not None and old_id is not None and issues is not None:
        issues.warn(f"kbase_id changed for renamed role '{role_name}' (was {old_id}, now {entry_id})")
    return True


def run_apply(tsv_text, curator, schema, dry_run=False, store=None):
    issues = IssueCollector()
    actions = parse_tsv_text(tsv_text, schema=schema, issues=issues)
    if not os.path.isfile(ROLES_FILE):
        issues.error(f"PlantSEED_Roles.json not found at {ROLES_FILE}")
        return _issue_dict(issues, summary={}, role_diffs=[])

    with open(ROLES_FILE) as f:
        roles_list = json.load(f)

    known_roles = {entry["role"] for entry in roles_list} | set(actions["new"])
    bucket_to_action = {"replace": "UPDATE", "add": "ADD", "rem": "REMOVE",
                        "key": "RELOCATE", "change": "CHANGE", "assign": "ASSIGN"}
    for bucket, action_name in bucket_to_action.items():
        for role_name in actions[bucket]:
            if role_name not in known_roles:
                issues.warn(f"role '{role_name}' not found in database — its "
                            f"{action_name} action(s) will be ignored")

    affected = set(known_roles_for_actions(actions))
    before_snapshot = {r["role"]: copy.deepcopy(r)
                       for r in roles_list if r["role"] in affected}

    if not seed_new_entries(roles_list, actions["new"], schema, actions=actions, issues=issues):
        return _issue_dict(issues, summary={}, role_diffs=[])

    touched, rename_map = apply_actions(roles_list, actions, curator, issues=issues)
    touched.update(actions["new"])

    reverse_rename = {new: old for old, new in rename_map.items()}
    existing_ids = {entry["kbase_id"] for entry in roles_list if "kbase_id" in entry}
    for entry in roles_list:
        if entry["role"] not in touched: continue
        for w in ensure_schema_defaults(entry, schema): issues.warn(w)
        for w in validate_dependencies(entry, schema):  issues.warn(w)
        assign_kbase_id(entry, existing_ids,
                        renamed_from=reverse_rename.get(entry["role"]), issues=issues)

    role_diffs = []
    for entry in roles_list:
        if entry["role"] not in touched: continue
        old_name = reverse_rename.get(entry["role"], entry["role"])
        role_diffs.append({
            "role":   entry["role"],
            "renamed_from": old_name if old_name != entry["role"] else None,
            "before": before_snapshot.get(old_name),
            "after":  copy.deepcopy(entry),
            "is_new": entry["role"] in actions["new"],
        })

    summary = {"touched": sorted(touched), "renamed": rename_map,
               "new": actions["new"], "dry_run": dry_run}
    if not dry_run and touched and not issues.errors:
        atomic_write(ROLES_FILE, json.dumps(roles_list, indent=4))
        issues.log(f"Wrote {len(roles_list)} roles to {ROLES_FILE}")
        if store is not None: store.load_roles(force=True)
    elif dry_run:
        issues.log(f"Dry run — no file written. {len(touched)} role(s) would be touched.")
    elif not touched:
        issues.log("No roles touched — nothing to write.")
    elif issues.errors:
        issues.log("Errors present — refusing to write database.")
    return _issue_dict(issues, summary=summary, role_diffs=role_diffs)


def known_roles_for_actions(actions):
    roles = set()
    for bucket in ("replace", "add", "rem", "key", "change", "assign"):
        roles.update(actions[bucket].keys())
    roles.update(actions["new"])
    roles.update(actions["replace"].keys())
    return roles


def _issue_dict(issues, summary, role_diffs):
    return {"warnings": issues.warnings, "errors": issues.errors,
            "info": issues.info, "summary": summary, "role_diffs": role_diffs}


# ----------------------------------------------------------------------------
# Curator-file I/O. Atomic writes; NO auto-backups (per Sam — no backup files).
# ----------------------------------------------------------------------------
def curator_dir_path(username):
    return os.path.join(CURATORS_DIR, username)


def list_curator_files(username):
    path = curator_dir_path(username)
    if not os.path.isdir(path): return []
    out = []
    for name in sorted(os.listdir(path)):
        if not name.endswith(".tsv"): continue
        fp = os.path.join(path, name)
        try:
            st = os.stat(fp)
            with open(fp) as f:
                lines = f.readlines()
            row_count = sum(1 for ln in lines if ln.strip() and not ln.startswith("#"))
        except OSError:
            row_count = 0; st = None
        out.append({
            "name":   name,
            "size":   st.st_size if st else 0,
            "mtime":  st.st_mtime if st else 0,
            "rows":   row_count,
            "relpath": os.path.relpath(fp, BASE_DIR),
        })
    return out


def list_all_curators():
    if not os.path.isdir(CURATORS_DIR): return []
    out = []
    for d in sorted(os.listdir(CURATORS_DIR)):
        dp = os.path.join(CURATORS_DIR, d)
        if not os.path.isdir(dp): continue
        tsvs = [n for n in os.listdir(dp) if n.endswith(".tsv")]
        out.append({"name": d, "n_files": len(tsvs)})
    return out


def read_curator_file(username, filename):
    fp = os.path.join(curator_dir_path(username), sanitize_filename(filename))
    if not os.path.isfile(fp): return ""
    with open(fp) as f:
        return f.read()


def write_curator_file(username, filename, content):
    os.makedirs(curator_dir_path(username), exist_ok=True)
    fp = os.path.join(curator_dir_path(username), sanitize_filename(filename))
    if content and not content.endswith("\n"):
        content += "\n"
    atomic_write(fp, content)
    return fp


def append_curator_file(username, filename, rows):
    if not rows: return None, 0
    os.makedirs(curator_dir_path(username), exist_ok=True)
    fp = os.path.join(curator_dir_path(username), sanitize_filename(filename))
    needs_leading_nl = False
    if os.path.exists(fp) and os.path.getsize(fp) > 0:
        with open(fp, "rb") as f:
            try:
                f.seek(-1, os.SEEK_END)
                needs_leading_nl = f.read(1) != b"\n"
            except OSError:
                pass
    existing = ""
    if os.path.exists(fp):
        with open(fp) as f:
            existing = f.read()
    new_text = existing + ("\n" if needs_leading_nl else "")
    for r in rows:
        new_text += r.rstrip("\n") + "\n"
    atomic_write(fp, new_text)
    return fp, len(rows)


# ----------------------------------------------------------------------------
# Per-role preview
# ----------------------------------------------------------------------------
def preview_for_enzyme(enzyme, rows, schema, store):
    issues = IssueCollector()
    text = "\n".join(rows)
    actions = parse_tsv_text(text, schema=schema, issues=issues)
    roles_copy = copy.deepcopy(store.roles)
    before = next((copy.deepcopy(r) for r in roles_copy if r["role"] == enzyme), None)
    if enzyme in actions["new"]:
        before = None
    if not seed_new_entries(roles_copy, actions["new"], schema, actions=actions, issues=issues):
        return {"before": before, "after": None, "errors": issues.errors, "warnings": issues.warnings}
    touched, rename_map = apply_actions(roles_copy, actions, curator="(preview)", issues=issues)
    final_name = rename_map.get(enzyme, enzyme)
    after = next((r for r in roles_copy if r["role"] == final_name), None)
    return {
        "before":     before,
        "after":      after,
        "renamed_to": final_name if final_name != enzyme else None,
        "errors":     issues.errors,
        "warnings":   issues.warnings,
        "touched":    sorted(touched),
    }


# ============================================================================
# HTTP server
# ============================================================================
STORE = DataStore()


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status
        self.message = message


def json_response(handler, payload, status=200):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


# ---------- API handlers ----------
def api_status(_r, _q, _b):
    return {
        "roles":        len(STORE.roles),
        "schema_keys":  list(STORE.schema_normalized.keys()),
        "expasy":       STORE.expasy_status(),
        "roles_file":   ROLES_FILE,
        "curators_dir": CURATORS_DIR,
    }


def api_search(_r, qs, _b):
    return ranked_search(STORE, qs.get("q", [""])[0])


def api_role(_r, qs, _b):
    name = qs.get("name", [""])[0]
    if not name: raise ApiError("missing 'name'")
    entry = STORE.find_role(name)
    if entry is None:
        return {"exists": False, "role": name}
    return {"exists": True, "entry": entry,
            "warnings": required_empty_fields(entry, STORE.schema_normalized)}


def api_xref(_r, qs, _b):
    field = qs.get("field", [""])[0]
    value = qs.get("value", [""])[0]
    exclude = qs.get("exclude", [""])[0] or None
    mode = qs.get("mode", ["exact"])[0]
    if not field or not value:
        return {"matches": [], "total": 0}
    if mode == "substring":
        m = find_substring_match(STORE.roles, field, value, exclude=exclude)
    else:
        m = find_exact_match(STORE.roles, field, value, exclude=exclude)
    return {"matches": m[:50], "total": len(m)}


def api_user(_r, _q, _b):
    display = get_git_username()
    info = detect_github_username(display)
    info["display_name"] = display
    info["dir_name"] = normalize_existing_dirname(info["username"])
    info["email"] = get_git_email()
    return info


def api_set_user(_r, _q, body):
    username = sanitize_username(body.get("username") or "") or "user"
    display  = (body.get("display_name") or "").strip()
    username = normalize_existing_dirname(username)
    confirm_curator_registry(username, display, get_git_email())
    os.makedirs(curator_dir_path(username), exist_ok=True)
    return {"username": username, "display_name": display}


def api_files(_r, qs, _b):
    user = qs.get("user", [""])[0]
    if not user: raise ApiError("missing user")
    return {"files": list_curator_files(user),
            "dir":   curator_dir_path(user),
            "all_curators": list_all_curators()}


def api_file_read(_r, qs, _b):
    user = qs.get("user", [""])[0]
    name = qs.get("name", [""])[0]
    if not user or not name: raise ApiError("missing user/name")
    content = read_curator_file(user, name)
    rows = parse_tsv_to_rows(content)
    return {"content": content, "rows": rows}


def api_file_create(_r, _q, body):
    user = (body.get("user") or "").strip()
    name = (body.get("name") or "").strip()
    if not user or not name: raise ApiError("missing user/name")
    name = sanitize_filename(name)
    if not name.endswith(".tsv"): name += ".tsv"
    fp = os.path.join(curator_dir_path(user), name)
    if not os.path.exists(fp):
        os.makedirs(curator_dir_path(user), exist_ok=True)
        atomic_write(fp, "")
    return {"name": name, "path": fp}


def api_file_save(_r, _q, body):
    user = (body.get("user") or "").strip()
    name = (body.get("name") or "").strip()
    content = body.get("content", "")
    if not user or not name: raise ApiError("missing user/name")
    fp = write_curator_file(user, name, content)
    return {"path": fp, "bytes": len(content)}


def api_file_append(_r, _q, body):
    user = (body.get("user") or "").strip()
    name = (body.get("name") or "").strip()
    rows = body.get("rows") or []
    if not user or not name: raise ApiError("missing user/name")
    if not isinstance(rows, list): raise ApiError("rows must be a list of strings")
    fp, n = append_curator_file(user, name, [str(r) for r in rows])
    return {"path": fp, "appended": n}


def api_file_delete(_r, _q, body):
    user = (body.get("user") or "").strip()
    name = (body.get("name") or "").strip()
    if not user or not name: raise ApiError("missing user/name")
    fp = os.path.join(curator_dir_path(user), sanitize_filename(name))
    if not os.path.exists(fp): raise ApiError("file not found", 404)
    os.remove(fp)
    return {"removed": fp}


def api_validate(_r, _q, body):
    action  = (body.get("action") or "").upper()
    enzyme  = body.get("enzyme") or ""
    payload = body.get("payload") or {}
    errors, warnings = validate_payload(action, enzyme, payload, STORE)
    return {"errors": errors, "warnings": warnings, "ok": len(errors) == 0}


def api_build_rows(_r, _q, body):
    action  = (body.get("action") or "").upper()
    enzyme  = body.get("enzyme") or ""
    payload = body.get("payload") or {}
    rows, errors, warnings = build_tsv_rows(action, enzyme, payload, STORE)
    return {"rows": rows, "errors": errors, "warnings": warnings}


def api_preview(_r, _q, body):
    enzyme = body.get("enzyme") or ""
    rows = body.get("rows") or []
    if not enzyme: raise ApiError("missing enzyme")
    if not isinstance(rows, list): raise ApiError("rows must be a list")
    return preview_for_enzyme(enzyme, [str(r) for r in rows],
                              STORE.schema_normalized, STORE)


def api_apply(_r, _q, body):
    user = (body.get("user") or "").strip()
    tsv = body.get("tsv") or ""
    dry_run = bool(body.get("dry_run", False))
    if not tsv.strip(): raise ApiError("nothing to apply (TSV is empty)")
    return run_apply(tsv, user, STORE.schema_normalized, dry_run=dry_run, store=STORE)


def api_reload(_r, _q, _b):
    STORE.load_roles(force=True)
    return {"roles": len(STORE.roles)}


def api_action_meta(_r, _q, _b):
    return {
        "actions": [
            {"name": a, "description": ACTION_DESCRIPTIONS[a],
             "fields": ACTION_FIELDS.get(a, [])}
            for a in ACTION_OPTIONS
        ],
        "multi_col":      MULTI_COL_FIELDS,
        "scalar_types":   SCALAR_TYPES,
        "field_prefixes": list(FIELD_PREFIXES.keys()),
        "compartments":   [{"id": c, "name": n} for c, n in COMPARTMENTS],
        "default_compartment": DEFAULT_COMPARTMENT,
        "default_loc_source":  DEFAULT_LOC_SOURCE,
    }


def api_all_roles(_r, _q, _b):
    return {"roles": STORE.all_roles_summary(), "facets": STORE.facets()}


def api_expasy_refresh(_r, _q, _b):
    if os.path.exists(ENZYME_DAT_CACHE):
        os.remove(ENZYME_DAT_CACHE)
    with STORE.lock:
        STORE.ec_status = "idle"
        STORE.ec_entries = []
    STORE.start_load_expasy()
    return {"status": "refreshing"}


def parse_tsv_to_rows(text):
    out = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip("\r\n")
        if not line.strip() or line.startswith("#"): continue
        cols = line.split("\t")
        if len(cols) < 2:
            out.append({"lineno": lineno, "raw": line, "valid": False, "cols": cols})
            continue
        out.append({
            "lineno": lineno, "raw": line, "valid": True, "cols": cols,
            "enzyme": cols[0], "action": cols[1],
            "field":  cols[2] if len(cols) > 2 else "",
            "value":  cols[3] if len(cols) > 3 else "",
            "extra":  cols[4] if len(cols) > 4 else "",
        })
    return out


API_ROUTES = {
    ("GET",  "/api/status"):         api_status,
    ("GET",  "/api/search"):         api_search,
    ("GET",  "/api/role"):           api_role,
    ("GET",  "/api/roles/all"):      api_all_roles,
    ("GET",  "/api/xref"):           api_xref,
    ("GET",  "/api/user"):           api_user,
    ("POST", "/api/user"):           api_set_user,
    ("GET",  "/api/files"):          api_files,
    ("GET",  "/api/file"):           api_file_read,
    ("POST", "/api/file/create"):    api_file_create,
    ("POST", "/api/file/save"):      api_file_save,
    ("POST", "/api/file/append"):    api_file_append,
    ("POST", "/api/file/delete"):    api_file_delete,
    ("POST", "/api/validate"):       api_validate,
    ("POST", "/api/build"):          api_build_rows,
    ("POST", "/api/preview"):        api_preview,
    ("POST", "/api/apply"):          api_apply,
    ("POST", "/api/reload"):         api_reload,
    ("GET",  "/api/actions"):        api_action_meta,
    ("POST", "/api/expasy/refresh"): api_expasy_refresh,
}


class Handler(BaseHTTPRequestHandler):
    server_version = "PlantSEEDCurationDashboard/3.0"

    def log_message(self, format, *args):
        sys.stderr.write(f"  [{self.command}] {self.path}\n")

    def _dispatch(self, method):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        if path in ("/", "/index.html"):
            return self._serve(INDEX_HTML, "text/html")
        if path == "/static/app.js":
            return self._serve(INDEX_JS, "text/javascript")
        if path == "/static/app.css":
            return self._serve(INDEX_CSS, "text/css")
        if path == "/static/favicon.ico":
            self.send_response(204); self.end_headers(); return
        handler = API_ROUTES.get((method, path))
        if not handler:
            self.send_error(404, f"unknown path {path}"); return
        body = {}
        if method == "POST":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            if raw:
                try:
                    body = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    self.send_error(400, "invalid JSON body"); return
        try:
            STORE.load_roles(); STORE.load_schema()
            result = handler(self, qs, body)
            json_response(self, result)
        except ApiError as e:
            json_response(self, {"error": e.message}, status=e.status)
        except Exception as e:
            sys.stderr.write("API error:\n" + traceback.format_exc())
            json_response(self, {"error": str(e), "trace": traceback.format_exc()}, status=500)

    def do_GET(self):  self._dispatch("GET")
    def do_POST(self): self._dispatch("POST")

    def _serve(self, content, mime):
        body = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def find_free_port(host, preferred):
    for port in [preferred] + [preferred + i for i in range(1, 30)]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError("no free port found")


# ============================================================================
# Embedded frontend: HTML / CSS / JS
# Style brief: clean, GitHub-dark-inspired. No gradients, no neon, no emoji,
# no animated pulses. Single accent color (#58a6ff blue). Subtle borders.
# ============================================================================

INDEX_CSS = r"""
/* ============================================================================
 * PlantSEED Curation Dashboard - v4
 * App-shell layout: sidebar + full-height main. Dense panels. Theme toggle.
 * ============================================================================ */

:root {
  /* Dark (default) — GitHub Primer dark tokens */
  --bg:           #0d1117;
  --bg-elev:      #010409;
  --sidebar:      #010409;
  --panel:        #161b22;
  --panel-2:      #1c2128;
  --panel-3:      #21262d;
  --border:       #30363d;
  --border-soft:  #21262d;
  --text:         #e6edf3;
  --text-2:       #c9d1d9;
  --muted:        #8b949e;
  --dim:          #6e7681;
  --accent:       #2f81f7;
  --accent-fg:    #ffffff;
  --accent-bg:    rgba(47, 129, 247, 0.15);
  --accent-soft:  rgba(47, 129, 247, 0.30);
  --good:         #3fb950;
  --good-bg:      rgba(63, 185, 80, 0.15);
  --warn:         #d29922;
  --warn-bg:      rgba(210, 153, 34, 0.15);
  --bad:          #f85149;
  --bad-bg:       rgba(248, 81, 73, 0.15);
  --new:          #bc8cff;
  --new-bg:       rgba(188, 140, 255, 0.15);
  --code-bg:      #0d1117;
  --hover:        #1c2128;
  --selected-bg:  rgba(47, 129, 247, 0.12);
  --diff-add-bg:  rgba(63, 185, 80, 0.10);
  --diff-rem-bg:  rgba(248, 81, 73, 0.10);
  --diff-add-fg:  #7ee787;
  --diff-rem-fg:  #ff9591;
}

[data-theme="light"] {
  --bg:           #f6f8fa;
  --bg-elev:      #ffffff;
  --sidebar:      #ffffff;
  --panel:        #ffffff;
  --panel-2:      #f6f8fa;
  --panel-3:      #eaeef2;
  --border:       #d0d7de;
  --border-soft:  #d8dee4;
  --text:         #1f2328;
  --text-2:       #424a53;
  --muted:        #59636e;
  --dim:          #818b98;
  --accent:       #0969da;
  --accent-fg:    #ffffff;
  --accent-bg:    rgba(9, 105, 218, 0.10);
  --accent-soft:  rgba(9, 105, 218, 0.25);
  --good:         #1a7f37;
  --good-bg:      rgba(26, 127, 55, 0.08);
  --warn:         #9a6700;
  --warn-bg:      rgba(154, 103, 0, 0.08);
  --bad:          #cf222e;
  --bad-bg:       rgba(207, 34, 46, 0.08);
  --new:          #8250df;
  --new-bg:       rgba(130, 80, 223, 0.08);
  --code-bg:      #f6f8fa;
  --hover:        #f3f4f6;
  --selected-bg:  rgba(9, 105, 218, 0.08);
  --diff-add-bg:  rgba(26, 127, 55, 0.08);
  --diff-rem-bg:  rgba(207, 34, 46, 0.08);
  --diff-add-fg:  #1a7f37;
  --diff-rem-fg:  #cf222e;
}

* { box-sizing: border-box; }
html, body { height: 100%; margin: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", Roboto, sans-serif;
  font-size: 13px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  overflow: hidden;
  /* Default render scale: 100% browser zoom felt too small for the user.
     1.15 reproduces their preferred 115% manual zoom. */
  zoom: 1.15;
}
code, pre, .mono { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; }

/* ============================================================================
 * App shell
 * ============================================================================ */
.app {
  display: grid;
  grid-template-columns: 188px 1fr;
  height: 100vh;
  overflow: hidden;
}

/* Sidebar -------------------------------------------------------------------- */
.sidebar {
  background: var(--sidebar);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  overflow: hidden;
}
.sidebar .brand {
  padding: 12px 16px 10px;
  font-size: 14px; font-weight: 600;
  letter-spacing: -0.1px;
  border-bottom: 1px solid var(--border-soft);
}
.sidebar .brand .accent { color: var(--accent); }
.sidebar nav {
  flex: 1; display: flex; flex-direction: column;
  padding: 8px 6px;
  overflow-y: auto;
}
.sidebar nav button {
  background: none; border: 0;
  padding: 7px 12px;
  margin: 1px 0;
  color: var(--muted);
  cursor: pointer; text-align: left;
  font-size: 13px; font-family: inherit;
  border-radius: 5px;
  display: flex; align-items: center; justify-content: space-between;
}
.sidebar nav button:hover { color: var(--text); background: var(--hover); }
.sidebar nav button.active {
  color: var(--text); background: var(--accent-bg);
  font-weight: 500;
}
.sidebar nav button .label-count {
  background: var(--panel-3); color: var(--text);
  font-size: 10.5px; font-weight: 600;
  padding: 1px 6px; border-radius: 10px;
  display: none;
}
.sidebar nav button .label-count.visible { display: inline-block; }
.sidebar .footer {
  border-top: 1px solid var(--border-soft);
  padding: 10px 12px;
  display: flex; flex-direction: column; gap: 6px;
}
.sidebar .footer .row {
  display: flex; align-items: center; justify-content: space-between; gap: 6px;
  font-size: 12px;
}
.sidebar .footer .user-block {
  font-size: 12px; color: var(--muted);
}
.sidebar .footer .user-block .username {
  color: var(--text); font-weight: 500; cursor: pointer;
}
.sidebar .footer .user-block .username:hover { text-decoration: underline; color: var(--accent); }
.theme-toggle {
  background: none; border: 1px solid var(--border);
  color: var(--muted); border-radius: 4px;
  padding: 3px 8px; font-size: 11px; cursor: pointer;
  font-family: inherit;
}
.theme-toggle:hover { color: var(--text); border-color: var(--accent); }

/* Main column ---------------------------------------------------------------- */
.main {
  display: flex; flex-direction: column;
  overflow: hidden;
  min-width: 0;
}
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid var(--border);
  background: var(--panel);
  height: 42px;
  flex-shrink: 0;
}
.topbar .section-title {
  font-size: 14px; font-weight: 600; color: var(--text);
}
.topbar .status {
  display: flex; align-items: center; gap: 14px;
  font-size: 12px; color: var(--muted);
}
.topbar .status .item { display: flex; gap: 5px; align-items: center; }
.topbar .status .item .label { color: var(--dim); }
.topbar .status .item .value { color: var(--text); }
.topbar .status .item .value.muted { color: var(--muted); }
.topbar .status .reload {
  background: none; border: 0; color: var(--accent);
  cursor: pointer; font-size: 12px; padding: 0;
  font-family: inherit;
}
.topbar .status .reload:hover { text-decoration: underline; }

.content {
  flex: 1;
  padding: 12px;
  overflow: hidden;
  min-height: 0;
}
.section {
  display: none; height: 100%; min-height: 0;
  flex-direction: column;
}
.section.active { display: flex; }

/* ============================================================================
 * Grid layouts per section — each panel fills available height & scrolls.
 * ============================================================================ */
.grid-curate {
  display: grid;
  grid-template-columns: minmax(260px, 0.85fr) minmax(320px, 1fr) minmax(320px, 1.15fr);
  gap: 12px;
  flex: 1; min-height: 0;
}
.grid-files {
  display: grid;
  grid-template-columns: minmax(220px, 0.6fr) minmax(360px, 1.6fr);
  gap: 12px;
  flex: 1; min-height: 0;
}
.grid-browse {
  display: grid;
  grid-template-columns: minmax(220px, 0.55fr) minmax(280px, 1.1fr) minmax(280px, 1.1fr);
  gap: 12px;
  flex: 1; min-height: 0;
}
.col-stack { display: flex; flex-direction: column; gap: 12px; min-height: 0; }
.col-stack > .panel { min-height: 0; }
.flex-1 { flex: 1; min-height: 0; }

/* ============================================================================
 * Panel
 * ============================================================================ */
.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px;
  min-height: 0;
  overflow: hidden;
  display: flex; flex-direction: column;
}
.panel-scroll { overflow-y: auto; flex: 1; min-height: 0; margin: 0 -4px; padding: 0 4px; }
.panel.scroll { overflow-y: auto; }
.panel > h2 {
  margin: 0 0 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: .6px;
  display: flex; justify-content: space-between; align-items: center;
  flex-shrink: 0;
}
.panel > h2 .right {
  font-size: 11px; text-transform: none; letter-spacing: 0;
  color: var(--dim); font-weight: 400;
}
.panel > h2 .right.actions { display: flex; gap: 4px; }

/* ============================================================================
 * Form elements
 * ============================================================================ */
input[type=text], input[type=search], input[type=number], select, textarea {
  background: var(--code-bg);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 5px 8px;
  width: 100%;
  font-family: inherit;
  font-size: 12.5px;
}
input:focus, select:focus, textarea:focus {
  outline: 0;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-bg);
}
input.invalid, select.invalid {
  border-color: var(--bad);
  box-shadow: 0 0 0 3px var(--bad-bg);
}
textarea { min-height: 140px; resize: vertical; font-family: ui-monospace, monospace; }
label {
  display: block;
  font-size: 11px; color: var(--muted);
  margin: 8px 0 3px;
  text-transform: uppercase; letter-spacing: .4px;
  font-weight: 600;
}
label:first-child { margin-top: 0; }
.field-error { color: var(--bad); font-size: 11.5px; margin-top: 3px; }
.help {
  color: var(--muted); font-size: 11.5px;
  margin-top: 4px; line-height: 1.4;
}
.help code {
  background: var(--panel-3); color: var(--accent);
  padding: 0 4px; border-radius: 3px; font-size: 11px;
}
.subtle { color: var(--muted); font-size: 12px; }
.dim    { color: var(--dim); }

/* ============================================================================
 * Buttons
 * ============================================================================ */
button.btn {
  background: var(--panel-3);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 4px 12px;
  font-size: 12.5px; cursor: pointer;
  font-family: inherit;
  display: inline-flex; align-items: center; gap: 5px;
}
button.btn:hover:not(:disabled) { background: var(--hover); border-color: var(--border); }
button.btn:disabled { opacity: 0.5; cursor: not-allowed; }
button.btn.primary {
  background: var(--accent); color: var(--accent-fg);
  border-color: var(--accent); font-weight: 500;
}
button.btn.primary:hover:not(:disabled) { filter: brightness(1.1); }
button.btn.danger { color: var(--bad); }
button.btn.danger:hover:not(:disabled) { background: var(--bad-bg); border-color: var(--bad); }
button.btn.warn   { color: var(--warn); }
button.btn.warn:hover:not(:disabled)   { background: var(--warn-bg); border-color: var(--warn); }
button.btn.good   { color: var(--good); }
button.btn.good:hover:not(:disabled)   { background: var(--good-bg); border-color: var(--good); }
button.btn.small  { padding: 3px 8px; font-size: 11.5px; }
button.btn.tiny   { padding: 1px 6px; font-size: 11px; }
button.btn.link   {
  background: none; border: 0; color: var(--accent);
  padding: 0; cursor: pointer; font-family: inherit;
  text-decoration: none;
}
button.btn.link:hover { text-decoration: underline; }

.toolbar { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.toolbar-spacer { flex: 1; }

/* ============================================================================
 * Tags
 * ============================================================================ */
.tag {
  display: inline-block; padding: 1px 7px;
  border-radius: 12px; font-size: 10.5px; font-weight: 500;
  background: var(--panel-3); color: var(--muted);
  border: 1px solid var(--border);
  vertical-align: middle;
}
.tag.plant   { color: var(--good); border-color: var(--good); background: var(--good-bg); }
.tag.expasy  { color: var(--warn); border-color: var(--warn); background: var(--warn-bg); }
.tag.new     { color: var(--new);  border-color: var(--new);  background: var(--new-bg); }
.tag.action { font-weight: 600; letter-spacing: .3px; }
.tag.ADD     { color: var(--good); border-color: var(--good); background: var(--good-bg); }
.tag.REMOVE  { color: var(--bad);  border-color: var(--bad);  background: var(--bad-bg); }
.tag.UPDATE  { color: var(--accent); border-color: var(--accent); background: var(--accent-bg); }
.tag.NEW     { color: var(--new);  border-color: var(--new);  background: var(--new-bg); }
.tag.CHANGE  { color: var(--accent); border-color: var(--accent); background: var(--accent-bg); }
.tag.ASSIGN  { color: var(--accent); border-color: var(--accent); background: var(--accent-bg); }
.tag.RELOCATE{ color: var(--warn); border-color: var(--warn); background: var(--warn-bg); }

/* ============================================================================
 * Search results
 * ============================================================================ */
.results {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 5px;
  flex: 1; min-height: 0;
  overflow-y: auto;
}
.results .group-header {
  padding: 5px 10px;
  font-size: 10.5px; font-weight: 600;
  color: var(--muted);
  text-transform: uppercase; letter-spacing: .5px;
  border-bottom: 1px solid var(--border-soft);
  background: var(--panel-2);
  position: sticky; top: 0;
  z-index: 1;
}
.results .item {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 10px;
  font-size: 12.5px; cursor: pointer;
  border-bottom: 1px solid var(--border-soft);
}
.results .item:last-child { border-bottom: 0; }
.results .item:hover { background: var(--hover); }
.results .item.selected { background: var(--selected-bg); }
.results .item .name { flex: 1; word-break: break-word; min-width: 0; }
.results .item .meta { font-size: 11px; color: var(--muted); flex-shrink: 0; }
.results .item mark {
  background: var(--accent-soft); color: inherit;
  padding: 0 2px; border-radius: 2px;
}
.results .item .sub {
  display: block; font-size: 10.5px; color: var(--dim);
  font-family: ui-monospace, monospace; margin-top: 1px;
}
.results .empty { padding: 14px; text-align: center; color: var(--dim); font-style: italic; }

/* ============================================================================
 * Current-enzyme banner
 * ============================================================================ */
.current-enzyme {
  background: var(--accent-bg);
  border: 1px solid var(--accent-soft);
  border-radius: 5px;
  padding: 8px 10px;
  display: flex; align-items: center; gap: 10px;
  font-size: 12.5px;
  margin-bottom: 8px;
}
.current-enzyme .label {
  font-size: 10px; color: var(--accent);
  text-transform: uppercase; letter-spacing: .5px;
  font-weight: 700; flex-shrink: 0;
}
.current-enzyme .name {
  flex: 1; font-weight: 500; word-break: break-word; min-width: 0;
}

/* ============================================================================
 * Role card (current record + browse detail)
 * ============================================================================ */
.role-card {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 5px;
}
.role-card .field {
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 4px 10px;
  padding: 5px 10px;
  border-bottom: 1px solid var(--border-soft);
  font-size: 12px;
  align-items: start;
}
.role-card .field:last-child { border-bottom: 0; }
.role-card .field .k {
  color: var(--muted);
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: .4px;
  font-weight: 600;
  padding-top: 1px;
}
.role-card .field .v {
  font-family: ui-monospace, monospace;
  word-break: break-word;
}
.role-card .field .v.empty {
  color: var(--dim);
  font-style: italic;
  font-family: inherit;
}
.role-card .field .v code {
  display: inline-block;
  background: var(--panel-3);
  color: var(--accent);
  padding: 1px 5px;
  border-radius: 3px;
  margin: 1px 3px 1px 0;
  font-size: 11px;
}
.role-card .field .v .obj-line {
  margin: 1px 0;
}

/* ============================================================================
 * Entry rows (ADD/REMOVE entries)
 * ============================================================================ */
.entry-row {
  display: flex; gap: 5px; margin-bottom: 4px; align-items: flex-start;
}
.entry-row > input, .entry-row > select { flex: 1; }
.entry-row .entry-extra-wrap {
  flex: 1; display: flex; gap: 4px;
}
.entry-row .entry-extra-wrap > * { flex: 1; }
.entry-row .rm-btn { flex: 0 0 auto; }

/* ============================================================================
 * Staging cards
 * ============================================================================ */
.staging-card {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px;
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 5px;
  margin-bottom: 4px;
  font-size: 12px;
}
.staging-card .num {
  color: var(--dim); width: 28px;
  font-family: ui-monospace, monospace; font-size: 11px;
  text-align: right; flex-shrink: 0;
}
.staging-card .body {
  flex: 1; min-width: 0;
  font-family: ui-monospace, monospace; word-break: break-all;
}
.staging-card .body .e { color: var(--accent); }
.staging-card .body .f { color: var(--accent); opacity: 0.85; }
.staging-card .body .v { color: var(--good); }
.staging-card .body .x { color: var(--warn); }
.staging-card .acts { display: flex; gap: 2px; flex-shrink: 0; }

/* ============================================================================
 * File editor table
 * ============================================================================ */
.editor-table {
  width: 100%; border-collapse: collapse; font-size: 12px;
}
.editor-table th, .editor-table td {
  text-align: left; padding: 4px 6px;
  border-bottom: 1px solid var(--border-soft);
}
.editor-table th {
  font-size: 10.5px; color: var(--muted);
  text-transform: uppercase; letter-spacing: .4px;
  font-weight: 600; background: var(--panel-2);
  position: sticky; top: 0;
}
.editor-table tr:hover td { background: var(--hover); }
.editor-table td input, .editor-table td select {
  padding: 3px 5px; font-size: 11.5px;
  background: var(--bg);
}
.editor-table .num {
  width: 32px; color: var(--dim);
  font-family: ui-monospace, monospace; font-size: 11px;
}

/* ============================================================================
 * Banners
 * ============================================================================ */
.banner {
  padding: 7px 10px;
  border-radius: 5px;
  margin-bottom: 8px;
  font-size: 12px;
  border-left: 3px solid;
  line-height: 1.45;
}
.banner.warn { background: var(--warn-bg); border-color: var(--warn); color: var(--warn); }
.banner.bad  { background: var(--bad-bg);  border-color: var(--bad);  color: var(--bad); }
.banner.good { background: var(--good-bg); border-color: var(--good); color: var(--good); }
.banner.info { background: var(--accent-bg); border-color: var(--accent); color: var(--accent); }
.banner b { color: inherit; }

/* ============================================================================
 * Lists in side panels
 * ============================================================================ */
.list-item {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 8px; border-radius: 4px; cursor: pointer;
  font-size: 12.5px;
  border: 1px solid transparent;
}
.list-item:hover { background: var(--hover); }
.list-item.selected {
  background: var(--selected-bg);
  border-color: var(--accent-soft);
}
.list-item .name { flex: 1; word-break: break-word; min-width: 0; }
.list-item .meta { font-size: 11px; color: var(--muted); flex-shrink: 0; }
.list-item .acts { display: flex; gap: 4px; flex-shrink: 0; }

/* ============================================================================
 * Browse facets — fill available height, scroll inside
 * ============================================================================ */
.facet-section { margin-bottom: 12px; }
.facet-section h4 {
  margin: 0 0 5px; font-size: 10.5px; color: var(--muted);
  text-transform: uppercase; letter-spacing: .4px; font-weight: 600;
}
.facet-options {
  display: flex; flex-wrap: wrap; gap: 3px;
  /* No max-height — the parent .panel handles scrolling */
}
.facet-chip {
  display: inline-block; padding: 2px 8px; font-size: 11px;
  background: var(--panel-2); border: 1px solid var(--border);
  border-radius: 10px; cursor: pointer;
  white-space: nowrap;
}
.facet-chip:hover { background: var(--hover); }
.facet-chip.active {
  background: var(--accent); color: var(--accent-fg);
  border-color: var(--accent); font-weight: 500;
}

/* ============================================================================
 * Compartment grid in help
 * ============================================================================ */
.compartment-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 3px;
}
.compartment-chip {
  padding: 4px 8px; background: var(--panel-2);
  border: 1px solid var(--border); border-radius: 4px;
  font-size: 11.5px; font-family: ui-monospace, monospace;
}
.compartment-chip .id {
  color: var(--accent); font-weight: 700;
  display: inline-block; width: 18px;
}

/* ============================================================================
 * Diff cards (apply tab + preview)
 * ============================================================================ */
.diff-card {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 10px; margin-bottom: 8px;
}
.diff-card h4 {
  margin: 0 0 8px; font-size: 12.5px; font-weight: 500;
  word-break: break-word;
  display: flex; align-items: center; gap: 8px;
}
.diff-section { margin: 4px 0; }
.diff-section .field-name {
  font-size: 10.5px; color: var(--muted);
  margin-bottom: 2px;
  text-transform: uppercase; letter-spacing: .4px; font-weight: 600;
}
.diff-line {
  font-family: ui-monospace, monospace; font-size: 11.5px;
  padding: 2px 8px; border-left: 2px solid;
  white-space: pre-wrap; word-break: break-word;
  margin: 1px 0;
}
.diff-line.add { color: var(--diff-add-fg); background: var(--diff-add-bg); border-color: var(--good); }
.diff-line.rem { color: var(--diff-rem-fg); background: var(--diff-rem-bg); border-color: var(--bad); }

/* ============================================================================
 * Modal
 * ============================================================================ */
.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.55);
  z-index: 100;
  display: flex; align-items: center; justify-content: center;
}
.modal {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  min-width: 380px; max-width: 90vw; max-height: 85vh;
  display: flex; flex-direction: column;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}
.modal .modal-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; border-bottom: 1px solid var(--border);
}
.modal .modal-head h3 { margin: 0; font-size: 13px; font-weight: 600; }
.modal .modal-head button {
  background: none; border: 0; color: var(--muted);
  cursor: pointer; font-size: 18px; line-height: 1;
  padding: 0 4px;
}
.modal .modal-head button:hover { color: var(--text); }
.modal .modal-body { padding: 14px; overflow-y: auto; flex: 1; }
.modal .modal-foot {
  padding: 10px 14px; border-top: 1px solid var(--border);
  display: flex; gap: 6px; justify-content: flex-end;
}

/* ============================================================================
 * Toast
 * ============================================================================ */
.toast-stack {
  position: fixed; bottom: 14px; right: 14px; z-index: 200;
  display: flex; flex-direction: column-reverse; gap: 5px;
  max-width: 400px;
}
.toast {
  background: var(--panel);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  padding: 8px 12px; border-radius: 5px;
  font-size: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  transition: all .2s;
}
.toast.bad  { border-left-color: var(--bad); }
.toast.good { border-left-color: var(--good); }
.toast.warn { border-left-color: var(--warn); }

/* ============================================================================
 * Spinner & misc
 * ============================================================================ */
.spinner {
  display: inline-block; width: 10px; height: 10px;
  border: 1.5px solid var(--muted); border-top-color: transparent;
  border-radius: 50%; animation: spin .6s linear infinite;
  margin-right: 5px; vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }

.empty { color: var(--dim); font-style: italic; padding: 14px; text-align: center; }
.empty-small { color: var(--dim); padding: 6px; text-align: center; font-size: 11.5px; }
hr.sep { border: 0; border-top: 1px solid var(--border-soft); margin: 10px 0; }
.flex-between { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
kbd {
  display: inline-block; background: var(--panel-3);
  border: 1px solid var(--border); border-bottom-width: 2px;
  border-radius: 3px; padding: 1px 5px;
  font-size: 10.5px; font-family: ui-monospace, monospace;
}

/* xref banner */
.xref-msg {
  font-size: 11px; color: var(--warn);
  background: var(--warn-bg); padding: 4px 7px;
  border-radius: 4px; margin-top: 3px;
  border-left: 2px solid var(--warn);
}
"""

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>PlantSEED Curation</title>
<link rel="stylesheet" href="/static/app.css">
</head>
<body>

<div class="app">

  <!-- ====== SIDEBAR =================================================== -->
  <aside class="sidebar">
    <div class="brand">Plant<span class="accent">SEED</span> Curation</div>
    <nav id="sidebar-nav">
      <button data-tab="curate"  class="active">Curate</button>
      <button data-tab="staging">Staging  <span class="label-count" id="staging-count">0</span></button>
      <button data-tab="files">Files</button>
      <button data-tab="apply">Apply Updates</button>
      <button data-tab="browse">Browse DB</button>
      <button data-tab="help">Help</button>
    </nav>
    <div class="footer">
      <div class="user-block">
        <div class="row">
          <span class="dim">curator</span>
          <button class="theme-toggle" id="btn-theme" title="Toggle light/dark">dark</button>
        </div>
        <div class="username" id="user-text" title="Click to change">loading…</div>
      </div>
    </div>
  </aside>

  <!-- ====== MAIN ====================================================== -->
  <div class="main">

    <!-- Top bar -->
    <div class="topbar">
      <div class="section-title" id="section-title">Curate</div>
      <div class="status">
        <span class="item"><span class="label">file:</span>
          <span class="value muted" id="file-text">none</span></span>
        <span class="item"><span class="label">db:</span>
          <span class="value" id="db-text">0 roles</span></span>
        <span class="item"><span class="label">EC:</span>
          <span class="value muted" id="ec-text">loading…</span></span>
        <button class="reload" id="btn-reload">reload</button>
      </div>
    </div>

    <!-- Content area -->
    <div class="content">

      <!-- =========== CURATE ========================================= -->
      <section id="tab-curate" class="section active">
        <div class="grid-curate">

          <!-- Col 1: Find or current enzyme -->
          <div class="panel">
            <h2>Enzyme</h2>
            <div id="enzyme-picker" class="col-stack" style="flex:1;">
              <input type="search" id="search-input" autocomplete="off"
                     placeholder="Search by name, EC, or gene…">
              <div class="help">
                <kbd>↑↓</kbd> navigate, <kbd>Enter</kbd> select. Prefix:
                <code>ec:</code> <code>feature:</code> <code>rxn:</code>
                <code>subsystem:</code> <code>class:</code> <code>curator:</code>
              </div>
              <div id="results-list" class="results">
                <div class="empty">Type 2+ characters to search.</div>
              </div>
              <div class="toolbar">
                <button id="btn-novel" class="btn small">+ Novel enzyme</button>
                <span class="subtle" id="search-summary" style="margin-left:auto;"></span>
              </div>
            </div>
            <div id="enzyme-current" style="display:none;">
              <div class="current-enzyme">
                <span class="label">Working on</span>
                <span class="name" id="current-name"></span>
                <button class="btn small" id="btn-switch-enzyme">Switch</button>
              </div>
              <div id="current-warnings"></div>
              <div id="current-actions" class="col-stack" style="margin-top:8px;">
                <label>Action</label>
                <select id="action-select"></select>
                <div class="help" id="action-help"></div>
                <div id="action-body" style="margin-top:8px;"></div>
                <hr class="sep">
                <div class="toolbar">
                  <button id="btn-stage" class="btn primary">Stage row(s)</button>
                  <button id="btn-stage-preview" class="btn small">Refresh preview</button>
                </div>
                <span id="stage-status" class="subtle"></span>
              </div>
            </div>
          </div>

          <!-- Col 2: Role record -->
          <div class="panel">
            <h2>Current record</h2>
            <div class="panel-scroll">
              <div id="role-detail"><div class="empty">Pick an enzyme on the left.</div></div>
            </div>
          </div>

          <!-- Col 3: Live preview -->
          <div class="panel">
            <h2>Preview after staged + new rows</h2>
            <div class="panel-scroll">
              <div id="preview-area"><div class="empty">Fill the action form to see preview.</div></div>
            </div>
          </div>

        </div>
      </section>

      <!-- =========== STAGING ======================================== -->
      <section id="tab-staging" class="section">
        <div class="col-stack" style="flex:1;">
          <div class="panel" style="flex-shrink:0;">
            <h2 class="flex-between">
              <span>Staged rows <span class="dim" id="staging-count-2">(0)</span></span>
            </h2>
            <div class="toolbar">
              <button id="btn-staging-save"   class="btn primary">Append to current file</button>
              <button id="btn-staging-saveas" class="btn">Append to another file…</button>
              <button id="btn-staging-clear"  class="btn">Clear</button>
              <button id="btn-staging-copy"   class="btn">Copy TSV</button>
            </div>
          </div>
          <div class="panel" style="flex:1; min-height:0;">
            <div class="panel-scroll">
              <div id="staging-list"></div>
            </div>
          </div>
          <details style="background:var(--panel); border:1px solid var(--border); border-radius:6px; padding:8px 12px;">
            <summary class="subtle" style="cursor:pointer;">Raw TSV preview</summary>
            <pre id="staging-raw" class="mono" style="margin-top:6px; background:var(--code-bg); padding:8px; border-radius:4px; font-size:11.5px; max-height:200px; overflow:auto;"></pre>
          </details>
        </div>
      </section>

      <!-- =========== FILES ========================================== -->
      <section id="tab-files" class="section">
        <div class="grid-files">

          <!-- Left -->
          <div class="col-stack">
            <div class="panel" style="flex:1; min-height:0;">
              <h2 class="flex-between">
                <span>Your files</span>
                <button id="btn-new-file" class="btn small primary">+ New</button>
              </h2>
              <div class="panel-scroll">
                <div id="files-list"></div>
              </div>
            </div>
            <div class="panel" style="flex-shrink:0; max-height:35%;">
              <h2>Other curators</h2>
              <div class="panel-scroll">
                <div id="other-curators" class="subtle">none</div>
              </div>
            </div>
          </div>

          <!-- Right (editor) -->
          <div class="panel">
            <h2 class="flex-between">
              <span id="file-editor-title">No file open</span>
              <span class="right actions">
                <button id="btn-file-save"   class="btn small primary">Save</button>
                <button id="btn-file-apply"  class="btn small">Apply…</button>
                <button id="btn-file-delete" class="btn small danger">Delete</button>
              </span>
            </h2>
            <div class="subtle" id="file-editor-path" style="margin-bottom:8px;"></div>
            <div id="file-banner"></div>
            <div class="panel-scroll" style="flex:1;">
              <div id="file-rows"></div>
              <details style="margin-top:10px;">
                <summary class="subtle" style="cursor:pointer;">Raw editor (advanced)</summary>
                <textarea id="file-raw-editor" spellcheck="false" style="margin-top:6px; min-height:200px;"></textarea>
              </details>
            </div>
          </div>
        </div>
      </section>

      <!-- =========== APPLY ========================================== -->
      <section id="tab-apply" class="section">
        <div class="col-stack" style="flex:1;">
          <div class="panel" style="flex-shrink:0;">
            <h2>Apply TSV to PlantSEED_Roles.json</h2>
            <div class="help">
              Equivalent to <code>Update_Enzymes_in_PlantSEED.py</code>. Dry-run first to see the diff;
              the real run writes the JSON atomically.
            </div>
            <div style="display:grid; grid-template-columns: 200px 1fr; gap:8px; margin-top:10px; align-items:start;">
              <div>
                <label>Source</label>
                <select id="apply-source">
                  <option value="staging">Staged rows</option>
                  <option value="file">Saved file</option>
                  <option value="paste">Paste TSV</option>
                </select>
              </div>
              <div>
                <div id="apply-file-pick" style="display:none;">
                  <label>File</label>
                  <select id="apply-file-select"></select>
                </div>
                <div id="apply-paste" style="display:none;">
                  <label>TSV</label>
                  <textarea id="apply-paste-area" spellcheck="false" placeholder="Paste TSV rows…"></textarea>
                </div>
              </div>
            </div>
            <hr class="sep">
            <div class="toolbar">
              <button id="btn-apply-dry"  class="btn">Dry run</button>
              <button id="btn-apply-real" class="btn warn">Apply (write JSON)</button>
              <span id="apply-status" class="subtle" style="margin-left:auto;"></span>
            </div>
          </div>
          <div class="panel" style="flex:1; min-height:0;">
            <h2>Result</h2>
            <div class="panel-scroll">
              <div id="apply-result"><div class="empty">Run a dry-run or apply to see results.</div></div>
            </div>
          </div>
        </div>
      </section>

      <!-- =========== BROWSE ========================================= -->
      <section id="tab-browse" class="section">
        <div class="grid-browse">

          <!-- Facets (left, full height, scrolls) -->
          <div class="panel">
            <h2 class="flex-between">
              <span>Filters</span>
              <button id="btn-browse-clear" class="btn tiny">clear</button>
            </h2>
            <input type="search" id="browse-input" placeholder="Filter by name…" style="flex-shrink:0;">
            <div class="panel-scroll" style="margin-top:8px;">
              <div id="browse-facets"></div>
            </div>
          </div>

          <!-- Role list (middle, full height, scrolls) -->
          <div class="panel">
            <h2 class="flex-between"><span>Roles</span>
              <span class="dim" id="browse-count">0</span></h2>
            <div class="panel-scroll">
              <div id="browse-list"></div>
            </div>
          </div>

          <!-- Role detail (right) -->
          <div class="panel">
            <h2>Detail</h2>
            <div class="panel-scroll">
              <div id="browse-detail"><div class="empty">Click a role to view it.</div></div>
            </div>
          </div>

        </div>
      </section>

      <!-- =========== HELP =========================================== -->
      <section id="tab-help" class="section">
        <div class="panel scroll" style="flex:1;">
          <h2>Help &amp; reference</h2>
          <div class="panel-scroll">
            <h3 style="font-size:13px; margin-top:0;">Workflow</h3>
            <ol style="margin-top:4px;">
              <li><b>Curate</b> — search, pick an enzyme, choose an action, fill the form. Stage the row(s).</li>
              <li>After staging the form clears but the enzyme stays selected. Click <b>Switch</b> for a different one.</li>
              <li><b>Staging</b> — review/edit pending rows. <b>Append to current file</b> writes them to disk.</li>
              <li><b>Files</b> — open any of your TSV files. Edit row-by-row or in the raw editor.</li>
              <li><b>Apply Updates</b> — runs the equivalent of <code>Update_Enzymes_in_PlantSEED.py</code>. Shows per-role before/after diffs.</li>
            </ol>

            <h3 style="font-size:13px;">Search syntax</h3>
            <p>Plain text matches role names AND feature lists, so a gene id like <code>AT3G30775</code> surfaces its role(s). Prefix to scope:</p>
            <ul>
              <li><code>ec:1.1.1</code> — EC number</li>
              <li><code>feature:AT3G30775</code> — feature substring</li>
              <li><code>rxn:rxn00001</code> — reaction</li>
              <li><code>subsystem:fatty</code> — subsystem substring</li>
              <li><code>class:amino</code> — class substring</li>
              <li><code>curator:samseaver</code> — curator</li>
              <li><code>type:universal</code> — role type</li>
            </ul>

            <h3 style="font-size:13px;">Compartments (ModelSEED Plant)</h3>
            <p>When ADDing features or reactions the extra column is <b>optional</b>. Blank → compartment <code>c</code> (cytosol) with source <code>Assumed</code>.</p>
            <div id="help-compartments" class="compartment-grid"></div>

            <h3 style="font-size:13px;">Actions</h3>
            <div id="help-actions"></div>

            <h3 style="font-size:13px;">Keyboard shortcuts</h3>
            <ul>
              <li><kbd>/</kbd> focus search</li>
              <li><kbd>g</kbd> then <kbd>c/s/f/a/b/h</kbd> jump tabs</li>
              <li><kbd>Ctrl</kbd>+<kbd>Enter</kbd> stage current action</li>
              <li><kbd>Esc</kbd> close modal</li>
            </ul>
          </div>
        </div>
      </section>

    </div><!-- /.content -->
  </div><!-- /.main -->
</div><!-- /.app -->

<div id="modal-root"></div>
<div id="toast-stack" class="toast-stack"></div>

<script src="/static/app.js"></script>
</body>
</html>
"""

INDEX_JS = r"""
// PlantSEED Curation Dashboard frontend (v4).
// Vanilla JS, no build step.

const $  = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

const state = {
  user: null,
  currentFile: null,
  selection: null,
  actionMeta: null,
  staging: [],
  fileEditor: { name: null, content: "", rows: [] },
  allRoles: [],
  facets: {},
  browseFilters: { name: "", subsystems: new Set(), types: new Set(), curators: new Set(), include: null, transporter: null },
  searchSelectedIdx: -1,
  searchFlat: [],
};

const TAB_TITLES = {
  curate:  "Curate",
  staging: "Staging",
  files:   "Files",
  apply:   "Apply Updates",
  browse:  "Browse Database",
  help:    "Help",
};

// ---------- HTTP & helpers ------------------------------------------------
async function api(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method || "GET",
    headers: opts.body ? { "Content-Type": "application/json" } : {},
    body: opts.body ? JSON.stringify(opts.body) : null,
  });
  const text = await res.text();
  let json;
  try { json = JSON.parse(text); } catch { json = { error: text || `HTTP ${res.status}` }; }
  if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
  return json;
}
const esc = (s) => (s == null ? "" : String(s))
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
function highlight(text, q) {
  if (!q || q.length < 2 || q.includes(":")) return esc(text);
  const safe = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return esc(text).replace(new RegExp("(" + safe + ")", "ig"), "<mark>$1</mark>");
}
const bytesFmt = (n) => n < 1024 ? n + " B" : n < 1024*1024 ? (n/1024).toFixed(1) + " KB" : (n/1024/1024).toFixed(2) + " MB";

// ---------- Theme toggle --------------------------------------------------
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("plantseed-theme", theme);
  $("#btn-theme").textContent = theme;
}
function initTheme() {
  const saved = localStorage.getItem("plantseed-theme");
  const prefersLight = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
  applyTheme(saved || (prefersLight ? "light" : "dark"));
  $("#btn-theme").addEventListener("click", () => {
    const cur = document.documentElement.getAttribute("data-theme") || "dark";
    applyTheme(cur === "dark" ? "light" : "dark");
  });
}

// ---------- Toast & Modal -------------------------------------------------
function toast(message, kind = "") {
  const t = document.createElement("div");
  t.className = "toast " + (kind || "");
  t.textContent = message;
  $("#toast-stack").appendChild(t);
  setTimeout(() => { t.style.opacity = "0"; t.style.transform = "translateY(8px)"; }, 3000);
  setTimeout(() => t.remove(), 3400);
}
const Modal = {
  current: null,
  show({ title, bodyHTML, actions, onMount }) {
    this.hide();
    const wrap = document.createElement("div");
    wrap.className = "modal-backdrop";
    wrap.innerHTML = `<div class="modal">
      <div class="modal-head"><h3>${esc(title)}</h3><button data-close>×</button></div>
      <div class="modal-body">${bodyHTML}</div>
      <div class="modal-foot">${(actions || []).map((a,i) => `<button class="btn ${a.kind || ""}" data-act="${i}">${esc(a.label)}</button>`).join("")}</div>
    </div>`;
    $("#modal-root").appendChild(wrap);
    this.current = wrap;
    const body = wrap.querySelector(".modal-body");
    onMount && onMount(body);
    wrap.querySelector("[data-close]").addEventListener("click", () => this.hide());
    wrap.addEventListener("click", e => { if (e.target === wrap) this.hide(); });
    (actions || []).forEach((a,i) => {
      const btn = wrap.querySelector(`[data-act="${i}"]`);
      btn?.addEventListener("click", () => a.onClick && a.onClick(body));
    });
    setTimeout(() => wrap.querySelector("input, textarea, select")?.focus(), 30);
  },
  hide() { this.current && this.current.remove(); this.current = null; },
  confirm(message) {
    return new Promise(resolve => this.show({
      title: "Confirm",
      bodyHTML: `<div>${esc(message)}</div>`,
      actions: [
        { label: "Cancel", onClick: () => { this.hide(); resolve(false); } },
        { label: "OK", kind: "warn", onClick: () => { this.hide(); resolve(true); } },
      ],
    }));
  },
  prompt(message, defaultValue = "") {
    return new Promise(resolve => this.show({
      title: "Input",
      bodyHTML: `<label>${esc(message)}</label><input type="text" id="mp-val" value="${esc(defaultValue)}">`,
      actions: [
        { label: "Cancel", onClick: () => { this.hide(); resolve(null); } },
        { label: "OK", kind: "primary", onClick: (b) => { const v = b.querySelector("#mp-val").value; this.hide(); resolve(v); } },
      ],
      onMount: (b) => b.querySelector("#mp-val").addEventListener("keydown", e => {
        if (e.key === "Enter") { const v = e.target.value; this.hide(); resolve(v); }
      }),
    }));
  }
};
document.addEventListener("keydown", e => { if (e.key === "Escape") Modal.hide(); });

// ---------- Tabs (sidebar nav) + shortcuts --------------------------------
function showTab(name) {
  $$(".section").forEach(s => s.classList.remove("active"));
  $$(".sidebar nav button").forEach(b => b.classList.toggle("active", b.dataset.tab === name));
  $(`#tab-${name}`)?.classList.add("active");
  $("#section-title").textContent = TAB_TITLES[name] || name;
  if (name === "browse")  renderBrowse();
  if (name === "staging") renderStaging();
  if (name === "files")   refreshFiles();
  if (name === "apply")   refreshApplyTab();
  if (name === "help")    renderHelp();
}
$$(".sidebar nav button").forEach(b => b.addEventListener("click", () => showTab(b.dataset.tab)));

let chord = null;
document.addEventListener("keydown", e => {
  const t = e.target.tagName;
  if (t === "INPUT" || t === "TEXTAREA" || t === "SELECT") return;
  if (e.key === "/") { e.preventDefault(); showTab("curate"); $("#search-input").focus(); return; }
  if (e.key === "g") { chord = "g"; setTimeout(() => chord = null, 1000); return; }
  if (chord === "g") {
    const map = { c:"curate", s:"staging", f:"files", a:"apply", b:"browse", h:"help" };
    if (map[e.key]) showTab(map[e.key]);
    chord = null;
  }
});

// ---------- Bootstrap -----------------------------------------------------
async function init() {
  initTheme();
  try {
    state.actionMeta = await api("/api/actions");
    const status = await api("/api/status");
    setDbCount(status.roles);
    setExpasy(status.expasy);
    pollExpasy();
    await ensureUser();
    await refreshFiles();
    renderHelp();
  } catch (e) {
    toast("Init failed: " + e.message, "bad");
  }
}

function setDbCount(n) { $("#db-text").textContent = `${n.toLocaleString()} roles`; }
function setExpasy(e) {
  const el = $("#ec-text");
  if (e.status === "loaded") { el.textContent = `${e.count.toLocaleString()}`; el.classList.remove("muted"); }
  else if (e.status === "loading") { el.innerHTML = `<span class="spinner"></span>loading`; el.classList.add("muted"); }
  else if (e.status === "error") { el.textContent = "error"; el.classList.add("muted"); el.title = e.error || ""; }
  else { el.textContent = "idle"; el.classList.add("muted"); }
}
async function pollExpasy() {
  for (let i = 0; i < 60; i++) {
    const s = await api("/api/status");
    setExpasy(s.expasy);
    if (s.expasy.status === "loaded" || s.expasy.status === "error") return;
    await new Promise(r => setTimeout(r, 2000));
  }
}

async function ensureUser() {
  const u = await api("/api/user");
  if (!sessionStorage.getItem("user_confirmed")) {
    const chosen = await showUserModal(u);
    if (chosen) {
      const r = await api("/api/user", { method: "POST", body: { username: chosen, display_name: u.display_name } });
      state.user = { ...u, ...r, dir_name: r.username };
    } else {
      state.user = u;
    }
    sessionStorage.setItem("user_confirmed", "1");
  } else {
    state.user = u;
  }
  renderUserBadge();
}
function renderUserBadge() {
  const u = state.user;
  $("#user-text").textContent = `@${u.dir_name}`;
  $("#user-text").title = `display: ${u.display_name || "?"}\nsource: ${u.source}\nemail: ${u.email || "?"}\n(click to switch)`;
}
function showUserModal(detected) {
  return new Promise(resolve => {
    const opts = detected.candidates.map((c, i) =>
      `<label style="display:flex; align-items:center; gap:8px; padding:5px 0; cursor:pointer;">
        <input type="radio" name="ghu" value="${esc(c.value)}" ${i===0?"checked":""} style="width:auto;">
        <span><code>@${esc(c.value)}</code> <span class="dim" style="font-size:11px;">(${esc(c.source)})</span></span>
      </label>`).join("");
    Modal.show({
      title: "Confirm your GitHub username",
      bodyHTML: `<div class="help" style="margin-bottom:10px;">Pick one of the detected candidates, or type your own. Your files live in <code>Curators/&lt;username&gt;/</code>.</div>
        ${opts}
        <label>Or enter manually</label>
        <input type="text" id="user-custom" placeholder="GitHub username">`,
      actions: [
        { label: "Use this", kind: "primary", onClick: (body) => {
            const custom = body.querySelector("#user-custom").value.trim();
            const radio = body.querySelector('input[name=ghu]:checked');
            Modal.hide();
            resolve(custom || (radio ? radio.value : detected.username));
        } },
      ],
    });
  });
}
$("#user-text").addEventListener("click", async () => {
  const u = await api("/api/user");
  const chosen = await showUserModal(u);
  if (!chosen) return;
  const r = await api("/api/user", { method: "POST", body: { username: chosen, display_name: u.display_name } });
  state.user = { ...u, ...r, dir_name: r.username };
  renderUserBadge();
  await refreshFiles();
  toast(`Switched to @${r.username}`, "good");
});
$("#btn-reload").addEventListener("click", async () => {
  const r = await api("/api/reload", { method: "POST" });
  setDbCount(r.roles);
  state.allRoles = [];
  toast(`Reloaded ${r.roles} roles`, "good");
});

// ---------- Search --------------------------------------------------------
let searchDebounce = null;
$("#search-input").addEventListener("input", e => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => runSearch(e.target.value), 180);
});
$("#search-input").addEventListener("keydown", e => {
  const flat = state.searchFlat;
  if (!flat.length) return;
  if (e.key === "ArrowDown") {
    e.preventDefault();
    state.searchSelectedIdx = Math.min(flat.length - 1, state.searchSelectedIdx + 1);
    paintResultSelection();
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    state.searchSelectedIdx = Math.max(0, state.searchSelectedIdx - 1);
    paintResultSelection();
  } else if (e.key === "Enter" && state.searchSelectedIdx >= 0) {
    e.preventDefault();
    const sel = flat[state.searchSelectedIdx];
    selectEnzyme(sel.name, sel.kind === "expasy" ? "expasy" : "plantseed");
  }
});
function paintResultSelection() {
  const items = $$(".results .item");
  items.forEach((el, i) => el.classList.toggle("selected", i === state.searchSelectedIdx));
  items[state.searchSelectedIdx]?.scrollIntoView({ block: "nearest" });
}

async function runSearch(q) {
  q = (q || "").trim();
  const root = $("#results-list");
  const summary = $("#search-summary");
  state.searchSelectedIdx = -1;
  state.searchFlat = [];
  if (q.length < 2 && !q.includes(":")) {
    root.innerHTML = `<div class="empty">Type 2+ characters to search.</div>`;
    summary.textContent = "";
    return;
  }
  root.innerHTML = `<div class="empty"><span class="spinner"></span>Searching…</div>`;
  const r = await api(`/api/search?q=${encodeURIComponent(q)}`);
  const total = r.totals.name + r.totals.expasy + r.totals.by_feature;
  let summaryText = `${r.totals.name} name`;
  if (r.totals.by_feature) summaryText += ` · ${r.totals.by_feature} feat`;
  if (r.totals.expasy) summaryText += ` · ${r.totals.expasy} EC`;
  summary.textContent = summaryText;

  if (total === 0) {
    root.innerHTML = `<div class="empty">No matches. Use <b>+ Novel</b> to create a new one.</div>`;
    return;
  }
  const psNames = new Set(r.name);
  const parts = [];

  if (r.name.length) {
    parts.push(`<div class="group-header">PlantSEED — ${r.totals.name}</div>`);
    r.name.forEach(n => {
      parts.push(`<div class="item" data-name="${esc(n)}" data-source="plantseed"><span class="tag plant">PS</span><span class="name">${highlight(n, q)}</span></div>`);
      state.searchFlat.push({ kind: "plantseed", name: n });
    });
  }
  if (r.by_feature.length) {
    parts.push(`<div class="group-header">By feature — ${r.totals.by_feature}</div>`);
    r.by_feature.forEach(item => {
      parts.push(`<div class="item" data-name="${esc(item.role)}" data-source="plantseed">
        <span class="tag plant">PS</span>
        <span class="name">${esc(item.role)}<span class="sub">via ${highlight(item.feature, q)}</span></span>
      </div>`);
      state.searchFlat.push({ kind: "feature", name: item.role });
    });
  }
  if (r.expasy.length) {
    parts.push(`<div class="group-header">Expasy — ${r.totals.expasy}</div>`);
    r.expasy.forEach(n => {
      const already = psNames.has(n);
      parts.push(`<div class="item" data-name="${esc(n)}" data-source="${already ? "plantseed" : "expasy"}">
        <span class="tag ${already ? "plant" : "expasy"}">${already ? "PS" : "EC"}</span>
        <span class="name">${highlight(n, q)}</span>
        <span class="meta">${already ? "in DB" : "novel"}</span>
      </div>`);
      state.searchFlat.push({ kind: already ? "plantseed" : "expasy", name: n });
    });
  }
  root.innerHTML = parts.join("");
  $$(".item", root).forEach((it, idx) => {
    it.addEventListener("click", () => selectEnzyme(it.dataset.name, it.dataset.source));
    it.addEventListener("mouseenter", () => { state.searchSelectedIdx = idx; paintResultSelection(); });
  });
}
$("#btn-novel").addEventListener("click", async () => {
  const name = await Modal.prompt("Full name for the new enzyme (include EC, e.g. … (EC 1.2.3.4)):");
  if (!name?.trim()) return;
  selectEnzyme(name.trim(), "novel");
});

// ---------- Enzyme selection ----------------------------------------------
async function selectEnzyme(name, source) {
  const isExisting = source === "plantseed";
  let role = null, warnings = [];
  if (isExisting) {
    const r = await api(`/api/role?name=${encodeURIComponent(name)}`);
    if (r.exists) { role = r.entry; warnings = r.warnings; }
    else source = "novel";
  }
  state.selection = { name, source, isNew: !isExisting, role, warnings };
  $("#enzyme-picker").style.display = "none";
  $("#enzyme-current").style.display = "";
  $("#current-name").innerHTML = `${esc(name)} ${
    source === "plantseed" ? '<span class="tag plant">in PlantSEED</span>' :
    source === "expasy"    ? '<span class="tag expasy">Expasy → CREATE</span>' :
                             '<span class="tag new">novel → CREATE</span>'
  }`;
  $("#current-warnings").innerHTML = warnings.length
    ? `<div class="banner warn">Empty required: ${warnings.map(esc).join(", ")}. Use ADD to populate.</div>` : "";
  $("#role-detail").innerHTML = renderRoleCard(role);
  populateActionSelect();
  renderActionBody();
  await refreshPreview();
}
$("#btn-switch-enzyme").addEventListener("click", () => switchEnzyme());
function switchEnzyme() {
  state.selection = null;
  $("#enzyme-picker").style.display = "";
  $("#enzyme-current").style.display = "none";
  $("#role-detail").innerHTML = `<div class="empty">Pick an enzyme on the left.</div>`;
  $("#preview-area").innerHTML = `<div class="empty">Fill the action form to see preview.</div>`;
  $("#search-input").focus();
  $("#search-input").select();
}

function renderRoleCard(role) {
  if (!role) return `<div class="empty">No PlantSEED record yet — will be created on NEW.</div>`;
  const order = ["role", "abstract_enzyme", "include", "type", "is_transporter",
                 "subsystems", "classes", "reactions", "features", "localization",
                 "publications", "curators", "kbase_id"];
  const fields = Object.keys(role);
  const sorted = [...order.filter(k => fields.includes(k)), ...fields.filter(k => !order.includes(k))];
  return `<div class="role-card">${sorted.map(k => renderField(k, role[k])).join("")}</div>`;
}
function renderField(k, v) {
  let html;
  if (v === null || v === undefined || v === "") html = `<span class="v empty">(empty)</span>`;
  else if (Array.isArray(v)) {
    html = v.length === 0 ? `<span class="v empty">[ ]</span>`
      : `<div class="v">${v.map(it => `<code>${esc(it)}</code>`).join("")}</div>`;
  } else if (typeof v === "object") {
    const lines = Object.entries(v).map(([kk, vv]) =>
      `<div class="obj-line"><code>${esc(kk)}</code> ${esc(typeof vv === "object" ? JSON.stringify(vv) : vv)}</div>`);
    html = Object.keys(v).length === 0 ? `<span class="v empty">{ }</span>`
      : `<div class="v">${lines.join("")}</div>`;
  } else if (typeof v === "boolean") html = `<span class="v"><code>${v ? "true" : "false"}</code></span>`;
  else html = `<span class="v">${esc(v)}</span>`;
  return `<div class="field"><div class="k">${esc(k)}</div>${html}</div>`;
}

// ---------- Action form ---------------------------------------------------
function populateActionSelect() {
  const sel = $("#action-select");
  const all = state.actionMeta.actions.map(a => a.name);
  const opts = state.selection?.isNew ? ["NEW", ...all.filter(a => a !== "NEW")] : all.filter(a => a !== "NEW");
  sel.innerHTML = opts.map(a => `<option value="${a}">${a}</option>`).join("");
  sel.onchange = () => { renderActionBody(); refreshPreviewDebounced(); };
}
const actionMetaFor = (name) => state.actionMeta?.actions.find(a => a.name === name);

function renderActionBody() {
  const action = $("#action-select").value;
  const meta = actionMetaFor(action);
  $("#action-help").textContent = meta?.description || "";
  const body = $("#action-body");
  if (action === "NEW") {
    body.innerHTML = `<div class="help">A blank role will be created with schema defaults.</div>`;
    bindAutoPreview(); return;
  }
  if (action === "UPDATE") {
    body.innerHTML = `<label>New enzyme name</label>
      <input type="text" id="payload-new_name" placeholder="… (EC 1.2.3.4)">
      <div class="field-error" data-err="new_name"></div>`;
    bindAutoPreview(); return;
  }
  if (action === "CHANGE" || action === "ASSIGN") {
    body.innerHTML = `<label>Field</label>
      <select id="payload-field">${meta.fields.map(f => `<option>${f}</option>`).join("")}</select>
      <div class="field-error" data-err="field"></div>
      <label>Value</label><div id="payload-value-wrap"></div>
      <div class="field-error" data-err="value"></div>`;
    function paintValue() {
      const f = $("#payload-field").value;
      const wrap = $("#payload-value-wrap");
      if (state.actionMeta.scalar_types[f] === "bool") {
        wrap.innerHTML = `<select id="payload-value"><option value="true">true</option><option value="false">false</option></select>`;
      } else {
        wrap.innerHTML = `<input type="text" id="payload-value" placeholder="value">`;
      }
      $("#payload-value").addEventListener("input", refreshPreviewDebounced);
      $("#payload-value").addEventListener("change", refreshPreviewDebounced);
    }
    paintValue();
    $("#payload-field").onchange = () => { paintValue(); refreshPreviewDebounced(); };
    return;
  }
  if (action === "RELOCATE") {
    body.innerHTML = `<label>Field</label>
      <select id="payload-field">${meta.fields.map(f => `<option>${f}</option>`).join("")}</select>
      <div class="field-error" data-err="field"></div>
      <label>Old key</label><input type="text" id="payload-old" placeholder="Existing key">
      <div class="field-error" data-err="old"></div>
      <label>New key</label><input type="text" id="payload-new" placeholder="Replacement key">
      <div class="field-error" data-err="new"></div>`;
    bindAutoPreview(); return;
  }
  body.innerHTML = `<label>Field</label>
    <select id="payload-field">${meta.fields.map(f => `<option>${f}</option>`).join("")}</select>
    <div class="field-error" data-err="field"></div>
    <div id="payload-entries" style="margin-top:8px;"></div>
    <button id="btn-add-entry" class="btn small" type="button">+ Add entry</button>
    <div id="action-extra-help" class="help"></div>`;
  $("#payload-field").onchange = () => { renderEntriesArea(); refreshPreviewDebounced(); paintExtraHelp(); };
  $("#btn-add-entry").onclick = () => { addEntryRow(); refreshPreviewDebounced(); };
  renderEntriesArea(); paintExtraHelp();
}

function bindAutoPreview() {
  $$("#action-body input, #action-body select").forEach(el => {
    el.addEventListener("input", refreshPreviewDebounced);
    el.addEventListener("change", refreshPreviewDebounced);
  });
}
function paintExtraHelp() {
  const action = $("#action-select").value;
  const field  = $("#payload-field")?.value;
  const help = $("#action-extra-help");
  if (!help) return;
  if (action === "ADD" && (field === "features" || field === "reactions")) {
    help.innerHTML = `Extra column is <b>optional</b>. Blank → compartment <code>${state.actionMeta.default_compartment}</code> (cytosol).`;
  } else { help.innerHTML = ""; }
}
function renderEntriesArea() {
  $("#payload-entries").innerHTML = "";
  addEntryRow();
}
function addEntryRow() {
  const action = $("#action-select").value;
  const field = $("#payload-field").value;
  const root = $("#payload-entries");
  const cfg = action === "ADD" ? state.actionMeta.multi_col[field] : null;
  const div = document.createElement("div");
  div.className = "entry-row";
  let extraHTML = "";
  if (cfg) {
    if (cfg.extra_kind === "compartment_only") {
      const opts = state.actionMeta.compartments.map(c => `<option value="${c.id}">${c.id} (${esc(c.name)})</option>`).join("");
      extraHTML = `<div class="entry-extra-wrap">
        <select class="entry-extra"><option value="">— (default: c)</option>${opts}</select>
      </div>`;
    } else if (cfg.extra_kind === "compartment_source") {
      const cptOpts = state.actionMeta.compartments.map(c => `<option value="${c.id}">${c.id} (${esc(c.name)})</option>`).join("");
      extraHTML = `<div class="entry-extra-wrap">
        <select class="entry-cpt"><option value="">— (default: c)</option>${cptOpts}</select>
        <input type="text" class="entry-src" placeholder="source (PPDB, SUBA…)">
      </div>`;
    } else {
      extraHTML = `<input type="text" class="entry-extra" placeholder="${esc(cfg.extra_label)}">`;
    }
  }
  div.innerHTML = `
    <input type="text" class="entry-value" placeholder="${esc(cfg ? cfg.primary_label : "value")}">
    ${extraHTML}
    <button class="btn tiny rm-btn" data-act="rm" title="Remove" type="button">×</button>`;
  root.appendChild(div);
  div.querySelector("[data-act=rm]").onclick = () => { div.remove(); refreshPreviewDebounced(); };
  div.querySelectorAll("input, select").forEach(el => el.addEventListener("input", refreshPreviewDebounced));
  const valInp = div.querySelector(".entry-value");
  valInp.addEventListener("blur", () => maybeShowXref(field, valInp));
}
async function maybeShowXref(field, inp) {
  const v = (inp.value || "").trim();
  if (!v || v.length < 3) return;
  if (!["features", "reactions", "publications"].includes(field)) return;
  const mode = field === "features" ? "substring" : "exact";
  const exclude = state.selection?.name || "";
  try {
    const r = await api(`/api/xref?field=${field}&value=${encodeURIComponent(v)}&mode=${mode}&exclude=${encodeURIComponent(exclude)}`);
    const row = inp.closest(".entry-row");
    row.querySelector(".xref-msg")?.remove();
    if (r.matches.length) {
      const div = document.createElement("div");
      div.className = "xref-msg";
      div.innerHTML = `<b>${esc(v)}</b> appears in ${r.total} other role(s): ${r.matches.slice(0, 3).map(esc).join(", ")}${r.total > 3 ? "…" : ""}`;
      row.appendChild(div);
    }
  } catch (e) {}
}
function gatherPayload() {
  const action = $("#action-select").value;
  if (action === "NEW") return {};
  if (action === "UPDATE") return { new_name: $("#payload-new_name")?.value || "" };
  const field = $("#payload-field")?.value;
  if (action === "CHANGE" || action === "ASSIGN") return { field, value: $("#payload-value")?.value || "" };
  if (action === "RELOCATE") return { field, old: $("#payload-old")?.value || "", new: $("#payload-new")?.value || "" };
  if (action === "ADD" || action === "REMOVE") {
    const entries = $$("#payload-entries .entry-row").map(div => {
      const value = div.querySelector(".entry-value")?.value || "";
      let extra = "";
      const cpt = div.querySelector(".entry-cpt");
      const src = div.querySelector(".entry-src");
      if (cpt) {
        const c = cpt.value, s = src?.value?.trim() || "";
        if (c && s) extra = `${c}:${s}`;
        else if (c) extra = c;
        else if (s) extra = `:${s}`;
      } else {
        extra = div.querySelector(".entry-extra")?.value || "";
      }
      return { value, extra };
    });
    return { field, entries };
  }
  return {};
}
function showFieldErrors(errors) {
  $$("#action-body .field-error").forEach(el => el.textContent = "");
  $$("#action-body input, #action-body select").forEach(el => el.classList.remove("invalid"));
  errors.forEach(e => {
    $(`[data-err="${e.field}"]`)?.replaceChildren(document.createTextNode(e.message));
    const inpId = "payload-" + e.field.replace(/[\[\].]/g, "-");
    $("#" + inpId)?.classList.add("invalid");
  });
}

// ---------- Preview -------------------------------------------------------
let previewDebounce = null;
function refreshPreviewDebounced() { clearTimeout(previewDebounce); previewDebounce = setTimeout(refreshPreview, 250); }
async function refreshPreview() {
  if (!state.selection) return;
  const area = $("#preview-area");
  area.innerHTML = `<div class="empty"><span class="spinner"></span>Computing…</div>`;
  const pendingRows = state.staging.filter(r => r.split("\t")[0] === state.selection.name);
  let currentRows = [];
  try {
    const action = $("#action-select")?.value;
    if (action) {
      const r = await api("/api/build", { method: "POST",
        body: { action, enzyme: state.selection.name, payload: gatherPayload() } });
      if (r.errors && r.errors.length) showFieldErrors(r.errors);
      else { showFieldErrors([]); currentRows = r.rows; }
    }
  } catch (e) {}
  const rows = [...pendingRows, ...currentRows];
  if (rows.length === 0) { area.innerHTML = `<div class="empty">Fill the action form to see preview.</div>`; return; }
  try {
    const p = await api("/api/preview", { method: "POST",
      body: { enzyme: state.selection.name, rows } });
    const parts = [];
    if (p.errors?.length)   parts.push(`<div class="banner bad"><b>Errors</b><br>${p.errors.map(esc).join("<br>")}</div>`);
    if (p.warnings?.length) parts.push(`<div class="banner warn"><b>${p.warnings.length} warning(s)</b><br>${p.warnings.slice(0,5).map(esc).join("<br>")}${p.warnings.length>5?"<br>… +"+(p.warnings.length-5)+" more":""}</div>`);
    if (p.renamed_to)       parts.push(`<div class="banner info">Would rename to <code>${esc(p.renamed_to)}</code></div>`);
    if (!p.after) parts.push(`<div class="empty">Would not produce a role record.</div>`);
    else parts.push(renderDiff(p.before, p.after));
    area.innerHTML = parts.join("");
  } catch (e) {
    area.innerHTML = `<div class="banner bad">Preview error: ${esc(e.message)}</div>`;
  }
}
function renderDiff(before, after) {
  if (!after) return `<div class="empty">No after state</div>`;
  const fields = new Set([...Object.keys(before || {}), ...Object.keys(after)]);
  const order = ["role", "abstract_enzyme", "include", "type", "is_transporter",
                 "subsystems", "classes", "reactions", "features", "localization",
                 "publications", "curators", "kbase_id"];
  const sorted = [...order.filter(k => fields.has(k)), ...[...fields].filter(k => !order.includes(k))];
  const parts = [];
  for (const k of sorted) {
    const a = before?.[k], b = after?.[k];
    const aStr = a === undefined ? "(absent)" : JSON.stringify(a, null, 2);
    const bStr = b === undefined ? "(absent)" : JSON.stringify(b, null, 2);
    if (aStr === bStr) continue;
    parts.push(`<div class="diff-section">
      <div class="field-name">${esc(k)}</div>
      <div class="diff-line rem">- ${esc(aStr)}</div>
      <div class="diff-line add">+ ${esc(bStr)}</div>
    </div>`);
  }
  return parts.length ? parts.join("") : `<div class="empty">No changes (no-op).</div>`;
}

// ---------- Stage ---------------------------------------------------------
$("#btn-stage").addEventListener("click", stageCurrentAction);
$("#btn-stage-preview").addEventListener("click", refreshPreview);
async function stageCurrentAction() {
  if (!state.selection) { toast("Pick an enzyme first", "warn"); return; }
  try {
    const action = $("#action-select").value;
    const r = await api("/api/build", { method: "POST",
      body: { action, enzyme: state.selection.name, payload: gatherPayload() } });
    if (r.errors?.length) { showFieldErrors(r.errors); toast("Fix highlighted fields", "bad"); return; }
    if (r.warnings?.length) r.warnings.forEach(w => toast(w, "warn"));
    if (!r.rows.length) { toast("No rows produced", "bad"); return; }
    state.staging.push(...r.rows);
    refreshStagingBadge();
    $("#stage-status").textContent = `Staged ${r.rows.length}. ${state.staging.length} row(s) pending. Enzyme stays selected.`;
    toast(`Staged ${r.rows.length} row(s)`, "good");
    renderActionBody();
    refreshPreview();
  } catch (e) { toast(e.message, "bad"); }
}
document.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && $("#tab-curate").classList.contains("active")) {
    e.preventDefault();
    stageCurrentAction();
  }
});
function refreshStagingBadge() {
  const c = state.staging.length;
  const b = $("#staging-count");
  b.classList.toggle("visible", c > 0);
  b.textContent = c;
  $("#staging-count-2").textContent = `(${c})`;
}

// ---------- Staging tab ---------------------------------------------------
function renderStaging() {
  refreshStagingBadge();
  const root = $("#staging-list");
  if (state.staging.length === 0) {
    root.innerHTML = `<div class="empty">No staged rows. Use Curate to add some.</div>`;
    $("#staging-raw").textContent = "";
    return;
  }
  root.innerHTML = state.staging.map((r, i) => stagingCardHTML(r, i)).join("");
  $$(".staging-card [data-act]", root).forEach(b => {
    b.addEventListener("click", () => {
      const idx = parseInt(b.closest(".staging-card").dataset.idx);
      const act = b.dataset.act;
      if (act === "del") { state.staging.splice(idx, 1); renderStaging(); return; }
      if (act === "up" && idx > 0)   { [state.staging[idx-1], state.staging[idx]] = [state.staging[idx], state.staging[idx-1]]; renderStaging(); return; }
      if (act === "down" && idx < state.staging.length - 1) { [state.staging[idx+1], state.staging[idx]] = [state.staging[idx], state.staging[idx+1]]; renderStaging(); return; }
      if (act === "edit") stagingEditModal(idx);
    });
  });
  $("#staging-raw").textContent = state.staging.join("\n");
}
function stagingCardHTML(row, idx) {
  const c = row.split("\t");
  const enzyme = esc(c[0] || "");
  const action = esc(c[1] || "?");
  const field  = c[2] ? `<span class="f">${esc(c[2])}</span>` : "";
  const value  = c[3] ? ` <span class="v">${esc(c[3])}</span>` : "";
  const extra  = c[4] ? ` <span class="x">${esc(c[4])}</span>` : "";
  return `<div class="staging-card" data-idx="${idx}">
    <span class="num">${idx + 1}</span>
    <span class="tag action ${action}">${action}</span>
    <div class="body"><span class="e">${enzyme}</span> ${field}${value}${extra}</div>
    <div class="acts">
      <button class="btn tiny" data-act="up"   title="Up">↑</button>
      <button class="btn tiny" data-act="down" title="Down">↓</button>
      <button class="btn tiny" data-act="edit" title="Edit">edit</button>
      <button class="btn tiny danger" data-act="del" title="Delete">×</button>
    </div>
  </div>`;
}
function stagingEditModal(idx) {
  const cols = state.staging[idx].split("\t");
  const opts = state.actionMeta.actions.map(a => `<option ${a.name === cols[1] ? "selected" : ""}>${a.name}</option>`).join("");
  Modal.show({
    title: `Edit staged row #${idx + 1}`,
    bodyHTML: `
      <label>Enzyme</label><input id="e-enz" type="text" value="${esc(cols[0] || "")}">
      <label>Action</label><select id="e-act">${opts}</select>
      <label>Field</label><input id="e-fld" type="text" value="${esc(cols[2] || "")}">
      <label>Value</label><input id="e-val" type="text" value="${esc(cols[3] || "")}">
      <label>Extra (optional)</label><input id="e-ext" type="text" value="${esc(cols[4] || "")}">`,
    actions: [
      { label: "Cancel", onClick: () => Modal.hide() },
      { label: "Save", kind: "primary", onClick: (b) => {
          const nc = [b.querySelector("#e-enz").value, b.querySelector("#e-act").value];
          const f = b.querySelector("#e-fld").value;
          const v = b.querySelector("#e-val").value;
          const x = b.querySelector("#e-ext").value;
          if (f) nc.push(f); if (v) nc.push(v); if (x) nc.push(x);
          state.staging[idx] = nc.join("\t");
          Modal.hide(); renderStaging(); toast("Row updated", "good");
      } },
    ]
  });
}
$("#btn-staging-clear").addEventListener("click", async () => {
  if (!state.staging.length) return;
  if (await Modal.confirm(`Discard all ${state.staging.length} staged row(s)?`)) {
    state.staging = []; renderStaging();
  }
});
$("#btn-staging-save").addEventListener("click", async () => {
  if (!state.staging.length) { toast("Nothing to save", "warn"); return; }
  if (!state.currentFile) {
    const name = await Modal.prompt("No current file. Filename:", "Updates.tsv");
    if (!name) return;
    await api("/api/file/create", { method: "POST", body: { user: state.user.dir_name, name } });
    setCurrentFile(name.endsWith(".tsv") ? name : name + ".tsv");
  }
  const r = await api("/api/file/append", { method: "POST",
    body: { user: state.user.dir_name, name: state.currentFile.name, rows: state.staging } });
  toast(`Appended ${r.appended} row(s) to ${state.currentFile.name}`, "good");
  state.staging = []; renderStaging();
  await refreshFiles();
});
$("#btn-staging-saveas").addEventListener("click", async () => {
  if (!state.staging.length) { toast("Nothing to save", "warn"); return; }
  const name = await Modal.prompt("Filename:", "Updates.tsv");
  if (!name) return;
  const fname = name.endsWith(".tsv") ? name : name + ".tsv";
  await api("/api/file/create", { method: "POST", body: { user: state.user.dir_name, name: fname } });
  const r = await api("/api/file/append", { method: "POST",
    body: { user: state.user.dir_name, name: fname, rows: state.staging } });
  toast(`Appended ${r.appended} row(s) to ${fname}`, "good");
  setCurrentFile(fname);
  state.staging = []; renderStaging();
  await refreshFiles();
});
$("#btn-staging-copy").addEventListener("click", () => {
  if (!state.staging.length) { toast("Nothing to copy", "warn"); return; }
  navigator.clipboard.writeText(state.staging.join("\n"))
    .then(() => toast("Copied", "good"))
    .catch(e => toast("Copy failed: " + e.message, "bad"));
});

// ---------- Files tab -----------------------------------------------------
async function refreshFiles() {
  if (!state.user) return;
  const r = await api(`/api/files?user=${encodeURIComponent(state.user.dir_name)}`);
  renderFilesList(r.files, r.dir);
  renderOtherCurators(r.all_curators);
  populateApplyFileSelect(r.files);
  if (state.fileEditor.name && r.files.some(f => f.name === state.fileEditor.name)) {
    openFile(state.fileEditor.name);
  } else if (!state.currentFile && r.files.length > 0) {
    setCurrentFile(r.files[0].name);
  } else if (state.currentFile && !r.files.some(f => f.name === state.currentFile.name)) {
    setCurrentFile(r.files[0]?.name || null);
  }
}
function setCurrentFile(name) {
  state.currentFile = name ? { name } : null;
  const el = $("#file-text");
  el.textContent = name || "none";
  el.classList.toggle("muted", !name);
}
function renderFilesList(files, dir) {
  const root = $("#files-list");
  if (files.length === 0) { root.innerHTML = `<div class="empty-small">No files yet.</div>`; return; }
  root.innerHTML = `<div class="dim" style="font-size:11px; margin-bottom:6px; word-break:break-all;">${esc(dir)}</div>` +
    files.map(f => `
      <div class="list-item ${state.currentFile?.name === f.name ? "selected" : ""}" data-name="${esc(f.name)}">
        <span class="name">${esc(f.name)}</span>
        <span class="meta">${f.rows}r · ${bytesFmt(f.size)}</span>
        <div class="acts">
          <button class="btn tiny" data-act="select">${state.currentFile?.name === f.name ? "✓" : "set"}</button>
        </div>
      </div>`).join("");
  $$(".list-item", root).forEach(it => it.addEventListener("click", e => {
    if (e.target.dataset.act === "select") { setCurrentFile(it.dataset.name); refreshFiles(); return; }
    openFile(it.dataset.name);
  }));
}
function renderOtherCurators(list) {
  const root = $("#other-curators");
  if (!list?.length) { root.innerHTML = `<div class="empty-small">none</div>`; return; }
  root.innerHTML = list.map(c => `
    <div class="list-item" data-user="${esc(c.name)}">
      <span class="name">@${esc(c.name)}</span>
      <span class="meta">${c.n_files}f</span>
    </div>`).join("");
  $$(".list-item", root).forEach(it => it.addEventListener("click", async () => {
    const u = it.dataset.user;
    const r = await api(`/api/files?user=${encodeURIComponent(u)}`);
    Modal.show({
      title: `@${u} (read-only)`,
      bodyHTML: r.files.length ? r.files.map(f => `<div class="list-item"><span class="name">${esc(f.name)}</span><span class="meta">${f.rows} rows · ${bytesFmt(f.size)}</span></div>`).join("") : `<div class="empty-small">No files</div>`,
      actions: [{ label: "Close", onClick: () => Modal.hide() }],
    });
  }));
}
$("#btn-new-file").addEventListener("click", async () => {
  const name = await Modal.prompt("New filename (.tsv appended if missing):", "Updates.tsv");
  if (!name) return;
  const r = await api("/api/file/create", { method: "POST", body: { user: state.user.dir_name, name } });
  toast(`Created ${r.name}`, "good");
  setCurrentFile(r.name);
  await refreshFiles();
  openFile(r.name);
});
async function openFile(name) {
  const r = await api(`/api/file?user=${encodeURIComponent(state.user.dir_name)}&name=${encodeURIComponent(name)}`);
  state.fileEditor = { name, content: r.content, rows: r.rows };
  $("#file-editor-title").textContent = name;
  $("#file-editor-path").textContent = `Curators/${state.user.dir_name}/${name}`;
  $("#file-raw-editor").value = r.content;
  renderFileRows(r.rows);
  $("#file-banner").innerHTML = "";
}
function renderFileRows(rows) {
  const root = $("#file-rows");
  if (!rows.length) { root.innerHTML = `<div class="empty-small">File is empty.</div>`; return; }
  const acts = state.actionMeta.actions.map(a => a.name);
  root.innerHTML = `<table class="editor-table"><thead><tr>
    <th class="num">#</th><th>Enzyme</th><th>Action</th><th>Field</th><th>Value</th><th>Extra</th><th></th>
  </tr></thead><tbody>${rows.map((r, i) => `
    <tr data-idx="${i}">
      <td class="num">${r.lineno}</td>
      <td><input type="text" data-k="enzyme" value="${esc(r.enzyme || "")}"></td>
      <td><select data-k="action">${acts.map(a => `<option ${a === r.action ? "selected" : ""}>${a}</option>`).join("")}</select></td>
      <td><input type="text" data-k="field" value="${esc(r.field || "")}"></td>
      <td><input type="text" data-k="value" value="${esc(r.value || "")}"></td>
      <td><input type="text" data-k="extra" value="${esc(r.extra || "")}"></td>
      <td><button class="btn tiny danger" data-act="del">×</button></td>
    </tr>`).join("")}</tbody></table>`;
  $$("[data-act=del]", root).forEach(b => b.addEventListener("click", () => { b.closest("tr").remove(); syncRaw(); }));
  $$("input, select", root).forEach(el => el.addEventListener("input", syncRaw));
}
function syncRaw() {
  const lines = $$("#file-rows tbody tr").map(tr => {
    const enz = tr.querySelector('[data-k="enzyme"]').value;
    const act = tr.querySelector('[data-k="action"]').value;
    const f = tr.querySelector('[data-k="field"]').value;
    const v = tr.querySelector('[data-k="value"]').value;
    const x = tr.querySelector('[data-k="extra"]').value;
    const cols = [enz, act];
    if (f) cols.push(f); if (v) cols.push(v); if (x) cols.push(x);
    return cols.join("\t");
  });
  $("#file-raw-editor").value = lines.join("\n") + (lines.length ? "\n" : "");
  $("#file-banner").innerHTML = `<div class="banner warn">Unsaved changes — click Save to write to disk.</div>`;
}
$("#btn-file-save").addEventListener("click", async () => {
  if (!state.fileEditor.name) { toast("No file open", "warn"); return; }
  await api("/api/file/save", { method: "POST",
    body: { user: state.user.dir_name, name: state.fileEditor.name, content: $("#file-raw-editor").value } });
  toast("Saved", "good");
  await refreshFiles();
  await openFile(state.fileEditor.name);
});
$("#btn-file-apply").addEventListener("click", () => {
  if (!state.fileEditor.name) { toast("No file open", "warn"); return; }
  showTab("apply");
  $("#apply-source").value = "file";
  $("#apply-source").dispatchEvent(new Event("change"));
  $("#apply-file-select").value = state.fileEditor.name;
});
$("#btn-file-delete").addEventListener("click", async () => {
  if (!state.fileEditor.name) return;
  if (!(await Modal.confirm(`Delete ${state.fileEditor.name}? This cannot be undone.`))) return;
  await api("/api/file/delete", { method: "POST",
    body: { user: state.user.dir_name, name: state.fileEditor.name } });
  toast("Deleted", "good");
  state.fileEditor = { name: null, content: "", rows: [] };
  $("#file-editor-title").textContent = "No file open";
  $("#file-rows").innerHTML = "";
  $("#file-raw-editor").value = "";
  await refreshFiles();
});

// ---------- Apply tab -----------------------------------------------------
function populateApplyFileSelect(files) {
  $("#apply-file-select").innerHTML = files.map(f => `<option value="${esc(f.name)}">${esc(f.name)} (${f.rows} rows)</option>`).join("");
}
$("#apply-source").addEventListener("change", () => {
  const v = $("#apply-source").value;
  $("#apply-file-pick").style.display = v === "file" ? "" : "none";
  $("#apply-paste").style.display = v === "paste" ? "" : "none";
});
function refreshApplyTab() { refreshFiles(); $("#apply-source").dispatchEvent(new Event("change")); }
async function gatherApplyTSV() {
  const v = $("#apply-source").value;
  if (v === "staging") return state.staging.join("\n");
  if (v === "paste") return $("#apply-paste-area").value;
  if (v === "file") {
    const name = $("#apply-file-select").value;
    if (!name) throw new Error("Select a file");
    const r = await api(`/api/file?user=${encodeURIComponent(state.user.dir_name)}&name=${encodeURIComponent(name)}`);
    return r.content;
  }
  return "";
}
async function runApply(dryRun) {
  const tsv = await gatherApplyTSV();
  if (!tsv.trim()) { toast("Nothing to apply", "warn"); return; }
  if (!dryRun && !(await Modal.confirm("Apply changes to PlantSEED_Roles.json?"))) return;
  $("#apply-status").innerHTML = `<span class="spinner"></span>${dryRun ? "Dry-running" : "Applying"}…`;
  $("#apply-result").innerHTML = "";
  try {
    const r = await api("/api/apply", { method: "POST",
      body: { user: state.user.dir_name, tsv, dry_run: dryRun } });
    renderApplyResult(r, dryRun);
    $("#apply-status").textContent = `${r.errors.length} error · ${r.warnings.length} warning · ${r.summary?.touched?.length || 0} role(s) ${dryRun ? "would be" : ""} touched`;
    if (!dryRun && r.errors.length === 0 && r.summary?.touched?.length) {
      toast(`Database updated — ${r.summary.touched.length} role(s)`, "good");
      const s = await api("/api/status");
      setDbCount(s.roles);
      state.allRoles = [];
    } else if (dryRun) {
      toast("Dry-run complete", "good");
    } else if (r.errors.length) {
      toast("Apply blocked by errors", "bad");
    }
  } catch (e) {
    $("#apply-result").innerHTML = `<div class="banner bad">ERROR: ${esc(e.message)}</div>`;
    $("#apply-status").textContent = "failed";
    toast("Apply failed: " + e.message, "bad");
  }
}
function renderApplyResult(r, dryRun) {
  const root = $("#apply-result");
  const parts = [];
  if (r.errors.length)   parts.push(`<div class="banner bad"><b>${r.errors.length} error(s)</b><br>${r.errors.map(esc).join("<br>")}</div>`);
  if (r.warnings.length) parts.push(`<div class="banner warn"><b>${r.warnings.length} warning(s)</b><br>${r.warnings.slice(0,10).map(esc).join("<br>")}${r.warnings.length>10?"<br>… +"+(r.warnings.length-10)+" more":""}</div>`);
  if (r.info.length)     parts.push(`<div class="banner good">${r.info.map(esc).join("<br>")}</div>`);
  const s = r.summary || {};
  if (s.touched?.length) {
    parts.push(`<div class="subtle" style="margin-bottom:10px;"><b>${s.touched.length}</b> role(s) ${dryRun ? "would be" : "were"} touched${s.new?.length ? ` · <b>${s.new.length}</b> new` : ""}${Object.keys(s.renamed||{}).length ? ` · <b>${Object.keys(s.renamed).length}</b> rename(s)` : ""}</div>`);
  }
  if (r.role_diffs?.length) {
    r.role_diffs.forEach(d => parts.push(renderRoleDiffCard(d)));
  } else if (!r.errors.length && !r.warnings.length) {
    parts.push(`<div class="empty">No changes.</div>`);
  }
  root.innerHTML = parts.join("");
}
function renderRoleDiffCard(d) {
  const tag = d.is_new ? '<span class="tag NEW">NEW</span>'
    : d.renamed_from ? `<span class="tag UPDATE">RENAMED from ${esc(d.renamed_from)}</span>`
    : '<span class="tag CHANGE">MODIFIED</span>';
  return `<div class="diff-card">
    <h4>${tag} <span>${esc(d.role)}</span></h4>
    ${renderDiff(d.before, d.after)}
  </div>`;
}
$("#btn-apply-dry").addEventListener("click", () => runApply(true));
$("#btn-apply-real").addEventListener("click", () => runApply(false));

// ---------- Browse --------------------------------------------------------
let browseTimer = null;
async function renderBrowse() {
  if (state.allRoles.length === 0) {
    const r = await api("/api/roles/all");
    state.allRoles = r.roles;
    state.facets = r.facets;
  }
  renderBrowseFacets();
  applyBrowseFilters();
  $("#browse-input").oninput = e => {
    clearTimeout(browseTimer);
    browseTimer = setTimeout(() => { state.browseFilters.name = e.target.value; applyBrowseFilters(); }, 150);
  };
}
function renderBrowseFacets() {
  const root = $("#browse-facets");
  const f = state.browseFilters;
  function chips(field, title, values) {
    if (!values?.length) return "";
    return `<div class="facet-section">
      <h4>${title}</h4>
      <div class="facet-options">
        ${values.map(v => `<span class="facet-chip ${f[field].has(v) ? "active" : ""}" data-field="${field}" data-val="${esc(v)}">${esc(v)}</span>`).join("")}
      </div>
    </div>`;
  }
  root.innerHTML =
    `<div class="facet-section">
      <h4>Include</h4>
      <span class="facet-chip ${f.include === true ? "active" : ""}"  data-toggle="include" data-val="true">included</span>
      <span class="facet-chip ${f.include === false ? "active" : ""}" data-toggle="include" data-val="false">excluded</span>
    </div>
    <div class="facet-section">
      <h4>Transporter</h4>
      <span class="facet-chip ${f.transporter === true ? "active" : ""}"  data-toggle="transporter" data-val="true">yes</span>
      <span class="facet-chip ${f.transporter === false ? "active" : ""}" data-toggle="transporter" data-val="false">no</span>
    </div>` +
    chips("types", "Type", state.facets.types) +
    chips("subsystems", `Subsystem (${state.facets.subsystems?.length || 0})`, state.facets.subsystems) +
    chips("curators",   `Curator (${state.facets.curators?.length || 0})`,    state.facets.curators);
  $$(".facet-chip[data-field]", root).forEach(c => c.addEventListener("click", () => {
    const set = state.browseFilters[c.dataset.field];
    set.has(c.dataset.val) ? set.delete(c.dataset.val) : set.add(c.dataset.val);
    renderBrowseFacets(); applyBrowseFilters();
  }));
  $$(".facet-chip[data-toggle]", root).forEach(c => c.addEventListener("click", () => {
    const key = c.dataset.toggle, v = c.dataset.val === "true";
    state.browseFilters[key] = state.browseFilters[key] === v ? null : v;
    renderBrowseFacets(); applyBrowseFilters();
  }));
}
$("#btn-browse-clear").addEventListener("click", () => {
  state.browseFilters = { name: "", subsystems: new Set(), types: new Set(), curators: new Set(), include: null, transporter: null };
  $("#browse-input").value = "";
  renderBrowseFacets(); applyBrowseFilters();
});
function applyBrowseFilters() {
  const f = state.browseFilters;
  const q = (f.name || "").toLowerCase();
  const filtered = state.allRoles.filter(r => {
    if (q && !r.role.toLowerCase().includes(q)) return false;
    if (f.types.size > 0 && !f.types.has(r.type)) return false;
    if (f.subsystems.size > 0 && !r.subsystems.some(s => f.subsystems.has(s))) return false;
    if (f.curators.size > 0 && !r.curators.some(c => f.curators.has(c))) return false;
    if (f.include !== null && Boolean(r.include) !== f.include) return false;
    if (f.transporter !== null && Boolean(r.is_transporter) !== f.transporter) return false;
    return true;
  });
  $("#browse-count").textContent = `${filtered.length} / ${state.allRoles.length}`;
  const root = $("#browse-list");
  if (!filtered.length) { root.innerHTML = `<div class="empty">No matches</div>`; return; }
  const visible = filtered.slice(0, 500);
  root.innerHTML = visible.map(r => `
    <div class="list-item" data-name="${esc(r.role)}">
      <span class="name">${esc(r.role)}</span>
      <span class="meta">${r.n_features}f · ${r.n_reactions}r${r.is_transporter ? " · trans" : ""}${!r.include ? " · excl" : ""}</span>
    </div>`).join("") +
    (filtered.length > visible.length ? `<div class="empty-small">${filtered.length - visible.length} more — refine your filter</div>` : "");
  $$(".list-item", root).forEach(it => it.addEventListener("click", async () => {
    $$(".list-item", root).forEach(i => i.classList.remove("selected"));
    it.classList.add("selected");
    const r = await api(`/api/role?name=${encodeURIComponent(it.dataset.name)}`);
    if (r.exists) $("#browse-detail").innerHTML = renderRoleCard(r.entry);
  }));
}

// ---------- Help ----------------------------------------------------------
function renderHelp() {
  if (!state.actionMeta) return;
  $("#help-actions").innerHTML = state.actionMeta.actions.map(a => `
    <div style="display:flex; align-items:flex-start; gap:10px; padding:5px 0; border-bottom:1px solid var(--border-soft);">
      <span style="min-width:80px;"><span class="tag action ${esc(a.name)}">${esc(a.name)}</span></span>
      <div>
        <div>${esc(a.description)}</div>
        ${a.fields.length ? `<div class="dim" style="font-size:11px;">Fields: ${a.fields.map(esc).join(", ")}</div>` : ""}
      </div>
    </div>`).join("");
  $("#help-compartments").innerHTML = state.actionMeta.compartments.map(c =>
    `<div class="compartment-chip"><span class="id">${esc(c.id)}</span> ${esc(c.name)}</div>`).join("");
}

init();
"""


# ============================================================================
# Main entry
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="PlantSEED Curation Tool Dashboard.")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="port (default 8765, auto-fallback)")
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    args = parser.parse_args()

    STORE.load_roles()
    STORE.load_schema()
    STORE.start_load_expasy()

    port = find_free_port(args.host, args.port)
    server = ThreadedServer((args.host, port), Handler)
    url = f"http://{args.host}:{port}/"

    print()
    print("PlantSEED Curation Dashboard")
    print(f"  Roles:    {len(STORE.roles)} loaded from {os.path.relpath(ROLES_FILE, BASE_DIR)}")
    print(f"  Curators: {os.path.relpath(CURATORS_DIR, BASE_DIR)}")
    print(f"  Expasy:   downloading/parsing in background")
    print(f"  URL:      {url}")
    print(f"  Stop:     Ctrl-C")
    print()

    if not args.no_browser:
        try: webbrowser.open(url)
        except Exception: pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
