"""Per-curator TSV file I/O. Atomic writes; no auto-backups."""

import os

from . import paths
from .identity import atomic_write, sanitize_filename


def curator_dir_path(username):
    return os.path.join(paths.CURATORS_DIR, username)


def list_curator_files(username):
    path = curator_dir_path(username)
    if not os.path.isdir(path):
        return []
    out = []
    for name in sorted(os.listdir(path)):
        if not name.endswith(".tsv"):
            continue
        fp = os.path.join(path, name)
        try:
            st = os.stat(fp)
            with open(fp) as f:
                lines = f.readlines()
            row_count = sum(1 for ln in lines if ln.strip() and not ln.startswith("#"))
        except OSError:
            row_count = 0
            st = None
        out.append({
            "name":    name,
            "size":    st.st_size if st else 0,
            "mtime":   st.st_mtime if st else 0,
            "rows":    row_count,
            "relpath": os.path.relpath(fp, paths.BASE_DIR),
        })
    return out


def list_all_curators():
    if not os.path.isdir(paths.CURATORS_DIR):
        return []
    out = []
    for d in sorted(os.listdir(paths.CURATORS_DIR)):
        dp = os.path.join(paths.CURATORS_DIR, d)
        if not os.path.isdir(dp):
            continue
        tsvs = [n for n in os.listdir(dp) if n.endswith(".tsv")]
        out.append({"name": d, "n_files": len(tsvs)})
    return out


def read_curator_file(username, filename):
    fp = os.path.join(curator_dir_path(username), sanitize_filename(filename))
    if not os.path.isfile(fp):
        return ""
    with open(fp) as f:
        return f.read()


def write_curator_file(username, filename, content):
    os.makedirs(curator_dir_path(username), exist_ok=True)
    fp = os.path.join(curator_dir_path(username), sanitize_filename(filename))
    if content and not content.endswith("\n"):
        content += "\n"
    atomic_write(fp, content)
    return fp


def append_curator_file(username, filename, rows):
    if not rows:
        return None, 0
    os.makedirs(curator_dir_path(username), exist_ok=True)
    fp = os.path.join(curator_dir_path(username), sanitize_filename(filename))
    needs_leading_nl = False
    if os.path.exists(fp) and os.path.getsize(fp) > 0:
        with open(fp, "rb") as f:
            try:
                f.seek(-1, os.SEEK_END)
                needs_leading_nl = f.read(1) != b"\n"
            except OSError:
                pass
    existing = ""
    if os.path.exists(fp):
        with open(fp) as f:
            existing = f.read()
    new_text = existing + ("\n" if needs_leading_nl else "")
    for r in rows:
        new_text += r.rstrip("\n") + "\n"
    atomic_write(fp, new_text)
    return fp, len(rows)


def delete_curator_file(username, filename):
    fp = os.path.join(curator_dir_path(username), sanitize_filename(filename))
    if not os.path.exists(fp):
        return False
    os.remove(fp)
    return True


def parse_tsv_to_rows(text):
    """Structured rendering of a TSV blob for UI display. Each row dict has
    {lineno, raw, valid, cols, enzyme?, action?, field?, value?, extra?}."""
    out = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip("\r\n")
        if not line.strip() or line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) < 2:
            out.append({"lineno": lineno, "raw": line, "valid": False, "cols": cols})
            continue
        out.append({
            "lineno": lineno, "raw": line, "valid": True, "cols": cols,
            "enzyme": cols[0], "action": cols[1],
            "field":  cols[2] if len(cols) > 2 else "",
            "value":  cols[3] if len(cols) > 3 else "",
            "extra":  cols[4] if len(cols) > 4 else "",
        })
    return out
