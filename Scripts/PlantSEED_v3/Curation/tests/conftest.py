"""Shared pytest fixtures.

Each test that mutates roles/curators/registry gets a tmp directory hierarchy
plus PLANTSEED_* env vars pointing at it. The library re-reads those env
vars via paths.refresh_from_env() so nothing touches the real database.
"""

import json
import os
import shutil
import sys
import threading

import pytest


# Make the package importable without installation.
HERE = os.path.dirname(os.path.abspath(__file__))
CURATION_ROOT = os.path.dirname(HERE)
sys.path.insert(0, CURATION_ROOT)

FIXTURES = os.path.join(HERE, "fixtures")
MINI_ROLES = os.path.join(FIXTURES, "mini_roles.json")
MINI_SCHEMA = os.path.join(FIXTURES, "mini_schema.yaml")


def _seed_tmp_db(tmp_root):
    """Copy fixture files into a tmp tree and return the four path strings."""
    roles = os.path.join(tmp_root, "PlantSEED_Roles.json")
    schema = os.path.join(tmp_root, "PlantSEED_Schema.yaml")
    curators = os.path.join(tmp_root, "Curators")
    os.makedirs(curators, exist_ok=True)
    shutil.copy(MINI_ROLES, roles)
    shutil.copy(MINI_SCHEMA, schema)
    return {
        "base":     tmp_root,
        "roles":    roles,
        "schema":   schema,
        "curators": curators,
        "registry": os.path.join(curators, "curator_registry.json"),
    }


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Per-test temp database. Returns a dict of paths."""
    paths_dict = _seed_tmp_db(str(tmp_path))
    monkeypatch.setenv("PLANTSEED_BASE_DIR",         paths_dict["base"])
    monkeypatch.setenv("PLANTSEED_ROLES_FILE",       paths_dict["roles"])
    monkeypatch.setenv("PLANTSEED_SCHEMA_FILE",      paths_dict["schema"])
    monkeypatch.setenv("PLANTSEED_CURATORS_DIR",     paths_dict["curators"])
    monkeypatch.setenv("PLANTSEED_CURATOR_REGISTRY", paths_dict["registry"])
    # Refresh module-level path constants so library imports honour the new env.
    from plantseed_curation import paths as p
    p.refresh_from_env()
    yield paths_dict
    # monkeypatch unsets the env vars on teardown; do one more refresh so
    # other tests don't see stale values.
    p.refresh_from_env()


@pytest.fixture
def store(tmp_db):
    """A DataStore pointed at tmp_db, with roles + schema preloaded."""
    from plantseed_curation.store import DataStore
    s = DataStore()
    s.load_roles(force=True)
    s.load_schema(force=True)
    return s


@pytest.fixture
def schema(tmp_db):
    from plantseed_curation.schema import load_schema
    return load_schema()


@pytest.fixture
def dashboard_server(tmp_db):
    """Start the dashboard's HTTP server in a background thread on a random
    free port. Yields (base_url, server) so tests can issue requests; server
    is shut down on teardown."""
    import Curation_Tool_Dashboard as dash
    # Force a fresh DataStore state so prior tests don't leak in.
    dash.STORE.roles = []
    dash.STORE.roles_mtime = None
    dash.STORE.schema_normalized = {}
    dash.STORE.ec_entries = []
    dash.STORE.ec_status = "idle"
    server, port = dash.make_server(host="127.0.0.1", port=0, load_expasy=False)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base_url = f"http://127.0.0.1:{port}"
    yield base_url, server
    server.shutdown()
    server.server_close()


@pytest.fixture
def http_client(dashboard_server):
    """Tiny POST/GET helper around urllib so we don't pull in requests."""
    import urllib.error
    import urllib.request

    base_url, _ = dashboard_server

    def _req(method, path, body=None):
        url = base_url + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if data else {}
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    return _req
