"""Bundle layout, and the primitives that make a build byte-reproducible.

Every refbuild step writes through this module, because reproducibility is
not a property you can add afterwards — it is the sum of a dozen small
decisions, each of which is invisible when you get it wrong.

The decisions, and what each one is defending against:

* **JSON via `write_json`.** Fixed separators, sorted keys, `ensure_ascii`
  off, one trailing newline. Python's defaults leave a trailing space after
  every comma and iterate dicts in insertion order, so two builds that
  computed the same values could still differ in bytes.
* **`sorted()` on raw strings, never locale collation.** `LC_ALL` changes
  what `sort` considers order; `sorted()` on str is codepoint order and is
  the same on every machine. Any directory listing that reaches an output
  goes through `sorted()`.
* **`SOURCE_DATE_EPOCH`.** The manifest schema requires `created_utc`, which
  would make every build differ by construction. Honouring the
  reproducible-builds convention means a build can be pinned to a timestamp
  and reproduced exactly; unset, it uses now, which is right for a real build
  and is why the determinism test sets it.
* **Hashes over content, never over paths or mtimes.** `content_id` is a hash
  of the per-file hashes, so it is stable across a move of the bundle
  directory and changes if any byte of any payload file changes.

What byte-reproducible buys, concretely: `verify()` can tell "this bundle is
intact" from "this bundle is a different build of the same inputs", a v1
bundle can be diffed against v0 to show exactly what SHOOT enrichment added,
and a rebuild on another host is checkable rather than hopeful.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os

__all__ = [
    "PSI_DIR", "FAMILIES_DIR", "CURATION_DIR", "MANIFEST", "PAYLOAD_DIRS",
    "write_json", "read_json", "sha256_file", "iter_payload", "content_id",
    "created_utc", "ensure_layout",
]

#: Subdirectories of a bundle. `families` and `psi` are what Phase 1 fills;
#: `shoot_db` arrives with enrichment and is deliberately absent from
#: PAYLOAD_DIRS until then, so a v0 bundle does not claim to have one.
FAMILIES_DIR = "orthofinder_families"
PSI_DIR = "psi_matrices"
CURATION_DIR = "curation"
MANIFEST = "manifest.json"

#: Directories hashed into the manifest, in a fixed order.
PAYLOAD_DIRS = (FAMILIES_DIR, PSI_DIR, CURATION_DIR)


def write_json(path, obj) -> None:
    """The only way this package writes JSON into a bundle.

    `separators` is explicit because json.dump's default emits `", "` and
    `": "`, and a future change to that default would silently alter every
    byte we claim is reproducible.
    """
    text = json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False,
                      separators=(",", ": "))
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text + "\n")


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def sha256_file(path, _chunk=1 << 20) -> tuple[str, int]:
    """(hex digest, byte count). Streamed: a family fasta can be large."""
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as fh:
        while chunk := fh.read(_chunk):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def iter_payload(bundle_dir):
    """Every payload file, as (bundle-relative posix path, absolute path).

    Sorted by relative path, and `os.walk`'s directory list is sorted in
    place so the traversal itself is deterministic rather than filesystem
    order. The manifest is excluded — it cannot contain its own hash.
    """
    found = []
    for sub in PAYLOAD_DIRS:
        root = os.path.join(bundle_dir, sub)
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames.sort()
            for name in sorted(filenames):
                absolute = os.path.join(dirpath, name)
                rel = os.path.relpath(absolute, bundle_dir).replace(os.sep, "/")
                found.append((rel, absolute))
    found.sort(key=lambda pair: pair[0])
    return found


def content_id(contents: dict) -> str:
    """A single hash identifying a bundle's payload.

    Over the `contents` mapping rather than the files, so it is cheap to
    recompute from a manifest, and stable if the bundle is moved. Two bundles
    with the same content_id have byte-identical payloads.
    """
    h = hashlib.sha256()
    for rel in sorted(contents):
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(contents[rel]["sha256"].encode("ascii"))
        h.update(b"\0")
    return h.hexdigest()


def created_utc() -> str:
    """Build timestamp, honouring SOURCE_DATE_EPOCH.

    Without the override two builds of identical inputs differ in one field,
    and "byte-identical" becomes a claim with an asterisk. With it, the
    asterisk goes away and the determinism test can assert on whole files.
    """
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    when = (datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc)
            if epoch and epoch.strip().isdigit()
            else datetime.datetime.now(datetime.timezone.utc))
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_layout(bundle_dir) -> str:
    for sub in PAYLOAD_DIRS:
        os.makedirs(os.path.join(bundle_dir, sub), exist_ok=True)
    return bundle_dir
