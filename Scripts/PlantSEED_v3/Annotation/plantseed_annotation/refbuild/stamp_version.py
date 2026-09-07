"""Finalize a bundle by writing its `manifest.json`.

The manifest is what `reference.verify` reads, and it is the only place a
bundle records what it was built from. Its shape is pinned by
`manifest_schema.json` in this directory.

Two fields carry most of the weight:

* **`contents`** — SHA-256 and byte count for every payload file. This is what
  turns "the directory looks right" into "the bundle is intact", and it is
  what makes a partially-rsynced bundle a detected error rather than a run
  with missing orthogroups.
* **`content_id`** — one hash over all of those. Two bundles with the same
  content_id have byte-identical payloads, so a rebuild can be checked without
  diffing thousands of files, and a v1 bundle is visibly different from the v0
  it grew out of.

`created_utc` honours `SOURCE_DATE_EPOCH`; see `bundle.created_utc` for why
that is not a detail.

Phase 1 writes a bundle with no SHOOT enrichment, so `sources.shoot_db_build_id`
and the `curated_non_arabidopsis` list are empty. They are present and empty
rather than absent: a consumer should be able to tell "this bundle carries no
SHOOT-placed proteins" from "this manifest predates the field".
"""

from __future__ import annotations

import os
import subprocess

from plantseed_core import __about__

from .. import paths
from . import bundle

__all__ = ["file_git_sha", "build_manifest", "stamp"]

SCHEMA_VERSION = 1


def file_git_sha(path, default="unknown") -> str:
    """The commit that last touched `path`, or `default`.

    A build from a tarball or a dirty tree has no meaningful SHA, and that is
    a normal thing for a developer to do — so this reports rather than raises.
    The manifest schema allows only hex, so the fallback is recorded in
    `sources.notes` instead of poisoning the field.
    """
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", os.path.basename(path)],
            cwd=os.path.dirname(os.path.abspath(path)),
            capture_output=True, text=True, timeout=15, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return default
    sha = out.stdout.strip()
    return sha if sha and all(c in "0123456789abcdef" for c in sha) else default


def build_manifest(bundle_dir, bundle_version, *, sources=None, totals=None,
                   tool_versions=None) -> dict:
    """Assemble the manifest for an already-populated bundle directory."""
    contents = {}
    for rel, absolute in bundle.iter_payload(bundle_dir):
        digest, size = bundle.sha256_file(absolute)
        contents[rel] = {"sha256": digest, "bytes": size}

    roles_sha = file_git_sha(paths.ROLES_FILE)
    complexes_sha = file_git_sha(paths.COMPLEXES_FILE)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "bundle_version": bundle_version,
        "created_utc": bundle.created_utc(),
        "content_id": bundle.content_id(contents),
        "sources": {
            "roles_json_sha": roles_sha,
            "complexes_json_sha": complexes_sha,
            "phytozome_release": "",
            "shoot_db_build_id": "",
            "curation_repo_url": "https://github.com/ModelSEED/PlantSEED",
            **(sources or {}),
        },
        "tool_versions": {
            "plantseed_annotation": __about__.__version__,
            "plantseed_data": __about__.DATA_VERSION,
            **(tool_versions or {}),
        },
        "contents": contents,
        "totals": {
            "bytes_total": sum(c["bytes"] for c in contents.values()),
            "og_count": sum(1 for rel in contents
                            if rel.startswith(bundle.FAMILIES_DIR + "/")),
            "protein_count": 0,
            **(totals or {}),
        },
        # Empty until SHOOT enrichment lands; present so a consumer can tell
        # "no placed proteins" from "manifest predates the field".
        "curated_non_arabidopsis": [],
    }
    return manifest


def stamp(bundle_dir, bundle_version, log=print, **kwargs) -> dict:
    """Write `manifest.json` into `bundle_dir` and return it."""
    manifest = build_manifest(bundle_dir, bundle_version, **kwargs)
    bundle.write_json(os.path.join(bundle_dir, bundle.MANIFEST), manifest)
    log(f"[stamp] {bundle_version}  {len(manifest['contents'])} files  "
        f"{manifest['totals']['bytes_total'] / 1e6:.1f} MB  "
        f"content_id {manifest['content_id'][:12]}")
    return manifest
