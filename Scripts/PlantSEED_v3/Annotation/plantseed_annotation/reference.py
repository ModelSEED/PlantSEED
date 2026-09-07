"""Locate + verify the versioned refdata bundle at annotation time.

    <BUNDLE_DIR>/
      manifest.json
      orthofinder_families/     alignments for the pruned orthogroups
      psi_matrices/             per-OG pairwise sequence identity
      curation/                 curated features + phylum thresholds
      shoot_db/                 (Phase 1b, once SHOOT enrichment lands)

`verify` exists because of how a bundle actually fails. It is rsynced to KBase
refdata and mounted read-only in two containers, so the realistic faults are a
partial copy and a stale copy — neither of which raises anything on its own.
An annotator reading a half-copied bundle does not crash; it silently finds no
orthologs for the orthogroups that did not arrive and reports fewer
annotations, which looks like biology rather than like a broken mount.

So verification is by content hash, not by "the directory exists".
"""

from __future__ import annotations

import os

from . import config, paths
from .refbuild import bundle

__all__ = ["bundle_dir", "load_manifest", "verify", "content_id"]


def bundle_dir(path=None) -> str:
    """The bundle to use: explicit argument, else `paths.BUNDLE_DIR`."""
    return path or paths.BUNDLE_DIR


def load_manifest(path=None) -> dict:
    """Read `manifest.json`. Raises FileNotFoundError naming the directory."""
    root = bundle_dir(path)
    manifest_path = os.path.join(root, bundle.MANIFEST)
    if not os.path.isfile(manifest_path):
        raise FileNotFoundError(
            f"no {bundle.MANIFEST} in {root} — either the bundle has not been "
            f"built (see plantseed-refbuild) or PLANTSEED_ANNOT_BUNDLE_DIR "
            f"points somewhere else")
    return bundle.read_json(manifest_path)


def content_id(path=None) -> str:
    """The bundle's content_id as recorded in its manifest."""
    return load_manifest(path).get("content_id", "")


def verify(path=None, tier=None, check_hashes=True):
    """Return `(ok, issues)` for the bundle at `path`.

    `check_hashes=False` skips re-reading every payload byte — appropriate for
    a startup probe on a large bundle, and not appropriate for deciding that a
    bundle is intact.

    `tier` compares total size against that tier's `refdata_gb_max`. The KBase
    cap is the binding constraint on the whole design, so exceeding it is an
    issue rather than a warning.
    """
    root = bundle_dir(path)
    issues = []

    if not os.path.isdir(root):
        return False, [f"bundle directory does not exist: {root}"]
    try:
        manifest = load_manifest(root)
    except (FileNotFoundError, ValueError) as exc:
        return False, [str(exc)]

    if manifest.get("schema_version") != 1:
        issues.append(f"unsupported manifest schema_version "
                      f"{manifest.get('schema_version')!r}; this package reads 1")

    contents = manifest.get("contents") or {}
    if not contents:
        issues.append("manifest lists no files — the bundle is empty or the "
                      "build did not finish")

    on_disk = {rel for rel, _ in bundle.iter_payload(root)}
    for rel in sorted(set(contents) - on_disk):
        issues.append(f"missing: {rel}")
    for rel in sorted(on_disk - set(contents)):
        issues.append(f"unexpected file not in manifest: {rel}")

    if check_hashes:
        for rel in sorted(set(contents) & on_disk):
            digest, size = bundle.sha256_file(os.path.join(root, rel))
            if digest != contents[rel]["sha256"]:
                issues.append(f"content differs from manifest: {rel}")
            elif size != contents[rel]["bytes"]:
                issues.append(f"size differs from manifest: {rel}")
        recomputed = bundle.content_id(contents)
        if manifest.get("content_id") and manifest["content_id"] != recomputed:
            issues.append("content_id does not match the contents it summarises "
                          "— the manifest was edited by hand or truncated")

    if tier:
        cap_gb = config.get(tier).refdata_gb_max
        total_gb = (manifest.get("totals", {}).get("bytes_total", 0)) / 1e9
        if cap_gb and total_gb > cap_gb:
            issues.append(f"bundle is {total_gb:.1f} GB, over the {tier} tier's "
                          f"{cap_gb} GB refdata cap")

    return (not issues), issues
