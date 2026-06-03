"""Curator identity helpers — git/gh username detection, the registry, and
the atomic-write primitive used by every file writer in the package."""

import json
import os
import re
import subprocess

from . import paths


def sanitize_filename(name):
    name = os.path.basename(name or "")
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def sanitize_username(name):
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def atomic_write(path, content):
    """Write to <path>.tmp then os.replace — never leaves a half-written file."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(content)
    os.replace(tmp, path)


def _run(cmd, timeout=5):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def get_git_username():
    r = _run(["git", "config", "user.name"])
    return r.stdout.strip() if (r and r.returncode == 0 and r.stdout.strip()) else ""


def get_git_email():
    r = _run(["git", "config", "user.email"])
    return r.stdout.strip() if (r and r.returncode == 0 and r.stdout.strip()) else ""


def get_gh_username_gh():
    r = _run(["gh", "api", "user", "--jq", ".login"])
    return r.stdout.strip().lower() if (r and r.returncode == 0 and r.stdout.strip()) else None


def get_gh_username_from_remote():
    r = _run(["git", "remote", "get-url", "origin"])
    if r and r.returncode == 0:
        m = re.search(r"(?:git@github\.com:|https?://github\.com/)([^/@]+)/", r.stdout.strip())
        if m:
            return m.group(1).lower()
    return None


def load_curator_registry():
    if os.path.exists(paths.CURATOR_REGISTRY):
        try:
            with open(paths.CURATOR_REGISTRY) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_curator_registry(registry):
    os.makedirs(paths.CURATORS_DIR, exist_ok=True)
    atomic_write(paths.CURATOR_REGISTRY, json.dumps(registry, indent=2))


def detect_github_username(display_name):
    """Return {"username", "source", "candidates"}.
    Source-of-truth precedence: saved registry by email → gh CLI → git remote
    → git user.name sanitized."""
    email = get_git_email()
    registry = load_curator_registry()
    candidates = []  # (label, value)
    if email:
        for gh_user, info in registry.items():
            if info.get("github_email") == email:
                candidates.append(("registry", gh_user))
                break  # Bug fix #5: stop at the first match (was implicit before)
    gh_user = get_gh_username_gh()
    if gh_user:
        candidates.append(("gh CLI", gh_user))
    gh_user = get_gh_username_from_remote()
    if gh_user:
        candidates.append(("git remote", gh_user))
    fallback = sanitize_username(display_name) or "user"
    candidates.append(("git user.name", fallback))
    return {
        "username": candidates[0][1],
        "source":   candidates[0][0],
        "candidates": [{"source": s, "value": v} for s, v in candidates],
    }


def normalize_existing_dirname(username):
    """If a Curators/<dir> already exists with a case-different name, prefer
    the on-disk spelling so we don't create a second directory."""
    if os.path.isdir(paths.CURATORS_DIR):
        for d in os.listdir(paths.CURATORS_DIR):
            dp = os.path.join(paths.CURATORS_DIR, d)
            if (os.path.isdir(dp) and d.lower() == username.lower()
                    and d.lower() != "curators"):
                return d
    return username


def confirm_curator_registry(username, display_name, email):
    registry = load_curator_registry()
    if username and username not in registry:
        registry[username] = {"display_name": display_name or "", "github_email": email or ""}
        save_curator_registry(registry)
