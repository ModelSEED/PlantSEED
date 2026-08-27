"""The registration documents.

These are generated rather than hand-written, so the tests are about the
properties a consumer depends on — and about the one property that is a
security decision rather than a formatting one.
"""

import json

import pytest

from plantseed_core import registry
from plantseed_delivery import manifest

URL = "https://poplar.example.org/plantseed/mcp"


class TestMcpJson:
    def test_it_is_the_shape_the_importer_reads(self):
        """`mcp_servers._normalize_server` keys on `url` and reads `type` as
        the transport."""
        entry = manifest.mcp_json(URL)["mcpServers"][manifest.SERVER_ID]
        assert entry["url"] == URL and entry["type"] == "http"

    def test_the_token_is_a_reference_never_a_value(self):
        """This is the whole reason to prefer .mcp.json over a plugin
        manifest: the importer expands ${VAR}, so the secret stays in the
        environment and the file is safe to commit."""
        entry = manifest.mcp_json(URL)["mcpServers"][manifest.SERVER_ID]
        assert entry["headers"]["Authorization"] == "Bearer ${PLANTSEED_MCP_TOKEN}"

    def test_an_unauthenticated_route_carries_no_header(self):
        entry = manifest.mcp_json(URL, token_env="")["mcpServers"][manifest.SERVER_ID]
        assert "headers" not in entry

    def test_it_is_json_serialisable(self):
        json.dumps(manifest.mcp_json(URL))


class TestKingPlugin:
    def test_it_carries_the_fields_the_surface_reads(self):
        """`mcp_servers.available()` reads each of these directly."""
        m = manifest.king_plugin(URL)
        assert m["type"] == "mcp"
        assert m["id"] and m["title"] and m["description"]
        assert m["server"] == {"transport": "http", "url": URL}
        assert m["tools"] == ["*"]

    def test_present_is_null_because_the_server_is_remote(self):
        """`_present()` treats a null spec as always-present; a `which` or
        `glob` probe would be looking for something that is not on this host."""
        assert manifest.king_plugin(URL)["present"] is None

    def test_it_never_carries_a_credential(self):
        """A plugin manifest's headers are passed through unexpanded, so a
        token here would be a committed secret."""
        assert "headers" not in manifest.king_plugin(URL)["server"]
        assert "${" not in json.dumps(manifest.king_plugin(URL))

    def test_the_note_is_the_owners_guarantee(self):
        assert manifest.king_plugin(URL)["note"] == \
            registry.get("reconstruct").guarantee


class TestExamples:
    """MCP_SERVERS.md's rule: live-probe before shipping. An example chip that
    returns nothing teaches the wrong thing about the tool."""

    @pytest.mark.parametrize("tool,args", [
        (t, ex["args"])
        for t, exs in manifest.king_plugin(URL)["examples"].items()
        for ex in exs
    ])
    def test_every_example_returns_a_real_answer(self, tool, args):
        from plantseed_delivery import queries

        out = getattr(queries, tool)(**args)
        assert "error" not in out, f"{tool}({args}) -> {out.get('error')}"

    def test_examples_only_name_tools_that_exist(self):
        assert set(manifest.king_plugin(URL)["examples"]) <= set(manifest.tool_names())


class TestDescription:
    def test_it_names_every_declared_capability(self):
        desc = manifest.king_plugin(URL)["description"]
        for cap in registry.names():
            assert cap in desc, f"{cap} is declared but not named in the blurb"

    def test_it_states_the_offline_property(self):
        """An MCP server that makes external calls expands the session's trust
        surface; saying that this one does not is the point."""
        assert "no external calls" in manifest.king_plugin(URL)["description"]


class TestCli:
    def test_mcp_json_is_the_default(self, capsys):
        assert manifest.main(["--url", URL]) == 0
        assert "mcpServers" in json.loads(capsys.readouterr().out)

    def test_king_is_opt_in(self, capsys):
        assert manifest.main(["--url", URL, "--king"]) == 0
        assert json.loads(capsys.readouterr().out)["type"] == "mcp"
