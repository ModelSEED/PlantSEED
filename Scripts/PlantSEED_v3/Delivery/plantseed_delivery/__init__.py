"""Delivery adapters — PlantSEED as something other than a command line.

Today that is one thing: an MCP server, so a KIND*AI session on the KBase
JupyterServer hub can reach PlantSEED running on poplar. It is a prototype for
the same capabilities running in the CDM Task Service, and the two share more
than they differ — both read the declarations in `plantseed_core.registry`,
both write only where `plantseed_core.runtime` permits, and both ship in the
same container.

Layout, and the reason for it:

    queries     read-only lookups over the curated data (no `mcp` import)
    invoke      running a declared capability in a long-lived process (no `mcp`)
    manifest    the registration documents, generated from the registry (no `mcp`)
    mcp_server  the server itself — the only module that imports `mcp`

Keeping the `mcp` import in one module is what makes the `[mcp]` extra
optional: the base install can still import, test and reason about everything
else. Same reason `plantseed_model.capabilities` avoids importing cobrapy.

This package ships in the wheel, so `Core/tests/test_core_isolation.py` holds
it to the same import rules as the science packages: no KBase clients, no
solara, no pyspark, no modelseedpy. An adapter may know about a platform's
shape — which is why the CTS and KIND*AI constraints are named in these
docstrings — but it may not import that platform's code.
"""

from .manifest import SERVER_ID, king_plugin, mcp_json, tool_names

__all__ = ["SERVER_ID", "king_plugin", "mcp_json", "tool_names"]
