"""The one-way dependency rule, enforced.

PlantSEED v3 is delivered through four platforms — modelseed.org, KBase
Narratives, the CDM Task Service, and KIND*AI. The science core is shared; the
adapters are not, and they live in a separate repository that depends on this
one. The dependency must never run the other way: the moment a platform client
is imported here, the core stops being portable, every container has to carry
KBase, and CTS's no-runtime-downloads rule becomes unsatisfiable.

That is easy to violate by accident and expensive to unpick later, so it is a
test rather than a code-review convention.

Scope is the four packages that actually ship in the wheel. Sibling scripts in
the same directories (Test-Model-FBA.py, Curation_Tool.py,
annotate-arabidopsis-genome.py) are local tooling, are not packaged, and may
import whatever they like — Test-Model-FBA.py imports cobrakbase today.

Implemented with ast rather than grep so that prose in a docstring naming a
forbidden module does not trip it. This docstring is the proof.
"""

import ast
import os

import pytest

#: Top-level modules the core may not import. Each maps to why it is banned, so
#: a failure explains itself instead of just pointing at a list.
FORBIDDEN_IMPORTS = {
    "installed_clients": "KBase SDK generated clients — adapter-only",
    "cobrakbase": "unconditionally constructs KBaseAPI and vendors a workspace client",
    "kbutillib": "resolves its own deps via sibling git clones; not pip-installable",
    "biokbase": "KBase runtime shim, present only inside the SDK base image",
    "solara": "the KIND*AI app shell is a delivery concern, not a science one",
    "pyspark": "lakehouse publication belongs to the adapter layer",
    "modelseedpy": (
        "not a declared dependency — pinned by commit in deps/external.json and "
        "fetched, because it is developed far ahead of PyPI. Importing it here "
        "would break `pip install plantseed`. Adapter-only."
    ),
}

#: Environment variables that only exist inside a specific platform's runtime.
#: Reading one in the core means the core has assumed where it is running.
FORBIDDEN_ENV = {
    "SDK_CALLBACK_URL": "KBase JobRunner callback server",
    "KB_AUTH_TOKEN": "KBase auth; the core takes credentials as arguments",
}

_CORE_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)

PACKAGES = {
    "plantseed_core": os.path.join(_CORE_ROOT, "Core", "plantseed_core"),
    "plantseed_annotation": os.path.join(_CORE_ROOT, "Annotation", "plantseed_annotation"),
    "plantseed_curation": os.path.join(_CORE_ROOT, "Curation", "plantseed_curation"),
    "plantseed_model": os.path.join(_CORE_ROOT, "Model", "plantseed_model"),
}


def _python_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in sorted(filenames):
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def _imported_roots(tree):
    """Top-level module name of every import in the file."""
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:          # relative import, necessarily internal
                continue
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def _env_lookups(tree):
    """String constants used as a subscript or argument against os.environ/getenv.

    Narrow on purpose: it finds os.environ["X"], os.environ.get("X") and
    os.getenv("X"), and ignores the same string appearing in a docstring.
    """
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            val = node.value
            if (isinstance(val, ast.Attribute) and val.attr == "environ"
                    and isinstance(node.slice, ast.Constant)
                    and isinstance(node.slice.value, str)):
                found.add(node.slice.value)
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
            if name in ("getenv", "get") and node.args:
                a0 = node.args[0]
                if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                    found.add(a0.value)
    return found


def _all_core_files():
    out = []
    for pkg, root in PACKAGES.items():
        if os.path.isdir(root):
            out.extend((pkg, p) for p in _python_files(root))
    return out


CORE_FILES = _all_core_files()


def test_every_package_was_found():
    """A renamed or moved package must not silently empty this test suite."""
    missing = [p for p, root in PACKAGES.items() if not os.path.isdir(root)]
    assert not missing, f"package directories not found: {missing}"
    assert len(CORE_FILES) > 15, f"suspiciously few core files scanned: {len(CORE_FILES)}"


@pytest.mark.parametrize("pkg,path", CORE_FILES,
                         ids=[f"{p}:{os.path.basename(f)}" for p, f in CORE_FILES])
def test_no_platform_imports(pkg, path):
    with open(path) as fh:
        tree = ast.parse(fh.read(), filename=path)
    bad = _imported_roots(tree) & FORBIDDEN_IMPORTS.keys()
    assert not bad, (
        f"{os.path.relpath(path, _CORE_ROOT)} imports "
        + ", ".join(f"{m} ({FORBIDDEN_IMPORTS[m]})" for m in sorted(bad))
        + ". Adapters belong in ModelSEED/plantseed-delivery, which depends on "
          "this package; the dependency must not run the other way."
    )


@pytest.mark.parametrize("pkg,path", CORE_FILES,
                         ids=[f"{p}:{os.path.basename(f)}" for p, f in CORE_FILES])
def test_no_platform_environment_variables(pkg, path):
    with open(path) as fh:
        tree = ast.parse(fh.read(), filename=path)
    bad = _env_lookups(tree) & FORBIDDEN_ENV.keys()
    assert not bad, (
        f"{os.path.relpath(path, _CORE_ROOT)} reads "
        + ", ".join(f"{v} ({FORBIDDEN_ENV[v]})" for v in sorted(bad))
        + ". The core must not infer which platform it is running on."
    )


@pytest.mark.parametrize("pkg,path", CORE_FILES,
                         ids=[f"{p}:{os.path.basename(f)}" for p, f in CORE_FILES])
def test_does_not_use_modelseedpys_biochemistry_loader(pkg, path):
    """PlantSEED reads ModelSEEDDatabase's sharded JSON directly.

    ModelSEEDDatabase `dev` — the branch we pin, and the one modelseed-api uses
    — stores biochemistry as 111 sharded JSON files and has no reactions.tsv or
    compounds.tsv at all. ModelSEEDpy's loader expects those TSVs, i.e. the
    `master` layout. Rather than carry two layouts, we read the JSON directly
    and never call that loader. See deps/README.md.
    """
    with open(path) as fh:
        tree = ast.parse(fh.read(), filename=path)
    banned = {"from_local", "from_local2", "from_github"}
    hits = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in banned
    }
    assert not hits, (
        f"{os.path.relpath(path, _CORE_ROOT)} calls {sorted(hits)} — "
        "ModelSEEDpy's biochemistry loader expects the master-branch TSVs. "
        "Read the sharded dev JSON directly instead."
    )


def test_core_has_no_third_party_imports():
    """plantseed_core specifically is pure stdlib — no extras, ever.

    The other three may reach for an extra (curation uses PyYAML). This one
    underpins all of them and every container, so it stays dependency-free.
    """
    stdlib = set(getattr(__import__("sys"), "stdlib_module_names", ()))
    internal = set(PACKAGES)
    offenders = {}
    for pkg, path in CORE_FILES:
        if pkg != "plantseed_core":
            continue
        with open(path) as fh:
            tree = ast.parse(fh.read(), filename=path)
        extra = {m for m in _imported_roots(tree) if m not in stdlib and m not in internal}
        if extra:
            offenders[os.path.basename(path)] = sorted(extra)
    assert not offenders, f"plantseed_core must stay pure stdlib; found {offenders}"
