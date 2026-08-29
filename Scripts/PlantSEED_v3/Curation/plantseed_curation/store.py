"""Thread-safe in-memory cache of roles, schema, and the Expasy enzyme list.

The dashboard's HTTP handlers and the CLI both use a DataStore so they share
the same `roles_index` lookups, facet sets, and Expasy state machine.
"""

import copy
import json
import os
import threading

from . import paths
from .expasy import fetch_enzyme_dat
from .schema import load_schema


class DataStore:
    def __init__(self):
        self.lock = threading.RLock()
        self.roles = []
        self.roles_mtime = None
        self.schema_raw = {}
        self.schema_normalized = {}
        self.ec_entries = []
        self.ec_status = "idle"
        self.ec_error = ""
        self.role_index = {}
        self.facet_subsystems = []
        self.facet_types = []
        self.facet_curators = []

    def load_roles(self, force=False):
        with self.lock:
            try:
                mtime = os.path.getmtime(paths.ROLES_FILE)
            except OSError:
                return
            if force or self.roles_mtime != mtime:
                with open(paths.ROLES_FILE) as f:
                    self.roles = json.load(f)
                self.roles_mtime = mtime
                self._reindex()

    def _reindex(self):
        self.role_index = {r["role"]: r for r in self.roles}
        subs, types, curators = set(), set(), set()
        for r in self.roles:
            for s in r.get("subsystems", []) or []:
                subs.add(s)
            t = r.get("type")
            if t:
                types.add(t)
            for cu in r.get("curators", []) or []:
                curators.add(cu)
        self.facet_subsystems = sorted(subs)
        self.facet_types = sorted(types)
        self.facet_curators = sorted(curators)

    def load_schema(self, force=False):
        with self.lock:
            if self.schema_normalized and not force:
                return
            self.schema_normalized = load_schema()

    def find_role(self, name):
        with self.lock:
            r = self.role_index.get(name)
            return copy.deepcopy(r) if r else None

    def all_roles_summary(self):
        with self.lock:
            out = []
            for r in self.roles:
                out.append({
                    "role":           r.get("role"),
                    "type":           r.get("type", ""),
                    "include":        r.get("include", True),
                    "n_features":     len(r.get("features", []) or []),
                    "n_reactions":    len(r.get("reactions", []) or []),
                    "subsystems":     list(r.get("subsystems", []) or [])[:3],
                    "curators":       list(r.get("curators", []) or []),
                    "is_transporter": r.get("is_transporter", False),
                })
            return out

    def facets(self):
        with self.lock:
            return {
                "subsystems": self.facet_subsystems,
                "types":      self.facet_types,
                "curators":   self.facet_curators,
            }

    def start_load_expasy(self, download=False):
        """Load the ExPASy list in the background.

        `download` defaults off, matching `expasy.fetch_enzyme_dat`: a packaged
        consumer gets whatever is cached and a clear error otherwise, and only
        an interactive tool asks for the network. Without this the method was a
        public way to make any process that holds a DataStore fetch 9 MB from
        ftp.expasy.org.
        """
        with self.lock:
            if self.ec_status in ("loading", "loaded"):
                return
            self.ec_status = "loading"
        threading.Thread(target=self._load_expasy_thread, args=(download,),
                         daemon=True).start()

    def _load_expasy_thread(self, download=False):
        try:
            entries = fetch_enzyme_dat(download=download)
            with self.lock:
                self.ec_entries = entries
                self.ec_status = "loaded" if entries else "error"
                self.ec_error = "" if entries else "no entries parsed"
        except Exception as e:
            with self.lock:
                self.ec_status = "error"
                self.ec_error = str(e)

    def expasy_status(self):
        with self.lock:
            return {"status": self.ec_status, "count": len(self.ec_entries),
                    "error": self.ec_error}

    def set_expasy_entries(self, entries):
        """Inject Expasy entries synchronously — used by tests and by the
        CLI when it wants to skip the network fetch."""
        with self.lock:
            self.ec_entries = entries or []
            self.ec_status = "loaded" if entries else "idle"
            self.ec_error = ""
