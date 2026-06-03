#!/usr/bin/env python3
"""PlantSEED Curation Tool — Web Dashboard.

Single-file HTTP server that exposes the same logic as Curation_Tool.py
plus an in-process apply pipeline (the equivalent of
Update_Enzymes_in_PlantSEED.py). All non-HTTP / non-UI code lives in
`plantseed_curation`; this file is the API surface and main entry point.

Run with nothing more than Python installed:

    python3 Curation_Tool_Dashboard.py

PyYAML is the only third-party dependency and is auto-installed on first
run. Ctrl-C to stop.

CLI flags:
    --host 0.0.0.0   listen on all interfaces (default 127.0.0.1)
    --port 9000      specific port (default 8765, auto-fallback if taken)
    --no-browser     do not open a browser tab
"""

import os
import subprocess
import sys


# --- Bootstrap PyYAML once on first run (the dashboard's only third-party dep). --
def _bootstrap_pyyaml():
    try:
        import yaml  # noqa: F401
        return
    except ImportError:
        pass
    print("PyYAML not found — installing for your user (one-time setup)...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--user", "--quiet", "pyyaml"]
        )
    except Exception as e:
        print(f"\nAutomatic install failed: {e}")
        print("Please run:  pip install --user pyyaml")
        sys.exit(1)
    try:
        import yaml  # noqa: F401
    except ImportError:
        print("PyYAML installed but still not importable — please restart Python.")
        sys.exit(1)


_bootstrap_pyyaml()


import argparse
import json
import socket
import socketserver
import threading
import traceback
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler


# The package sits next to this script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plantseed_curation import (
    ACTION_DESCRIPTIONS,
    ACTION_FIELDS,
    ACTION_OPTIONS,
    COMPARTMENTS,
    DEFAULT_COMPARTMENT,
    DEFAULT_LOC_SOURCE,
    FIELD_PREFIXES,
    MULTI_COL_FIELDS,
    SCALAR_TYPES,
    append_curator_file,
    atomic_write,
    build_tsv_rows,
    confirm_curator_registry,
    curator_dir_path,
    delete_curator_file,
    detect_github_username,
    find_exact_match,
    find_substring_match,
    get_git_email,
    get_git_username,
    list_all_curators,
    list_curator_files,
    normalize_existing_dirname,
    parse_tsv_to_rows,
    paths,
    preview_for_enzyme,
    ranked_search,
    read_curator_file,
    required_empty_fields,
    run_apply,
    sanitize_filename,
    sanitize_username,
    validate_payload,
    write_curator_file,
)
from plantseed_curation.expasy import fetch_enzyme_dat
from plantseed_curation.frontend import INDEX_CSS, INDEX_HTML, INDEX_JS
from plantseed_curation.store import DataStore


# ============================================================================
# Shared in-memory store
# ============================================================================
STORE = DataStore()


# ============================================================================
# API plumbing
# ============================================================================
class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status
        self.message = message


def json_response(handler, payload, status=200):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


# ============================================================================
# API handlers — each returns the response payload (or raises ApiError)
# ============================================================================
def api_status(_r, _q, _b):
    return {
        "roles":        len(STORE.roles),
        "schema_keys":  list(STORE.schema_normalized.keys()),
        "expasy":       STORE.expasy_status(),
        "roles_file":   paths.ROLES_FILE,
        "curators_dir": paths.CURATORS_DIR,
    }


def api_search(_r, qs, _b):
    return ranked_search(STORE, qs.get("q", [""])[0])


def api_role(_r, qs, _b):
    name = qs.get("name", [""])[0]
    if not name:
        raise ApiError("missing 'name'")
    entry = STORE.find_role(name)
    if entry is None:
        return {"exists": False, "role": name}
    return {"exists": True, "entry": entry,
            "warnings": required_empty_fields(entry, STORE.schema_normalized)}


def api_xref(_r, qs, _b):
    field = qs.get("field", [""])[0]
    value = qs.get("value", [""])[0]
    exclude = qs.get("exclude", [""])[0] or None
    mode = qs.get("mode", ["exact"])[0]
    if not field or not value:
        return {"matches": [], "total": 0}
    if mode == "substring":
        m = find_substring_match(STORE.roles, field, value, exclude=exclude)
    else:
        m = find_exact_match(STORE.roles, field, value, exclude=exclude)
    return {"matches": m[:50], "total": len(m)}


def api_user(_r, _q, _b):
    display = get_git_username()
    info = detect_github_username(display)
    info["display_name"] = display
    info["dir_name"] = normalize_existing_dirname(info["username"])
    info["email"] = get_git_email()
    return info


