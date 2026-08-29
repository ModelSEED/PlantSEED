"""Expasy enzyme.dat fetch/parse.

This module is the single canonical source. Returns a list of dicts shaped
{"label": "Description (EC X.Y.Z.W)", "ec": "X.Y.Z.W"}.

**The network is opt-in.** `fetch_enzyme_dat()` parses a local cache and does
not download; only `fetch_enzyme_dat(download=True)` will fetch. Three reasons,
and the first is the one that used to bite:

* The CDM Task Service rejects, at image review, a container that pulls files
  from remote sources during a run. A default that downloads makes every
  packaged consumer a liability even when it never actually fires.
* enzyme.dat changes. Two runs of the same code against different vintages are
  not the same run, and nothing here records which vintage was used.
* A container may have no egress, turning a curation convenience into a hard
  failure a long way from where anyone can diagnose it.

The only caller that wants the network is `Curation_Tool_Dashboard.py`, which
is an unpackaged curator tool on a workstation, and it now says so explicitly.
"""

import os
import ssl
import tempfile
import urllib.request

from . import paths

__all__ = ["fetch_enzyme_dat", "parse_enzyme_dat", "download_enzyme_dat"]

#: Truthful, so ExPASy's operators can see who is calling and rate-limit or
#: contact us rather than guess. The old value claimed to be a browser.
USER_AGENT = "plantseed-curation (+https://github.com/ModelSEED/PlantSEED)"


def download_enzyme_dat(dest=None, url=None, timeout=60):
    """Fetch enzyme.dat to `dest`. Explicit, never implicit.

    Certificates are verified. They were not: this module used to set
    `check_hostname = False` and `verify_mode = CERT_NONE`, which accepts any
    certificate and so accepts anything a network attacker substitutes — and
    the result becomes part of the curation search vocabulary. Verification
    against ftp.expasy.org works, so there was nothing to work around.

    Written via a temporary file and renamed, because the previous code treated
    any non-empty file as a good cache: a download interrupted halfway left a
    truncated file that was never re-fetched and parsed as though complete.
    """
    dest = dest or paths.ENZYME_DAT_CACHE
    url = url or paths.ENZYME_DAT_URL
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    parent = os.path.dirname(dest) or "."
    os.makedirs(parent, exist_ok=True)

    fd, staged = tempfile.mkstemp(dir=parent, prefix=".enzyme_dat-")
    try:
        # fdopen outermost so the descriptor is closed however this exits,
        # including a connection failure before the first byte arrives.
        with os.fdopen(fd, "wb") as out:
            with urllib.request.urlopen(
                req, context=ssl.create_default_context(), timeout=timeout
            ) as response:
                while chunk := response.read(1 << 20):
                    out.write(chunk)
        if os.path.getsize(staged) == 0:
            raise OSError(f"{url} returned an empty body")
        os.replace(staged, dest)          # atomic: no half-written cache
    except BaseException:
        if os.path.exists(staged):
            os.unlink(staged)
        raise
    return dest


def parse_enzyme_dat(path=None):
    """Parse a local enzyme.dat into label/ec dicts. No network, ever."""
    path = path or paths.ENZYME_DAT_CACHE
    with open(path, encoding="latin-1") as f:
        text = f.read()

    entries = []
    for block in text.split("\n//\n"):
        ec_id = ""
        de_lines = []
        for line in block.strip().split("\n"):
            if line.startswith("ID   "):
                ec_id = line[5:].strip()
            elif line.startswith("DE   "):
                de_lines.append(line[5:].strip())
        if ec_id and de_lines:
            de_full = " ".join(de_lines)
            if de_full:
                de_full = de_full[0].upper() + de_full[1:]
            de_full = de_full.rstrip(".")
            entries.append({"label": f"{de_full} (EC {ec_id})", "ec": ec_id})
    return entries


def fetch_enzyme_dat(download=False):
    """The cached enzyme list.

    `download=False` (the default) parses whatever is cached and raises
    FileNotFoundError naming the fix if there is nothing there. Pass
    `download=True` only from an interactive tool on a workstation.
    """
    cache = paths.ENZYME_DAT_CACHE
    have = os.path.exists(cache) and os.path.getsize(cache) > 0
    if not have:
        if not download:
            raise FileNotFoundError(
                f"no cached enzyme.dat at {cache}. This does not download by "
                f"default — a packaged run must not fetch from the network. "
                f"Either set PLANTSEED_ENZYME_DAT_CACHE to an existing copy, "
                f"or call fetch_enzyme_dat(download=True) from an interactive "
                f"tool."
            )
        download_enzyme_dat(cache)
    return parse_enzyme_dat(cache)
