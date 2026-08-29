"""Who may call the server.

poplar has a routable public address and no host firewall, so a bound port is
reachable by anything the site perimeter permits. `reconstruct` is compute, and
compute on an open port is somebody else's free cluster. Hence a credential.

The design point is the *startup guard*, not the check. A token that can be
forgotten will be, and the failure is silent — the service works perfectly for
the person testing it and is open to everyone else. So binding a non-loopback
address without `PLANTSEED_MCP_TOKEN` set is refused outright: the unsafe
configuration cannot be reached, rather than being documented as a bad idea.
Same posture as `plantseed_core.runtime.enforce_writable`, and for the same
reason — the mistake is invisible in the environment where it is made.

What this is not: TLS. A bearer token over plain HTTP crosses the network in
the clear, which is tolerable between two ANL hosts for a prototype and is not
a durable answer. Terminate TLS at a proxy before anyone else's token is
involved.
"""

from __future__ import annotations

import hmac
import os

__all__ = ["TOKEN_ENV", "token", "is_loopback", "check_bind", "BearerAuth"]

TOKEN_ENV = "PLANTSEED_MCP_TOKEN"

#: Addresses that reach no further than the machine itself. `0.0.0.0` is not
#: here on purpose — it means "every interface", which is the opposite.
_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost", ""})


def token() -> str | None:
    """The configured token, or None. Whitespace-only counts as unset."""
    value = (os.environ.get(TOKEN_ENV) or "").strip()
    return value or None


def is_loopback(host: str) -> bool:
    return (host or "").strip().lower() in _LOOPBACK


def check_bind(host: str) -> None:
    """Raise unless this bind is safe to make.

    Called before the socket is opened, so a misconfigured service fails to
    start rather than starting wide open.
    """
    if is_loopback(host) or token():
        return
    raise RuntimeError(
        f"refusing to bind {host}:* without a credential.\n"
        f"  {host} is reachable from other machines, and this server exposes "
        f"reconstruction as well as reads.\n"
        f"  Set {TOKEN_ENV} to a secret the client will send as "
        f"`Authorization: Bearer <token>`,\n"
        f"  or bind 127.0.0.1 and reach it through a proxy that authenticates."
    )


class BearerAuth:
    """ASGI middleware requiring `Authorization: Bearer <token>`.

    Plain ASGI rather than a Starlette `BaseHTTPMiddleware` subclass: the MCP
    transports stream, and wrapping a streaming response in the request/
    response abstraction is a known way to break server-sent events. This never
    touches the body.

    A no-op when no token is configured — which is only reachable on a loopback
    bind, because `check_bind` refuses everything else.
    """

    def __init__(self, app, secret: str | None):
        self.app = app
        self.secret = secret
        # Kept as bytes: headers arrive as bytes, and hmac.compare_digest
        # rejects str containing anything outside ASCII. Comparing in bytes
        # means a hostile client cannot turn a bad header into a 500.
        self._secret = secret.encode() if secret is not None else None

    async def __call__(self, scope, receive, send):
        if self.secret is None or scope.get("type") != "http":
            return await self.app(scope, receive, send)
        if self._authorised(scope):
            return await self.app(scope, receive, send)
        await self._unauthorised(send)

    def _authorised(self, scope) -> bool:
        for name, value in scope.get("headers") or ():
            if name.lower() != b"authorization":
                continue
            scheme, _, given = bytes(value).strip().partition(b" ")
            if scheme.lower() != b"bearer":
                return False
            # Constant-time: a plain == leaks the token one byte at a time to
            # anyone who can measure the response.
            return hmac.compare_digest(given.strip(), self._secret)
        return False

    @staticmethod
    async def _unauthorised(send) -> None:
        body = b'{"error":"unauthorized"}'
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                # RFC 9110: a 401 states how to authenticate.
                (b"www-authenticate", b'Bearer realm="plantseed"'),
            ],
        })
        await send({"type": "http.response.body", "body": body})
