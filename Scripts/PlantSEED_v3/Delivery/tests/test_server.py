"""The server, driven the way a client drives it.

`call_tool` rather than the Python function, so the SDK's own argument
coercion and result wrapping are in the path — that is what KIND*AI will
exercise, and it is where a signature mistake actually shows up.
"""

import asyncio
import json
import os

import pytest

from conftest import GENOME, HAVE_GENOME

mcp_server = pytest.importorskip(
    "plantseed_delivery.mcp_server",
    reason="the MCP server needs the [mcp] extra")


@pytest.fixture(scope="module")
def server():
    return mcp_server.build_server()


def _call(server, name, args):
    """Call a tool and return its parsed JSON payload."""
    result = asyncio.run(server.call_tool(name, args))
    text = "".join(c.text for c in result.content if getattr(c, "text", None))
    return json.loads(text)


class TestToolSurface:
    def test_every_advertised_tool_is_registered(self, server):
        from plantseed_delivery import manifest

        names = sorted(t.name for t in asyncio.run(server.list_tools()))
        assert names == manifest.tool_names()

    def test_every_tool_has_a_description(self, server):
        """An undescribed tool is one the model will not reach for."""
        for t in asyncio.run(server.list_tools()):
            assert t.description and t.description.strip(), t.name


class TestQueriesOverTheWire:
    def test_list_subsystems(self, server):
        assert _call(server, "list_subsystems", {})["n_roles"] > 900

    def test_get_role_by_stable_id(self, server):
        assert _call(server, "get_role", {"role": "PS_role_1cc588"})["reactions"]

    def test_an_error_comes_back_as_a_result_not_a_crash(self, server):
        """A failed tool call should tell the model what went wrong, not hand
        it a traceback from a server it cannot see."""
        out = _call(server, "get_role", {"role": "no such role"})
        assert "error" in out


@pytest.mark.skipif(not HAVE_GENOME,
                    reason="preprint genome not present (installed wheel)")
class TestReconstruct:
    def test_it_reproduces_the_golden_model(self, server):
        """Same numbers as Model/tests/test_golden_reconstruction.py — going
        through MCP must not change the science."""
        out = _call(server, "reconstruct", {"genome": GENOME})
        assert out["n_reactions"] == 1218
        assert out["n_compounds"] == 1313
        assert out["n_biomasses"] == 1

    def test_the_model_is_on_disk_not_in_the_result(self, server):
        """1218 reactions inlined would spend the session's context on one
        call. The result carries a path and a hash instead."""
        out = _call(server, "reconstruct", {"genome": GENOME})
        assert "modelreactions" not in out
        assert os.path.isfile(out["model_path"])
        assert len(out["sha256"]) == 64

    def test_output_lands_in_the_output_root_not_beside_the_input(self, server):
        """Under the output root so a mounted /output exposes the model, and
        inside the writable roots so strict mode permits the write at all."""
        from plantseed_core import runtime

        out = _call(server, "reconstruct", {"genome": GENOME})
        assert runtime.is_writable_path(out["model_path"])
        assert out["model_path"].startswith(str(runtime.output_root()))
        assert os.path.dirname(GENOME) not in out["model_path"]

    def test_concurrent_calls_do_not_share_an_output_path(self, server):
        """The reason output goes to a per-call directory rather than through
        runtime.output_root(), which is process-global."""
        a = _call(server, "reconstruct", {"genome": GENOME, "model_id": "a"})
        b = _call(server, "reconstruct", {"genome": GENOME, "model_id": "b"})
        assert a["model_path"] != b["model_path"]
        assert a["model_id"] == "a" and b["model_id"] == "b"

    def test_a_missing_genome_is_an_error(self, server):
        assert "error" in _call(server, "reconstruct", {"genome": "/nope.json"})


class TestCli:
    def test_list_tools_exits_clean(self, capsys):
        """A readiness check that needs no MCP client — what a container
        healthcheck can run."""
        assert mcp_server.main(["--list-tools"]) == 0
        assert "reconstruct" in capsys.readouterr().out


class TestTransportWiring:
    """Where the bind address goes moved between mcp 1.x and 2.x, and getting
    it wrong fails only when a socket is actually opened — after the image has
    built and the container has started. These bind the call against the
    installed SDK's real signature instead."""

    def test_the_chosen_call_matches_the_installed_sdk(self, server):
        import inspect

        fields = getattr(type(server.settings), "model_fields", {})
        if "host" in fields:                       # mcp 1.x
            inspect.signature(server.run).bind(transport="streamable-http")
        else:                                      # mcp >= 2
            inspect.signature(server.run_streamable_http_async).bind(
                host="127.0.0.1", port=8931)

    def test_settings_are_not_assigned_when_the_sdk_has_no_such_field(self, server):
        """The actual bug: pydantic raises on an unknown field, so assigning
        `settings.host` blindly takes the server down at startup."""
        fields = getattr(type(server.settings), "model_fields", {})
        if "host" not in fields:
            with pytest.raises(ValueError):
                server.settings.host = "127.0.0.1"


@pytest.mark.skipif(not HAVE_GENOME, reason="preprint genome not present")
def test_artifacts_are_readable_from_outside_the_container(server):
    """mkdtemp defaults to 0700. CTS collects outputs with `find <mount>` and a
    bind-mounted /output is read by a different uid; either way a 0700 subtree
    means the artifact is there and unreachable."""
    import stat

    out = _call(server, "reconstruct", {"genome": GENOME})
    mode = os.stat(os.path.dirname(out["model_path"])).st_mode
    assert mode & stat.S_IROTH and mode & stat.S_IXOTH, oct(mode)
