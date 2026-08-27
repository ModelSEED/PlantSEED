"""Registration documents for the harnesses that consume this server.

Generated from the registry rather than hand-written, for the reason the whole
delivery package exists: a hand-maintained manifest is a second declaration of
the same capability, and it goes stale the first time a parameter changes.

Two output forms, and which one to use is a security decision, not a taste one:

* `mcp_json()` — the ecosystem-standard `.mcp.json`. **Use this whenever the
  server needs a token.** KIND*AI imports `.mcp.json` automatically and runs
  `${VAR:-default}` expansion over the entry, including headers, so the token
  stays in the environment.
* `king_plugin()` — a `type:"mcp"` plugin manifest, for a server that needs no
  credential. KIND*AI passes a plugin manifest's `headers` through
  **unexpanded** (`mcp_servers.py::_server_config`), so a bearer token written
  here would be a committed secret rather than a reference to one.

Authorization is the same ORCID-attributed act either way; the only difference
is where the secret lives.
"""

from __future__ import annotations

import json

from plantseed_core import registry

__all__ = ["SERVER_ID", "tool_names", "mcp_json", "king_plugin", "main"]

SERVER_ID = "plantseed"
TITLE = "PlantSEED (plant metabolic curation + reconstruction)"

#: Tools that are not capability invocations — the read-only curation lookups.
#: Kept here so both documents and the server agree on one list.
QUERY_TOOLS = ("search_roles", "get_role", "list_subsystems",
               "subsystem_reactions", "get_complex")


def tool_names() -> list[str]:
    """Every tool this server exposes: one per declared capability that has an
    invoker, plus the query tools."""
    from . import invoke

    return sorted([n for n in registry.names() if n in invoke.INVOKERS]
                  + list(QUERY_TOOLS))


def _description() -> str:
    """The fallback summary a harness shows before it has read the owner's own
    description. The depth — when / guarantee — travels on
    `plantseed capabilities --json`, which is where the contract expects it."""
    caps = registry.all_capabilities()
    verbs = ", ".join(c.name for c in caps) or "none"
    return (
        "Curated plant primary metabolism: reconstruct a metabolic model from "
        f"an annotated genome ({verbs}), and query the PlantSEED curation — "
        "roles, subsystems, complexes, and their curated subcellular "
        "compartments. Deterministic and offline; makes no external calls."
    )


def mcp_json(url: str, token_env: str = "PLANTSEED_MCP_TOKEN") -> dict:
    """A `.mcp.json` document declaring this server.

    `token_env` names an environment variable, and the reference to it is what
    gets written — never its value. Pass `token_env=""` for an unauthenticated
    route.
    """
    entry: dict = {"type": "http", "url": url, "description": _description()}
    if token_env:
        entry["headers"] = {"Authorization": f"Bearer ${{{token_env}}}"}
    return {"mcpServers": {SERVER_ID: entry}}


def king_plugin(url: str) -> dict:
    """A KIND*AI `type:"mcp"` plugin manifest. No credential — see the module
    docstring for why a token belongs in `.mcp.json` instead."""
    return {
        "type": "mcp",
        "id": SERVER_ID,
        "title": TITLE,
        "description": _description(),
        "server": {"transport": "http", "url": url},
        "tools": ["*"],
        # Remote: there is nothing installed locally to detect.
        "present": None,
        "note": (registry.get("reconstruct").guarantee
                 if "reconstruct" in registry.names() else ""),
        # Live-probed against the shipped data, not invented — these are the
        # click-to-fill chips KIND*AI renders on the explorer page, and a chip
        # that returns nothing teaches the wrong thing about the tool.
        "examples": {
            "search_roles": [
                {"label": "peroxidase", "args": {"query": "peroxidase"}},
                {"label": "by subsystem",
                 "args": {"query": "subsystem:Calvin"}},
                {"label": "by gene id", "args": {"query": "AT2G41480"}},
            ],
            "subsystem_reactions": [
                {"label": "Calvin cycle",
                 "args": {"subsystem": "Calvin-Benson-Bassham_cycle"}},
                {"label": "Lignin", "args": {"subsystem": "Lignin_biosynthesis"}},
            ],
            "get_role": [{"label": "by stable id",
                          "args": {"role": "PS_role_1cc588"}}],
            "get_complex": [{"label": "by stable id",
                             "args": {"complex_id": "PS_complex_be6254"}}],
        },
    }


def main(argv=None) -> int:
    """`python -m plantseed_delivery.manifest --url … [--king]` → stdout."""
    import argparse

    ap = argparse.ArgumentParser(
        description="Emit the registration document for the PlantSEED MCP server.")
    ap.add_argument("--url", required=True,
                    help="Where the server is reachable, e.g. http://poplar:8931/mcp")
    ap.add_argument("--king", action="store_true",
                    help="Emit a KIND*AI plugin manifest instead of .mcp.json. "
                         "Only for an unauthenticated route — a plugin "
                         "manifest's headers are not env-expanded.")
    ap.add_argument("--token-env", default="PLANTSEED_MCP_TOKEN",
                    help="Env var holding the bearer token; '' for none.")
    args = ap.parse_args(argv)

    doc = (king_plugin(args.url) if args.king
           else mcp_json(args.url, args.token_env))
    print(json.dumps(doc, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
