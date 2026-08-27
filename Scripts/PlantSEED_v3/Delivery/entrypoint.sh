#!/bin/bash
# One entrypoint, several lanes.
#
# CTS constrains the arguments it will pass: each must match
# ^[\w\./][\w\.,+/-]*$ and may not lead with a dash, so a lane is selected by a
# bare word rather than a flag. The same words work for `docker run` locally,
# which keeps the poplar service and the batch job on one image.
#
# Anything unrecognised is exec'd as given. That is deliberate: an admin
# reviewing this image needs `docker run … bash` to look around, and a
# healthcheck needs to call a command directly.
set -euo pipefail

case "${1:-mcp}" in
    mcp)
        shift || true
        exec plantseed-mcp "$@"
        ;;
    reconstruct)
        shift
        exec plantseed-reconstruct "$@"
        ;;
    annotate)
        shift
        exec plantseed-annotate "$@"
        ;;
    capabilities)
        shift
        exec plantseed capabilities "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
