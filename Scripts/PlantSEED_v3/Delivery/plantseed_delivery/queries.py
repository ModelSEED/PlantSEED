"""Read-only lookups over the curated PlantSEED data.

An agent asking "what does PlantSEED know about lignin?" should not have to
read 935 role records to find out, and should not re-derive the answer with
grep — the curated compartment assignment and the stable `PS_role_*` identity
are exactly what a hand-rolled search loses.

Everything here is a pure read. Two consequences worth stating:

* **No network.** `plantseed_curation.search.ranked_search` will also search
  the ExPASy enzyme list, but only once `DataStore.start_load_expasy()` has
  downloaded `enzyme.dat`. This module never calls it. A container that
  downloads during a run is rejected at CTS image review, and two runs of a
  tool that silently depends on a remote file are not the same run.
* **No writes.** Nothing here opens a file for writing, so the writable-root
  contract in `plantseed_core.runtime` has nothing to police.

Reuse over reimplementation: `DataStore` is already a thread-safe, mtime-
checked cache of the role file, and `ranked_search` already understands the
curation dashboard's `:`-prefixed field queries (`subsystem:`, `curator:`, …),
so an agent gets those for free.
"""

from __future__ import annotations

import json
import os
import threading

from plantseed_curation import paths
from plantseed_curation.search import ranked_search
from plantseed_curation.store import DataStore

__all__ = [
    "search_roles", "get_role", "list_subsystems", "subsystem_reactions",
    "get_complex", "reset_cache",
]

_LOCK = threading.RLock()
_STORE: DataStore | None = None
_COMPLEXES: list[dict] | None = None
_COMPLEXES_MTIME: float | None = None


def _store() -> DataStore:
    """One DataStore for the life of the process — the point of a long-lived
    server. `load_roles` re-reads only when the file's mtime moves, so a
    curation merge is picked up without a restart."""
    global _STORE
    with _LOCK:
        if _STORE is None:
            _STORE = DataStore()
        _STORE.load_roles()
        return _STORE


def _complexes() -> list[dict]:
    """The complex file, cached on mtime the same way `DataStore` caches roles.

    Not part of `DataStore`: the curation dashboard it was written for does not
    read complexes, and widening that class from here would be reaching into
    another package's design for our convenience.
    """
    global _COMPLEXES, _COMPLEXES_MTIME
    with _LOCK:
        try:
            mtime = os.path.getmtime(paths.COMPLEXES_FILE)
        except OSError:
            return _COMPLEXES or []
        if _COMPLEXES is None or _COMPLEXES_MTIME != mtime:
            with open(paths.COMPLEXES_FILE) as fh:
                _COMPLEXES = json.load(fh)
            _COMPLEXES_MTIME = mtime
        return _COMPLEXES


def reset_cache() -> None:
    """Drop the caches. For tests that repoint `paths.*` at a fixture."""
    global _STORE, _COMPLEXES, _COMPLEXES_MTIME
    with _LOCK:
        _STORE = None
        _COMPLEXES = None
        _COMPLEXES_MTIME = None


def _role_brief(role: dict) -> dict:
    """The fields worth spending context on. `features` is omitted — 1666 gene
    ids across the role set, and an agent that wants them asks for one role."""
    return {
        "role": role.get("role"),
        "id": role.get("kbase_id"),
        "type": role.get("type", ""),
        "subsystems": list(role.get("subsystems") or []),
        "reactions": list(role.get("reactions") or []),
        "compartments": sorted(role.get("localization") or {}),
        "is_transporter": bool(role.get("is_transporter")),
        "n_features": len(role.get("features") or []),
    }


