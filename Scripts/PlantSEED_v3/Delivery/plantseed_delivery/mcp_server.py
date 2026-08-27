"""The PlantSEED MCP server.

The only module in this package that imports `mcp`, so everything else stays
testable with the base install and the `[mcp]` extra is genuinely optional.

Tool bodies are explicitly typed rather than generated from
`Capability.input_schema()`, because the SDK derives a tool's schema from the
function signature and offers no hook for supplying one. That leaves two
descriptions of the same parameters, so `tests/test_schema_parity.py` asserts
they agree — the declaration stays authoritative, and a drift is a test
failure rather than a runtime surprise.

Every tool fails soft: a bad input returns `{"error": …}`. An exception here
propagates to the SDK and can take a session's tool call down with a traceback
that means nothing to the model.
"""

from __future__ import annotations

import argparse
import sys

try:                                       # mcp >= 2 renamed FastMCP
    from mcp.server.mcpserver import MCPServer as _Server
except ModuleNotFoundError:                # mcp 1.x, which is what KIND*AI ships
    from mcp.server.fastmcp import FastMCP as _Server  # type: ignore[assignment]

from plantseed_core import registry

from . import invoke, manifest, queries

__all__ = ["build_server", "main"]


def build_server() -> "_Server":
    """Construct the server with every tool registered.

    Separate from `main` so a test can list the tools without opening a socket.
    """
    server = _Server(manifest.SERVER_ID)

    # --- capabilities --------------------------------------------------------
    reconstruct_cap = registry.get("reconstruct")

    @server.tool(name="reconstruct", description=reconstruct_cap.summary)
    def reconstruct(genome: str, template: str | None = None,
                    compartments: str | None = None,
                    model_id: str | None = None) -> dict:
        """Reconstruct a plant primary-metabolism model from an annotated genome.

        Returns counts, a path and a sha256 — not the model, which is far too
        large for a tool result. Read `model_path` if you need the object.
        """
        return invoke.call("reconstruct", genome=genome, template=template,
                           compartments=compartments, model_id=model_id)

    # --- curation lookups ----------------------------------------------------
    @server.tool(name="list_subsystems")
    def list_subsystems() -> dict:
        """Every curated subsystem, role type and curator, with the total role
        count. Call this first: it is the vocabulary the other lookups match
        against, and it is cheap."""
        return queries.list_subsystems()

    @server.tool(name="search_roles")
    def search_roles(query: str, limit: int = 20) -> dict:
        """Ranked search over curated PlantSEED role names.

        Accepts the curation field prefixes as well as plain text — e.g.
        `subsystem:Photosynthesis`, `curator:samseaver`, `ec:1.11.1.7`.
        """
        return queries.search_roles(query, limit)

    @server.tool(name="get_role")
    def get_role(role: str, include_features: bool = False) -> dict:
        """One curated role by name or by `PS_role_*` id: its reactions, its
        curated compartments, its subsystems and pathway classes. Set
        `include_features` for the curated gene ids."""
        return queries.get_role(role, include_features)

    @server.tool(name="subsystem_reactions")
    def subsystem_reactions(subsystem: str) -> dict:
        """Every role and reaction curated into one subsystem, each reaction
        with the compartments it was curated into. Use `list_subsystems` for
        the exact names."""
        return queries.subsystem_reactions(subsystem)

    @server.tool(name="get_complex")
    def get_complex(complex_id: str) -> dict:
        """One curated enzyme complex by `PS_complex_*` id or enzyme name: its
        member roles and its per-compartment reactions."""
        return queries.get_complex(complex_id)

    return server


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="plantseed-mcp",
        description="Serve PlantSEED reconstruction and curation lookups over MCP.")
    ap.add_argument("--transport", default="stdio",
                    choices=("stdio", "sse", "streamable-http"),
                    help="stdio for a locally-launched client; streamable-http "
                         "to be reached over the network (default: stdio).")
    ap.add_argument("--host", default="127.0.0.1",
                    help="Bind address for the http transports. Defaults to "
                         "loopback — put a reverse proxy in front rather than "
                         "binding a shared host's public interface.")
    ap.add_argument("--port", type=int, default=8931)
    ap.add_argument("--list-tools", action="store_true",
                    help="Print the tool names and exit. A readiness check "
                         "that needs no client.")
    args = ap.parse_args(argv)

    server = build_server()

    if args.list_tools:
        for name in manifest.tool_names():
            print(name)
        return 0

    if args.transport != "stdio":
        server.settings.host = args.host
        server.settings.port = args.port
        print(f"[plantseed-mcp] {args.transport} on {args.host}:{args.port}",
              file=sys.stderr, flush=True)

    server.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
