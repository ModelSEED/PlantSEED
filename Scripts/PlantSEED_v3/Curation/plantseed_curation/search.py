"""Ranked search across PlantSEED role names, Expasy enzyme entries, and
role features. The dashboard's `:`-prefix field queries are honoured here so
the CLI gets them for free."""

import re


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


def fuzzy_match(term, choices):
    """Simple substring containment — used by the CLI's free-text fallback."""
    t = (term or "").lower()
    return [c for c in choices if t in c.lower()]


def _score_name(role_name, q_lower):
    rn = role_name.lower()
    if rn == q_lower:
        return 1000
    if rn.startswith(q_lower):
        return 700
    for token in re.split(r"[^A-Za-z0-9]+", rn):
        if token.startswith(q_lower):
            return 500
    if q_lower in rn:
        return 300
    return 0


def search_features(roles, q_lower, exclude_roles):
    """Roles whose features substring-match the query.

    Returns [(role_name, matched_feature), ...] in first-match order.
    """
    out, seen = [], set()
    for r in roles:
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
    """Search PlantSEED + Expasy + role-features for `query`. Honours `:`
    field prefixes. `store` is a DataStore (see plantseed_curation.store)."""
    mode, field, value = parse_query(query)
    if not value or (mode == "name" and len(value) < 2):
        return {"name": [], "expasy": [], "by_feature": [],
                "totals": {"name": 0, "expasy": 0, "by_feature": 0},
                "mode": mode, "field": field,
                "expasy_status": store.expasy_status()["status"]}

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
                        ec_matches.append(
                            (900 if e["ec"].startswith(q_lower) else 400, e["label"])
                        )

    name_matches.sort(key=lambda t: -t[0])
    ec_matches.sort(key=lambda t: -t[0])
    name_only = [n for _, n in name_matches]
    ec_only = [n for _, n in ec_matches]

    by_feature_pairs = []
    if mode == "name":
        by_feature_pairs = search_features(store.roles, q_lower, exclude_roles=set(name_only))

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


def find_exact_match(roles, field, value, exclude=None):
    out = []
    for entry in roles:
        role = entry.get("role")
        if role == exclude:
            continue
        items = entry.get(field, [])
        if isinstance(items, list) and value in items:
            out.append(role)
        elif isinstance(items, dict) and value in items:
            out.append(role)
    return out


def find_substring_match(roles, field, substring, exclude=None):
    out = []
    t = (substring or "").lower()
    for entry in roles:
        role = entry.get("role")
        if role == exclude:
            continue
        items = entry.get(field, [])
        if isinstance(items, list):
            for item in items:
                if t in str(item).lower():
                    out.append(role)
                    break
        elif isinstance(items, dict):
            for item in items.keys():
                if t in str(item).lower():
                    out.append(role)
                    break
    return out
