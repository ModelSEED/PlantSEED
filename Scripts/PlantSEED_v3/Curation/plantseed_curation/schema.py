"""Schema loading and per-role validation helpers."""

import copy
import os

import yaml

from . import paths
from .constants import AUTO_POPULATED_FIELDS, TYPE_MAP


class IssueCollector:
    """Small accumulator passed through the apply pipeline so warnings,
    errors, and informational messages can be reported together at the end
    rather than printed inline."""

    def __init__(self):
        self.warnings = []
        self.errors = []
        self.info = []

    def warn(self, m):
        self.warnings.append(m)

    def error(self, m):
        self.errors.append(m)

    def log(self, m):
        self.info.append(m)


def load_schema(schema_path=None):
    """Read the schema YAML and normalise each entry into the dict shape the
    rest of the package expects. Returns {} if the file is missing."""
    path = schema_path or paths.SCHEMA_FILE
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    normalized = {}
    for key, rules in raw.items():
        normalized[key] = {
            "type":       TYPE_MAP.get(rules.get("type"), str),
            "type_name":  rules.get("type"),
            "default":    rules.get("default"),
            "required":   rules.get("required", False),
            "depends_on": rules.get("depends_on"),
        }
    return normalized


def default_role_from_schema(schema):
    """Build the default empty-role dict from the schema's required fields."""
    return {k: copy.deepcopy(rules["default"]) for k, rules in schema.items() if rules["required"]}


def required_empty_fields(role_entry, schema):
    """List required fields on this role that still hold their default value."""
    out = []
    if not schema or not role_entry:
        return out
    for field, rules in schema.items():
        if not rules["required"] or field in AUTO_POPULATED_FIELDS:
            continue
        actual = role_entry.get(field)
        default = rules["default"]
        if isinstance(default, (list, dict)) and actual == default:
            out.append(field)
        elif isinstance(default, str) and actual == default == "":
            out.append(field)
    return out


def ensure_schema_defaults(entry, schema):
    """Fill any missing required field with its schema default. Returns the
    list of warning messages for the caller to surface."""
    msgs = []
    role_name = entry.get("role", "<unnamed>")
    for key, rules in schema.items():
        if rules["required"] and key not in entry:
            entry[key] = copy.deepcopy(rules["default"])
            msgs.append(f"[DEFAULT FILLED] '{key}' missing in '{role_name}' — set to default")
    return msgs


def validate_dependencies(entry, schema):
    """Check schema `depends_on:` blocks. Non-restrictive — returns warnings,
    never mutates the entry."""
    msgs = []
    role_name = entry.get("role", "<unnamed>")
    for key, rules in schema.items():
        dep = rules.get("depends_on")
        if not dep or key not in entry:
            continue
        value = entry[key]
        if not isinstance(value, dict):
            continue
        if "keys_from" in dep:
            allowed = set()
            for source_field in dep["keys_from"]:
                allowed.update(entry.get(source_field, []))
            for k in value.keys():
                if k not in allowed:
                    msgs.append(
                        f"[DEP] '{key}' key '{k}' in '{role_name}' "
                        f"not present in {dep['keys_from']}"
                    )
        if "inner_keys_from" in dep:
            allowed = set()
            for source_field in dep["inner_keys_from"]:
                allowed.update(entry.get(source_field, []))
            for outer_k, inner in value.items():
                if not isinstance(inner, dict):
                    continue
                for k in inner.keys():
                    if k not in allowed:
                        msgs.append(
                            f"[DEP] '{key}.{outer_k}' inner key '{k}' in "
                            f"'{role_name}' not present in {dep['inner_keys_from']}"
                        )
    return msgs
