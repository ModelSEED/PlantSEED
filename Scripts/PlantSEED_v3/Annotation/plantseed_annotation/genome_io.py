"""Serialize an annotated genome in the shape
`plantseed_model.reconstruct` consumes.

The reconstructor reads:

    {
      "id": "...",
      "features": [
        {"id": "geneA", "functions": ["role1 / role2 # cytosol"]},
        {"id": "geneB", "functions": ["role3 # plastid"]},
        ...
      ]
    }

so this module writes exactly that. Unannotated features are omitted by
default (reconstruct skips them anyway); use `include_unannotated=True` to
include them with `["Unannotated"]`.
"""

import json


def build_annotated_genome(genome_id, annotations, include_unannotated=False):
    """Turn annotate_species()'s output into a reconstructor-compatible dict.

    `annotations` — {query_gene: annotate_query_gene() result}. Only entries
    with status == 'ANNOTATED' and a non-None function contribute a
    feature; the rest are skipped (or emitted as Unannotated if opted-in).
    """
    features = []
    for gene, ann in sorted(annotations.items()):
        fn = ann.get("function")
        if ann.get("status") == "ANNOTATED" and fn:
            features.append({"id": gene, "functions": [fn]})
        elif include_unannotated:
            features.append({"id": gene, "functions": ["Unannotated"]})
    return {"id": genome_id, "features": features}


def write_annotated_genome(path, genome_id, annotations,
                            include_unannotated=False, metadata=None):
    """Write the annotated genome JSON to `path`.

    `metadata` — optional dict merged into the top level under 'metadata';
    lets callers record OF results dir, phylum, threshold, timestamp, etc.
    """
    obj = build_annotated_genome(genome_id, annotations, include_unannotated)
    if metadata:
        obj["metadata"] = metadata
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True)
    return obj
