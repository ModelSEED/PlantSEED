# One image, two lanes: the MCP service on poplar today, a CTS batch job later.
#
# Built to the CDM Task Service's image-approval checklist
# (kbase/cdm-task-service docs/admin_image_setup.md), because approval there is
# a manual per-version human review and the cheapest time to satisfy it is
# before the image exists. Each rule is marked [CTS n] beside the line meeting
# it:
#
#   1 public              — the base is a Docker Hub official image
#   2 no root             — USER plantseed
#   3 /bin/bash present   — Debian base, asserted at build time
#   4 entrypoint          — ENTRYPOINT below
#   5 one output folder   — /output, named by PLANTSEED_OUTPUT_DIR
#   6 write nowhere else  — enforced at runtime, not merely intended
#   7 no input/output hardlinks — nothing in the package calls os.link
#   8 not Windows         — linux base
#   9 reproducible        — no runtime network; see the caveat at the end
#  10 malware review      — the reviewer's step, not ours
#
# Rule 6 is the one that is usually only a promise. Here PLANTSEED_OUTPUT_DIR
# puts plantseed_core.runtime into strict mode, so every gated write is checked
# against /output and the scratch dir and raises otherwise: a violation is a
# loud failure inside the container rather than a silent success outside it.

# [CTS 1] [CTS 8]
FROM python:3.12-slim-bookworm

# [CTS 3] Slim Debian ships bash, but "ships bash today" is not "will ship
# bash". CTS rejects an image without it, so fail the build, not the review.
RUN test -x /bin/bash

# --- the data the package does not carry ------------------------------------
# plantseed_curation and plantseed_annotation resolve their data files relative
# to the source tree, so a wheel install alone has no roles, complexes,
# compartments or template. Copy them somewhere known and name that place in
# the environment; every one of these paths is env-overridable, which is why
# this needs no code change.
#
# This is also the seam the refdata bundle slots into later: point the same
# variables at /kb/data/plantseed_annotation/vN/ and nothing else moves.
ARG DATA_DIR=/opt/plantseed/data
COPY Data/PlantSEED_v3 ${DATA_DIR}/PlantSEED_v3
COPY Scripts/PlantSEED_v3/Template ${DATA_DIR}/Template
COPY Scripts/PlantSEED_v3/Curation/PlantSEED_Schema.yaml ${DATA_DIR}/

ENV PLANTSEED_ROLES_FILE=${DATA_DIR}/PlantSEED_v3/PlantSEED_Roles.json \
    PLANTSEED_COMPLEXES_FILE=${DATA_DIR}/PlantSEED_v3/PlantSEED_Complexes.json \
    PLANTSEED_SCHEMA_FILE=${DATA_DIR}/PlantSEED_Schema.yaml \
    PLANTSEED_ANNOT_ROLES_FILE=${DATA_DIR}/PlantSEED_v3/PlantSEED_Roles.json \
    PLANTSEED_ANNOT_COMPLEXES_FILE=${DATA_DIR}/PlantSEED_v3/PlantSEED_Complexes.json \
    PLANTSEED_ANNOT_COMPARTMENTS_FILE=${DATA_DIR}/PlantSEED_v3/Compartments/PlantSEED_Compartments.json \
    PLANTSEED_ANNOT_TEMPLATE_FILE=${DATA_DIR}/Template/PlantSEED_Biomass_Template.json

# --- the package -------------------------------------------------------------
# [curate] is not optional here: the curation lookups read PlantSEED_Schema.yaml
# through plantseed_curation, which needs PyYAML. [model] is deliberately out —
# reconstruction is pure stdlib, which the core-is-standalone CI job proves, and
# cobrapy would add tens of megabytes for nothing either lane runs.
WORKDIR /src
COPY pyproject.toml README.md ./
COPY Scripts/PlantSEED_v3 ./Scripts/PlantSEED_v3
RUN pip install --no-cache-dir --no-compile ".[curate,mcp]" \
 && rm -rf /src /root/.cache

# --- where it may write -------------------------------------------------------
# [CTS 2] [CTS 5]
RUN useradd --create-home --uid 10001 plantseed \
 && mkdir -p /output /tmp/plantseed \
 && chown plantseed:plantseed /output /tmp/plantseed

# [CTS 6] The first two variables ARE the enforcement — setting
# PLANTSEED_OUTPUT_DIR is what turns runtime.strict_mode() on.
#
# PYTHONDONTWRITEBYTECODE matters for the same rule: without it the interpreter
# writes __pycache__ beside the installed package on first import, a write
# outside /output and /tmp introduced by nothing more than starting the
# program. Paired with --no-compile above, so no stale .pyc ships either.
ENV PLANTSEED_OUTPUT_DIR=/output \
    PLANTSEED_SCRATCH_DIR=/tmp/plantseed \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# [CTS 2]
USER plantseed
# [CTS 5]
WORKDIR /output

# [CTS 4]
COPY --chmod=0555 Scripts/PlantSEED_v3/Delivery/entrypoint.sh /usr/local/bin/plantseed-entrypoint
ENTRYPOINT ["/usr/local/bin/plantseed-entrypoint"]

# The MCP service is the default lane; CTS overrides argv with a subcommand.
# 0.0.0.0 is the container's own namespace — what is actually reachable is
# decided by the port publish, not here.
#
# This CMD therefore requires PLANTSEED_MCP_TOKEN: binding anything but
# loopback without a credential is refused (plantseed_delivery.auth), so the
# container exits 2 rather than starting open. Run it with
# `-e PLANTSEED_MCP_TOKEN=$(openssl rand -hex 32)`.
#
# Known conservative case: publishing with `-p 127.0.0.1:8931:8931` is safe,
# but the server sees 0.0.0.0 inside the namespace and cannot know that, so it
# still asks for a token. Set one anyway — cheaper than an escape hatch that
# ends up being the default.
CMD ["mcp", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8931"]
EXPOSE 8931

# Needs no MCP client and opens no socket: it builds the server and lists its
# tools, which fails if a capability, its data, or an import is missing.
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD ["/usr/local/bin/plantseed-entrypoint", "mcp", "--list-tools"]

# [CTS 9], honestly. Nothing either lane runs downloads anything: the one
# runtime fetch in the wheel is plantseed_curation.expasy.fetch_enzyme_dat,
# which pulls enzyme.dat from ftp.expasy.org, and no reachable code path calls
# it — plantseed_delivery.queries says so explicitly and a test pins it.
#
# What is NOT yet true is a byte-reproducible BUILD: pip resolves dependencies
# at build time with no lock file, so two builds a month apart can differ. Pin
# with a hash-pinned requirements file before submitting this for approval.
