"""Expasy enzyme.dat fetch/parse.

Bug fix #1: this module is the single canonical source. Returns a list of
dicts shaped {"label": "Description (EC X.Y.Z.W)", "ec": "X.Y.Z.W"} — the
older CLI's string-only return is gone.
"""

import os
import ssl
import urllib.request

from . import paths


def fetch_enzyme_dat():
    if not os.path.exists(paths.ENZYME_DAT_CACHE) or os.path.getsize(paths.ENZYME_DAT_CACHE) == 0:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            paths.ENZYME_DAT_URL, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=60) as response, \
                open(paths.ENZYME_DAT_CACHE, "wb") as out_file:
            out_file.write(response.read())

    entries = []
    with open(paths.ENZYME_DAT_CACHE, encoding="latin-1") as f:
        text = f.read()
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
