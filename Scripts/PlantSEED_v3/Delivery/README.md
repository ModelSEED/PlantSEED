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
  -e PLANTSEED_ANNOT_BUNDLE_DIR=/bundle \
  -v /path/to/a/plantseed-refbuild/bundle:/bundle:ro \
  -v /path/to/genomes:/input:ro \
  -v /path/to/results:/output \
  -p 8931:8931 \
  plantseed:dev
```

Four things about that command are load-bearing:

- **`PLANTSEED_MCP_TOKEN` is not optional.** The default `CMD` binds `0.0.0.0`,
  and the server refuses a non-loopback bind with no credential — it exits 2
  rather than starting open. poplar has a public address and no host firewall,
  so this is the difference between a prototype and somebody else's free
  cluster.
- **`-v …:/output` is not optional either.** Without it, `/output` is part of
  the read-only rootfs and every write fails. It fails *legibly* — the tool
  returns the directory and how to fix it — but it fails. The directory must
  also be writable by UID 10001 (the `plantseed` user the image runs as): a
  freshly `docker run`-created host directory comes back owned by `root` and
  fails the same way for the same underlying reason — `mkdir` it and `chown`
  (or `chmod 777`) it yourself first.
- **`-v …:/bundle:ro` + `PLANTSEED_ANNOT_BUNDLE_DIR` are only needed for
  `annotate`.** `reconstruct` and the curation-lookup tools need no refdata at
  all. A bundle is `plantseed-refbuild`'s output (`manifest.json` +
  `orthofinder_families/` + `curation/`) — see
  `plantseed_annotation/refbuild/cli.py`. Omit both and `annotate` calls fail
  with a legible "bundle … failed a fast verify" error; everything else still
  works.
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

## `annotate`

Places each query protein into a curated orthogroup with DIAMOND, realigns it
into that orthogroup's alignment (`mafft --add --keeplength`), and resolves
the top ortholog with the same `psi_refined.annotate_species` scoring every
other annotation path in this repository uses — see
`plantseed_annotation/algorithms/place_query.py`'s module docstring for why
this is DIAMOND-placement rather than a full OrthoFinder `-b` insert-mode run
(the latter needs each reference species' full original proteome and
re-clusters the whole similarity graph; neither fits a bundle's size budget
or an MCP call's latency budget).

Needs a refdata bundle mounted and `PLANTSEED_ANNOT_BUNDLE_DIR` set — see
above. Slower than `reconstruct`, and the cost scales with how many query
genes DIAMOND actually places into a curated orthogroup (and how big those
orthogroups are), NOT with total proteome size — DIAMOND search itself is
trivial (~3s for 10,000 queries); `mafft --add` realignment into the
bundle's largest orthogroups (2,300-3,200 members in the Sep09 bundle) is
what costs time. Measured end-to-end against the real Sep09 bundle + the
real Poplar proteome:

| query size | genes placed | orthogroups touched | wall time |
|---|---:|---:|---:|
| 500 | 67 | 33 | 22s |
| 2,000 | 329 | 121 | 56s |
| 10,000 | 1,649 | 376 | 2:39 |
| 52,400 (full Poplar proteome) | 9,134 | 735 (of 759 total) | 6:41 |

Note the sub-linear shape: by 52,400 queries, placement has already touched
735 of the bundle's 759 total curated orthogroups, so a further-larger
query genome mostly adds MORE sequences into orthogroups already paid for,
not NEW orthogroups. A hexaploid genome like bread wheat (~105-108K
high-confidence genes, IWGSC RefSeq v1.0/v2.1 — roughly 3x a diploid
ancestor's ~35-36K genes from the A/B/D subgenome triplication) would be
expected in the **10-20 minute range**, not hours — extrapolating from the
10K→52K slope (roughly +1.5-2 min per doubling once most orthogroups are
already saturated), not from a naive linear scale-up off the 500-gene
number.

Called synchronously today — a client should set a generous timeout (300s
comfortably covers every genome tested above; the Python example client
sets this). **Concurrency**: the MCP SDK runs each sync tool call in its own
thread (`anyio.to_thread.run_sync`), so multiple simultaneous `annotate`
calls against one running container genuinely run in parallel rather than
queueing — measured: 3 concurrent 500-protein `annotate` calls finished in
~48-57s total, barely more than one call alone. The one real bug this found
and fixed: the very first call against a bundle (building its DIAMOND
database, a one-time per-bundle cost) was not safe against simultaneous
callers — two concurrent cold-cache builds corrupted each other's output
(DIAMOND segfault / "Unexpected end of input"). `build_reference_db` now
holds an `flock` around the build, so concurrent cold-start callers queue
behind whichever one builds the DB first rather than racing. A warm cache
(the common case after a bundle's first use) is unaffected either way.

The project plan's background-job bridge (submit → poll) is still the
better long-term shape for a web-UI caller that can't hold an open
connection for ten minutes, but nothing above says the capability needs to
wait for it — a synchronous call with a long timeout is a legitimate way to
drive `annotate` today, including at full-genome, wheat-scale queries.

### Smoke-testing a deployment

`test_data/poplar_test_500.faa` is 250 Poplar proteins the Sep09 bundle
annotates plus 250 random ones with no Poplar member in any curated
orthogroup; `expected_plantseed_genes.txt` lists the first 250. Against a
correctly mounted Sep09 bundle, `annotate` should report 272 placed and
annotate all 250 expected genes (251 total; see `make_poplar_test_set.py`).
Regenerate both files with that script when the bundle changes.

## Not done yet

- **No TLS.** A bearer token over plain HTTP crosses the network in the clear.
  Acceptable between two ANL hosts for a prototype; terminate TLS at a proxy
  before anyone else's token is involved.
- **No refdata bundle ships with the image.** `annotate` needs one mounted at
  runtime (see above) — nothing here builds or distributes one yet beyond the
  `plantseed-refbuild` CLI itself.
- **`annotate` is synchronous.** See the section above.
