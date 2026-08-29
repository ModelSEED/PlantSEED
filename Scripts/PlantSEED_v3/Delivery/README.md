# Delivery — PlantSEED as an MCP service

One image, two lanes. `plantseed-mcp` serves the tools over MCP; the same image
runs `plantseed-reconstruct` as a batch job. Both are built to the CDM Task
Service's image checklist — see the `[CTS n]` markers in the `Dockerfile`.

## Build

```bash
cd <repo root>                       # the build context is the repo, not this dir
docker build -f Scripts/PlantSEED_v3/Delivery/Dockerfile -t plantseed:dev .
```

## Run the service

```bash
TOKEN=$(openssl rand -hex 32)
docker run -d --name plantseed-mcp \
  --read-only --tmpfs /tmp:rw,size=256m,mode=1777 \
  -e PLANTSEED_MCP_TOKEN="$TOKEN" \
  -v /path/to/genomes:/input:ro \
  -v /path/to/results:/output \
  -p 8931:8931 \
  plantseed:dev
```

Three things about that command are load-bearing:

- **`PLANTSEED_MCP_TOKEN` is not optional.** The default `CMD` binds `0.0.0.0`,
  and the server refuses a non-loopback bind with no credential — it exits 2
  rather than starting open. poplar has a public address and no host firewall,
  so this is the difference between a prototype and somebody else's free
  cluster.
- **`-v …:/output` is not optional either.** Without it, `/output` is part of
  the read-only rootfs and every reconstruction fails. It fails *legibly* —
  the tool returns the directory and how to fix it — but it fails.
- **`--read-only` is a choice you can make** because the image is built for it.
  Nothing writes outside `/output` and the tmpfs, and `PLANTSEED_OUTPUT_DIR`
  makes that enforced rather than hoped for.

Health, without an MCP client: `docker exec plantseed-mcp plantseed-entrypoint
mcp --list-tools`, which is also the container's `HEALTHCHECK`.

## Register it with KIND*AI

```bash
python -m plantseed_delivery.manifest --url https://<host>/mcp > .mcp.json
```

Use `.mcp.json` — not a KIND plugin manifest — whenever a token is involved.
KIND expands `${PLANTSEED_MCP_TOKEN}` in an imported `.mcp.json`, and passes a
plugin manifest's headers through verbatim, so the second form would commit the
secret. Authorization is the same ORCID-attributed act either way.

Then set `PLANTSEED_MCP_TOKEN` in KIND's environment and authorize the server
in nav → Apps → 🔌 MCP capabilities.

## Not done yet

- **No TLS.** A bearer token over plain HTTP crosses the network in the clear.
  Acceptable between two ANL hosts for a prototype; terminate TLS at a proxy
  before anyone else's token is involved.
- **The build is not byte-reproducible.** pip resolves at build time with no
  lock file. Pin with hashes before submitting the image for CTS approval.
- **`annotate` is not exposed.** It needs the refdata bundle, and an
  OrthoFinder run is minutes rather than seconds, so it wants KIND's
  background-job bridge rather than a blocking tool call.