def api_set_user(_r, _q, body):
    username = sanitize_username(body.get("username") or "") or "user"
    display = (body.get("display_name") or "").strip()
    username = normalize_existing_dirname(username)
    confirm_curator_registry(username, display, get_git_email())
    os.makedirs(curator_dir_path(username), exist_ok=True)
    return {"username": username, "display_name": display}


def api_files(_r, qs, _b):
    user = qs.get("user", [""])[0]
    if not user:
        raise ApiError("missing user")
    return {"files": list_curator_files(user),
            "dir":   curator_dir_path(user),
            "all_curators": list_all_curators()}


def api_file_read(_r, qs, _b):
    user = qs.get("user", [""])[0]
    name = qs.get("name", [""])[0]
    if not user or not name:
        raise ApiError("missing user/name")
    content = read_curator_file(user, name)
    return {"content": content, "rows": parse_tsv_to_rows(content)}


def api_file_create(_r, _q, body):
    user = (body.get("user") or "").strip()
    name = (body.get("name") or "").strip()
    if not user or not name:
        raise ApiError("missing user/name")
    name = sanitize_filename(name)
    if not name.endswith(".tsv"):
        name += ".tsv"
    fp = os.path.join(curator_dir_path(user), name)
    if not os.path.exists(fp):
        os.makedirs(curator_dir_path(user), exist_ok=True)
        atomic_write(fp, "")
    return {"name": name, "path": fp}


def api_file_save(_r, _q, body):
    user = (body.get("user") or "").strip()
    name = (body.get("name") or "").strip()
    content = body.get("content", "")
    if not user or not name:
        raise ApiError("missing user/name")
    fp = write_curator_file(user, name, content)
    return {"path": fp, "bytes": len(content)}


def api_file_append(_r, _q, body):
    user = (body.get("user") or "").strip()
    name = (body.get("name") or "").strip()
    rows = body.get("rows") or []
    if not user or not name:
        raise ApiError("missing user/name")
    if not isinstance(rows, list):
        raise ApiError("rows must be a list of strings")
    fp, n = append_curator_file(user, name, [str(r) for r in rows])
    return {"path": fp, "appended": n}


def api_file_delete(_r, _q, body):
    user = (body.get("user") or "").strip()
    name = (body.get("name") or "").strip()
    if not user or not name:
        raise ApiError("missing user/name")
    if not delete_curator_file(user, name):
        raise ApiError("file not found", 404)
    return {"removed": os.path.join(curator_dir_path(user), sanitize_filename(name))}


def api_validate(_r, _q, body):
    action = (body.get("action") or "").upper()
    enzyme = body.get("enzyme") or ""
    payload = body.get("payload") or {}
    errors, warnings = validate_payload(action, enzyme, payload, STORE)
    return {"errors": errors, "warnings": warnings, "ok": len(errors) == 0}


def api_build_rows(_r, _q, body):
    action = (body.get("action") or "").upper()
    enzyme = body.get("enzyme") or ""
    payload = body.get("payload") or {}
    rows, errors, warnings = build_tsv_rows(action, enzyme, payload, STORE)
    return {"rows": rows, "errors": errors, "warnings": warnings}


def api_preview(_r, _q, body):
    enzyme = body.get("enzyme") or ""
    rows = body.get("rows") or []
    if not enzyme:
        raise ApiError("missing enzyme")
    if not isinstance(rows, list):
        raise ApiError("rows must be a list")
    return preview_for_enzyme(enzyme, [str(r) for r in rows],
                              STORE.schema_normalized, STORE)


def api_apply(_r, _q, body):
    user = (body.get("user") or "").strip()
    tsv = body.get("tsv") or ""
    dry_run = bool(body.get("dry_run", False))
    if not tsv.strip():
        raise ApiError("nothing to apply (TSV is empty)")
    return run_apply(tsv, user, STORE.schema_normalized, dry_run=dry_run, store=STORE)


def api_reload(_r, _q, _b):
    STORE.load_roles(force=True)
    return {"roles": len(STORE.roles)}


def api_action_meta(_r, _q, _b):
    return {
        "actions": [
            {"name": a, "description": ACTION_DESCRIPTIONS[a],
             "fields": ACTION_FIELDS.get(a, [])}
            for a in ACTION_OPTIONS
        ],
        "multi_col":           MULTI_COL_FIELDS,
        "scalar_types":        SCALAR_TYPES,
        "field_prefixes":      list(FIELD_PREFIXES.keys()),
        "compartments":        [{"id": c, "name": n} for c, n in COMPARTMENTS],
        "default_compartment": DEFAULT_COMPARTMENT,
        "default_loc_source":  DEFAULT_LOC_SOURCE,
    }


def api_all_roles(_r, _q, _b):
    return {"roles": STORE.all_roles_summary(), "facets": STORE.facets()}


