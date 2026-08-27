"""The declaration and the tool signature must describe the same parameters.

`Capability.input_schema()` is the authority — it is what the manifest, the
KBase spec and the CTS submit body are built from. But the MCP SDK derives a
tool's schema from the Python function signature and gives no hook for
supplying one, so the tool body restates the parameters a second time.

Two statements of the same thing is exactly the drift this package exists to
prevent everywhere else, so it gets a test instead of a convention: add a
parameter to the capability and forget the tool (or the reverse) and this
fails, naming the parameter.

The two schemas are not textually equal and should not be. Pydantic writes an
optional as `anyOf: [T, null]` and adds titles; the registry writes a bare type
and `additionalProperties: false`. What must agree is the contract: the same
parameter names, the same required set, the same underlying types.
"""

import asyncio

import pytest

from plantseed_core import registry
from plantseed_delivery import invoke

mcp_server = pytest.importorskip(
    "plantseed_delivery.mcp_server",
    reason="the MCP server needs the [mcp] extra")


def _scalar(sub: dict):
    """The underlying type of one property, ignoring how optionality is spelt."""
    if "enum" in sub:
        return "enum"
    if "anyOf" in sub:
        types = sorted({x.get("type") for x in sub["anyOf"]} - {"null", None})
        return types[0] if len(types) == 1 else tuple(types)
    return sub.get("type")


def _contract(schema: dict) -> dict:
    return {
        "types": {n: _scalar(s) for n, s in (schema.get("properties") or {}).items()},
        "required": set(schema.get("required") or ()),
    }


@pytest.fixture(scope="module")
def tools():
    server = mcp_server.build_server()
    return {t.name: t for t in asyncio.run(server.list_tools())}


CAPABILITY_TOOLS = sorted(n for n in registry.names() if n in invoke.INVOKERS)


def test_there_is_something_to_compare():
    """A rename that emptied this list would make every test below vacuous."""
    assert CAPABILITY_TOOLS


@pytest.mark.parametrize("name", CAPABILITY_TOOLS)
def test_every_declared_capability_is_a_tool(name, tools):
    assert name in tools


@pytest.mark.parametrize("name", CAPABILITY_TOOLS)
def test_parameters_match_the_declaration(name, tools):
    declared = _contract(registry.get(name).input_schema())
    exposed = _contract(tools[name].input_schema)

    missing = set(declared["types"]) - set(exposed["types"])
    extra = set(exposed["types"]) - set(declared["types"])
    assert not missing, (
        f"{name}: declared but not exposed as tool parameters: {sorted(missing)}. "
        "Add them to the tool signature in mcp_server.py.")
    assert not extra, (
        f"{name}: the tool takes parameters the capability does not declare: "
        f"{sorted(extra)}. Add them to the capability, or drop them.")

    mismatched = {k: (declared["types"][k], exposed["types"][k])
                  for k in declared["types"]
                  if declared["types"][k] != exposed["types"][k]}
    assert not mismatched, f"{name}: declared vs exposed type: {mismatched}"


@pytest.mark.parametrize("name", CAPABILITY_TOOLS)
def test_required_parameters_match(name, tools):
    declared = _contract(registry.get(name).input_schema())["required"]
    exposed = _contract(tools[name].input_schema)["required"]
    assert declared == exposed, (
        f"{name}: required declared {sorted(declared)}, "
        f"tool requires {sorted(exposed)}")


@pytest.mark.parametrize("name", CAPABILITY_TOOLS)
def test_the_tool_description_is_the_owners_summary(name, tools):
    """KIND*AI renders the owner's text and authors none of its own; the tool
    description must therefore come from the declaration, not be retyped."""
    assert tools[name].description.startswith(registry.get(name).summary[:40])


def test_the_manifest_lists_exactly_the_registered_tools(tools):
    from plantseed_delivery import manifest

    assert sorted(tools) == manifest.tool_names()