def search_roles(query: str, limit: int = 20) -> dict:
    """Ranked search over curated role names.

    `query` accepts the curation dashboard's field prefixes — `subsystem:`,
    `curator:`, `ec:`, and the rest — as well as plain text.
    """
    if not isinstance(query, str) or not query.strip():
        return {"error": "query is required"}
    store = _store()
    try:
        hits = ranked_search(store, query)
    except Exception as exc:                        # fail soft: a tool returns
        return {"error": f"search failed: {exc}"}   # an error, it does not 500
    cap = max(1, int(limit))
    names = list(hits.get("name") or [])[:cap]
    totals = hits.get("totals") or {}
    out = {
        "query": query,
        "mode": hits.get("mode"),
        "n_matched": totals.get("name", len(names)),
        "n_returned": len(names),
        "roles": [_role_brief(store.find_role(n)) for n in names
                  if store.find_role(n)],
    }
    # A query that looks like a gene id ("AT2G41480") matches no role *name*
    # but does match a curated feature. Surfacing it is the difference between
    # "PlantSEED knows nothing about this gene" and the truth.
    by_feature = list(hits.get("by_feature") or [])[:cap]
    if by_feature:
        out["matched_by_feature"] = by_feature
        out["n_matched_by_feature"] = totals.get("by_feature", len(by_feature))
    return out


def get_role(role: str, include_features: bool = False) -> dict:
    """One curated role, by role name or by `PS_role_*` id.

    `include_features` adds the curated gene ids (`<species>||<gene>`); the
    largest role has 58 of them, so it is opt-in rather than default.
    """
    if not isinstance(role, str) or not role.strip():
        return {"error": "role is required"}
    store = _store()
    found = store.find_role(role)
    if found is None:                    # not a role name — try the stable id
        with store.lock:
            found = next((dict(r) for r in store.roles
                          if r.get("kbase_id") == role), None)
    if found is None:
        return {"error": f"no curated role named or identified by {role!r}"}

    out = _role_brief(found)
    out.update({
        "abstract_enzyme": found.get("abstract_enzyme", ""),
        "classes": found.get("classes") or {},
        "localization": found.get("localization") or {},
        "curators": list(found.get("curators") or []),
        "publications": list(found.get("publications") or []),
        "include": found.get("include", True),
    })
    if include_features:
        out["features"] = list(found.get("features") or [])
    return out


def list_subsystems() -> dict:
    """Every curated subsystem, type and curator — the orientation call.

    Cheap (117 subsystems) and worth making first: it tells an agent what
    vocabulary `search_roles` and `subsystem_reactions` will actually match.
    """
    store = _store()
    facets = store.facets()
    return {"subsystems": facets["subsystems"], "types": facets["types"],
            "curators": facets["curators"], "n_roles": len(store.roles)}


def subsystem_reactions(subsystem: str) -> dict:
    """The roles and reactions curated into one subsystem.

    This is the lookup that carries the guarantee: the reaction set comes with
    its curated compartments, which is the part a text search over role names
    cannot reproduce.
    """
    if not isinstance(subsystem, str) or not subsystem.strip():
        return {"error": "subsystem is required"}
    store = _store()
    with store.lock:
        members = [dict(r) for r in store.roles
                   if subsystem in (r.get("subsystems") or [])]
    if not members:
        return {"error": f"no curated subsystem named {subsystem!r}",
                "hint": "call list_subsystems for the exact vocabulary"}

    reactions: dict[str, set[str]] = {}
    for role in members:
        for cpt, rxns in (role.get("localization") or {}).items():
            for rxn in rxns:
                reactions.setdefault(rxn, set()).add(cpt)
        for rxn in role.get("reactions") or []:
            reactions.setdefault(rxn, set())
    return {
        "subsystem": subsystem,
        "n_roles": len(members),
        "roles": [_role_brief(r) for r in members],
        "reactions": {r: sorted(c) for r, c in sorted(reactions.items())},
    }


def get_complex(complex_id: str) -> dict:
    """One curated complex, by `PS_complex_*` id or by enzyme name."""
    if not isinstance(complex_id, str) or not complex_id.strip():
        return {"error": "complex_id is required"}
    key = complex_id.strip().lower()
    for c in _complexes():
        if c.get("kbase_id") == complex_id or (c.get("enzyme") or "").lower() == key:
            return {
                "id": c.get("kbase_id"),
                "enzyme": c.get("enzyme"),
                "roles": list(c.get("roles") or []),
                "compartments_reactions": c.get("compartments_reactions") or {},
            }
    return {"error": f"no curated complex named or identified by {complex_id!r}"}