def api_expasy_refresh(_r, _q, _b):
    if os.path.exists(paths.ENZYME_DAT_CACHE):
        os.remove(paths.ENZYME_DAT_CACHE)
    with STORE.lock:
        STORE.ec_status = "idle"
        STORE.ec_entries = []
    STORE.start_load_expasy()
    return {"status": "refreshing"}


API_ROUTES = {
    ("GET",  "/api/status"):         api_status,
    ("GET",  "/api/search"):         api_search,
    ("GET",  "/api/role"):           api_role,
    ("GET",  "/api/roles/all"):      api_all_roles,
    ("GET",  "/api/xref"):           api_xref,
    ("GET",  "/api/user"):           api_user,
    ("POST", "/api/user"):           api_set_user,
    ("GET",  "/api/files"):          api_files,
    ("GET",  "/api/file"):           api_file_read,
    ("POST", "/api/file/create"):    api_file_create,
    ("POST", "/api/file/save"):      api_file_save,
    ("POST", "/api/file/append"):    api_file_append,
    ("POST", "/api/file/delete"):    api_file_delete,
    ("POST", "/api/validate"):       api_validate,
    ("POST", "/api/build"):          api_build_rows,
    ("POST", "/api/preview"):        api_preview,
    ("POST", "/api/apply"):          api_apply,
    ("POST", "/api/reload"):         api_reload,
    ("GET",  "/api/actions"):        api_action_meta,
    ("POST", "/api/expasy/refresh"): api_expasy_refresh,
}


# ============================================================================
# HTTP server
# ============================================================================
class Handler(BaseHTTPRequestHandler):
    server_version = "PlantSEEDCurationDashboard/3.0"

    def log_message(self, format, *args):
        sys.stderr.write(f"  [{self.command}] {self.path}\n")

    def _dispatch(self, method):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        if path in ("/", "/index.html"):
            return self._serve(INDEX_HTML, "text/html")
        if path == "/static/app.js":
            return self._serve(INDEX_JS, "text/javascript")
        if path == "/static/app.css":
            return self._serve(INDEX_CSS, "text/css")
        if path == "/static/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        handler = API_ROUTES.get((method, path))
        if not handler:
            self.send_error(404, f"unknown path {path}")
            return
        body = {}
        if method == "POST":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            if raw:
                try:
                    body = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    self.send_error(400, "invalid JSON body")
                    return
        try:
            STORE.load_roles()
            STORE.load_schema()
            result = handler(self, qs, body)
            json_response(self, result)
        except ApiError as e:
            json_response(self, {"error": e.message}, status=e.status)
        except Exception as e:
            sys.stderr.write("API error:\n" + traceback.format_exc())
            json_response(
                self,
                {"error": str(e), "trace": traceback.format_exc()},
                status=500,
            )

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def _serve(self, content, mime):
        body = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def find_free_port(host, preferred):
    for port in [preferred] + [preferred + i for i in range(1, 30)]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError("no free port found")


def make_server(host="127.0.0.1", port=8765, load_expasy=True):
    """Factory used by both `main` and the test suite. Returns (server, port)
    with roles + schema preloaded into STORE; the caller decides whether to
    call serve_forever() or shut it down."""
    paths.refresh_from_env()
    STORE.load_roles()
    STORE.load_schema()
    if load_expasy:
        STORE.start_load_expasy()
    actual_port = find_free_port(host, port)
    server = ThreadedServer((host, actual_port), Handler)
    # When called with port=0 the OS picks for us; report what it picked.
    bound_port = server.server_address[1]
    return server, bound_port


# ============================================================================
# Main entry
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="PlantSEED Curation Tool Dashboard.")
    parser.add_argument("--host", default="127.0.0.1",
                        help="bind address (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765,
                        help="port (default 8765, auto-fallback)")
    parser.add_argument("--no-browser", action="store_true",
                        help="don't open a browser tab")
    parser.add_argument("--no-expasy", action="store_true",
                        help="skip the Expasy enzyme.dat fetch (useful offline)")
    args = parser.parse_args()

    server, port = make_server(args.host, args.port, load_expasy=not args.no_expasy)
    url = f"http://{args.host}:{port}/"

    print()
    print("PlantSEED Curation Dashboard")
    print(f"  Roles:    {len(STORE.roles)} loaded from "
          f"{os.path.relpath(paths.ROLES_FILE, paths.BASE_DIR)}")
    print(f"  Curators: {os.path.relpath(paths.CURATORS_DIR, paths.BASE_DIR)}")
    if not args.no_expasy:
        print(f"  Expasy:   downloading/parsing in background")
    print(f"  URL:      {url}")
    print(f"  Stop:     Ctrl-C")
    print()

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    # Serve in a background thread so Ctrl-C cleanly shuts down on every OS.
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        while t.is_alive():
            t.join(timeout=0.5)
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
