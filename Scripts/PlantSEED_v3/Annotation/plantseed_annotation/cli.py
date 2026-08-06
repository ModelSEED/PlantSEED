"""`plantseed-annotate` command-line entry point.

Usage (as of scaffold):
    plantseed-annotate --genome <path.faa|genome.json> \
                       --tier {kbase,poplar,local} \
                       [--bundle-version vN] \
                       [--phylum {eudicot,monocot,basal,auto}] \
                       [--out <path>]

The KBase App wrapper and the poplar celery task both shell out to this
same CLI (via python -m plantseed_annotation.cli) so there's one entry
point, one place to instrument logging + telemetry, and one behavior to
audit.
"""


def main():
    """Argparse + dispatch. Filled in at Phase 3 when the poplar CLI ships."""
    raise NotImplementedError("Phase 3: wire argparse + dispatch")


if __name__ == "__main__":
    main()
