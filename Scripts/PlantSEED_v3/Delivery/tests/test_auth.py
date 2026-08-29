"""The credential, and the guard that makes forgetting it impossible.

poplar has a public address and no host firewall, so "we'll remember to set the
token" is not a control. The tests that matter here are the ones about the
startup guard: a bind that could be reached from another machine must not
start without a credential, whatever the operator typed.
"""

import asyncio

import pytest

from plantseed_delivery import auth


@pytest.fixture(autouse=True)
def no_ambient_token(monkeypatch):
    monkeypatch.delenv(auth.TOKEN_ENV, raising=False)


class TestToken:
    def test_unset_is_none(self):
        assert auth.token() is None

    def test_whitespace_only_is_unset(self, monkeypatch):
        """`export PLANTSEED_MCP_TOKEN=` is a mistake, not a credential."""
        monkeypatch.setenv(auth.TOKEN_ENV, "   ")
        assert auth.token() is None

    def test_it_is_stripped(self, monkeypatch):
        monkeypatch.setenv(auth.TOKEN_ENV, " s3cret\n")
        assert auth.token() == "s3cret"


class TestBindGuard:
    @pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
    def test_loopback_needs_no_token(self, host):
        auth.check_bind(host)

    @pytest.mark.parametrize("host", ["0.0.0.0", "140.221.44.2", "::"])
    def test_a_reachable_bind_without_a_token_is_refused(self, host):
        """0.0.0.0 is every interface, which is the opposite of loopback —
        the one most likely to be typed by someone who means 'let me test it'."""
        with pytest.raises(RuntimeError) as exc:
            auth.check_bind(host)
        assert auth.TOKEN_ENV in str(exc.value)

    @pytest.mark.parametrize("host", ["0.0.0.0", "140.221.44.2"])
    def test_a_reachable_bind_with_a_token_is_allowed(self, host, monkeypatch):
        monkeypatch.setenv(auth.TOKEN_ENV, "s3cret")
        auth.check_bind(host)

    def test_the_message_says_both_ways_out(self):
        with pytest.raises(RuntimeError) as exc:
            auth.check_bind("0.0.0.0")
        msg = str(exc.value)
        assert "Bearer" in msg and "127.0.0.1" in msg


class _Recorder:
    """Collects what an ASGI app sends, and whether the inner app ran."""

    def __init__(self):
        self.reached = False
        self.messages = []

    async def app(self, scope, receive, send):
        self.reached = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"inner"})

    async def send(self, message):
        self.messages.append(message)

    @property
    def status(self):
        return next(m["status"] for m in self.messages
                    if m["type"] == "http.response.start")

    @property
    def headers(self):
        start = next(m for m in self.messages if m["type"] == "http.response.start")
        return {k.lower(): v for k, v in start["headers"]}


def _call(secret, header=None, scope_type="http"):
    rec = _Recorder()
    headers = [(b"authorization", header)] if header is not None else []
    scope = {"type": scope_type, "headers": headers}
    asyncio.run(auth.BearerAuth(rec.app, secret)(scope, None, rec.send))
    return rec


class TestBearerAuth:
    def test_the_right_token_passes_through(self):
        assert _call("s3cret", b"Bearer s3cret").reached

    def test_a_wrong_token_is_401_and_never_reaches_the_app(self):
        rec = _call("s3cret", b"Bearer wrong")
        assert rec.status == 401 and not rec.reached

    def test_a_missing_header_is_401(self):
        rec = _call("s3cret")
        assert rec.status == 401 and not rec.reached

    def test_the_wrong_scheme_is_401(self):
        """Basic auth with the token as the password is not what we asked for."""
        rec = _call("s3cret", b"Basic czNjcmV0")
        assert rec.status == 401 and not rec.reached

    def test_surrounding_whitespace_is_tolerated(self):
        assert _call("s3cret", b"  Bearer   s3cret  ").reached

    def test_the_401_says_how_to_authenticate(self):
        """RFC 9110 requires it, and without it a client cannot tell a
        credential problem from a broken endpoint."""
        assert b"Bearer" in _call("s3cret").headers[b"www-authenticate"]

    def test_no_configured_token_means_no_gate(self):
        """Only reachable on loopback — check_bind refuses everything else."""
        assert _call(None).reached

    def test_non_http_scopes_pass_straight_through(self):
        """Lifespan startup must not be answered with a 401."""
        rec = _Recorder()
        asyncio.run(auth.BearerAuth(rec.app, "s3cret")(
            {"type": "lifespan"}, None, rec.send))
        assert rec.reached

    def test_a_malformed_header_does_not_raise(self):
        """Bytes that are not valid UTF-8 are a hostile client's problem, not
        a traceback in the server log."""
        rec = _call("s3cret", b"Bearer \xff\xfe")
        assert rec.status == 401


class TestServerWiring:
    """The guard has to be on the path the CLI actually takes."""

    def test_serve_refuses_a_public_bind_before_opening_a_socket(self):
        mcp_server = pytest.importorskip("plantseed_delivery.mcp_server")
        with pytest.raises(RuntimeError):
            mcp_server.serve(object(), "streamable-http", "0.0.0.0", 8931)

    def test_the_cli_exits_nonzero_rather_than_serving(self, capsys):
        mcp_server = pytest.importorskip("plantseed_delivery.mcp_server")
        rc = mcp_server.main(["--transport", "streamable-http",
                              "--host", "0.0.0.0", "--port", "8931"])
        assert rc == 2
        assert "refusing to bind" in capsys.readouterr().err
