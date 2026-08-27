"""One declaration per capability; every platform's interface generated from it.

PlantSEED has to describe the same runnable thing in five places:

    KBase          ui/narrative/methods/<name>/{spec.json,display.yaml}
    modelseed.org  a Pydantic request model + two dispatcher map entries
    CTS            a JSON submit body (argv, no spaces, one file parameter)
    koros/KIND*AI  `plantseed capabilities --json`, ingested into the agent's
                   orientation prompt
    the CLI        argparse

Hand-maintaining five descriptions of one function is how they drift. So a
capability is declared once, here, and `export_manifest()` emits the machine-
readable form that the generators in ModelSEED/plantseed-delivery consume.

The `capabilities --json` emit is not incidental: KIND*AI's CAPABILITY_CONTRACT
specifies exactly that shape as the way a tool describes itself to the agent, so
the artifact that drives codegen is also the integration.

Design constraints, all inherited from the strictest consumer:

  * Pure stdlib. This module is imported by every container.
  * Declarative and introspectable without importing the implementation, so a
    generator can build a spec without importing cobrapy.
  * Parameter names must survive CTS's argv rules — see NAME_RE. CTS rejects
    arguments matching anything outside ^[\\w\\./][\\w\\.,+/-]*$ and forbids a
    leading dash, so nothing may rely on flags or on spaces.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

from .errors import CapabilityError

__all__ = [
    "Param",
    "FileParam",
    "Artifact",
    "Resources",
    "Capability",
    "capability",
    "get",
    "names",
    "all_capabilities",
    "export_manifest",
    "clear",
    "SELF_DESCRIPTION",
]

#: Capability and parameter names. Deliberately narrower than Python
#: identifiers: these become CLI flags, JSON keys, KBase spec ids and CTS argv,
#: and the intersection of those is lowercase alphanumeric plus underscore.
NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

PARAM_TYPES = ("str", "int", "float", "bool", "enum", "file", "dir")

#: Repo-relative path to the owner-authored, agent-facing description of what
#: PlantSEED is for. Emitted as the manifest's `self_description.source`.
SELF_DESCRIPTION = "Scripts/PlantSEED_v3/for-agents.md"

#: PARAM_TYPES -> JSON Schema primitive, for `Capability.input_schema`. `file`
#: and `dir` are strings because every platform passes a path; what differs --
#: a workspace ref on KBase, a mount-relative name on CTS -- is the caller's
#: business, not the schema's. `enum` is absent: it emits `{"enum": choices}`
#: with no `type`, so non-string choices stay valid.
_JSON_TYPES = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "file": "string",
    "dir": "string",
}


def _check_name(name: str, what: str) -> str:
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise CapabilityError(
            f"{what} {name!r} must match {NAME_RE.pattern} — it becomes a CLI "
            "flag, a JSON key, a KBase spec id and a CTS argv token"
        )
    return name


@dataclass(frozen=True, slots=True)
class Param:
    """A non-file parameter.

    `default=None` with `required=False` means genuinely optional. Note CTS
    cannot pass flags at all, so on that platform every parameter arrives via
    params.json — which is why defaults live here rather than in argparse.
    """

    name: str
    type: str = "str"
    required: bool = False
    default: Any = None
    choices: tuple[Any, ...] = ()
    help: str = ""

    def __post_init__(self):
        _check_name(self.name, "parameter name")
        if self.type not in PARAM_TYPES:
            raise CapabilityError(
                f"parameter {self.name!r}: type {self.type!r} not in {PARAM_TYPES}")
        if self.type == "enum" and not self.choices:
            raise CapabilityError(f"parameter {self.name!r}: enum needs choices")
        if self.choices and self.default is not None and self.default not in self.choices:
            raise CapabilityError(
                f"parameter {self.name!r}: default {self.default!r} not in {self.choices}")
        if self.required and self.default is not None:
            raise CapabilityError(
                f"parameter {self.name!r}: required parameters cannot have a default")


@dataclass(frozen=True, slots=True)
class FileParam:
    """An input file.

    `fmt` is advisory for humans and generators — the KBase generator maps it
    to `valid_ws_types`, the CTS generator to nothing (CTS passes files
    positionally in the input mount).
    """

    name: str
    fmt: str = ""
    required: bool = False
    multiple: bool = False
    help: str = ""

    type: str = field(default="file", init=False)

    def __post_init__(self):
        _check_name(self.name, "parameter name")


@dataclass(frozen=True, slots=True)
class Artifact:
    """An output file written to the output directory root.

    Flat by construction: CTS collects results with `find <mount> -type f` and
    strips the mount prefix, so nesting buys nothing and costs portability.
    """

    key: str
    filename: str
    schema: str | None = None
    help: str = ""

    def __post_init__(self):
        _check_name(self.key, "artifact key")
        if "/" in self.filename:
            raise CapabilityError(
                f"artifact {self.key!r}: filename {self.filename!r} must be flat — "
                "CTS discovers outputs with `find` and strips the mount prefix")


@dataclass(frozen=True, slots=True)
class Resources:
    """Requested compute, in platform-neutral units.

    Deliberately advisory. KBase does not let an app declare resources at all
    (they live in the catalog, admin-set), CTS takes them per-submission, and
    modelseed.org runs whatever the Celery worker has. So this is what the
    generators use as a default and what a human uses to sanity-check against
    the CTS 100-CPU-hour cap.
    """

    cpus: int = 1
    memory_gb: int = 4
    runtime_h: float = 1.0
    refdata: str | None = None

    def __post_init__(self):
        for f_ in ("cpus", "memory_gb"):
            if getattr(self, f_) < 1:
                raise CapabilityError(f"resources.{f_} must be >= 1")
        if self.runtime_h <= 0:
            raise CapabilityError("resources.runtime_h must be > 0")

    @property
    def cpu_hours(self) -> float:
        """CTS bills cpus x containers x runtime against a default 100 cap."""
        return self.cpus * self.runtime_h


@dataclass(frozen=True, slots=True)
class Capability:
    """A declared unit of work, described once and emitted many ways.

    `when` and `guarantee` are the agent-facing depth. They are declared here,
    beside the code they describe, because every harness that renders them
    requires the *owner* to author them — KIND*AI's capability contract makes
    this an invariant and forbids the harness from writing its own version.
    An empty `when` is legal but means the roster line says only what the tool
    is, never when to prefer it over hand-rolling the primitive.
    """

    name: str
    summary: str
    params: tuple[Param | FileParam, ...] = ()
    outputs: tuple[Artifact, ...] = ()
    resources: Resources = field(default_factory=Resources)
    image: str | None = None
    when: str = ""
    guarantee: str = ""
    func: Callable[..., Any] | None = None

    def param(self, name: str) -> Param | FileParam:
        for p in self.params:
            if p.name == name:
                return p
        raise KeyError(name)

    @property
    def file_params(self) -> tuple[FileParam, ...]:
        return tuple(p for p in self.params if isinstance(p, FileParam))

    def input_schema(self) -> dict:
        """The parameters as a JSON Schema object.

        An MCP tool takes a JSON Schema `inputSchema`, KING's MCP explorer
        builds its form from one, and anything validating a call without
        importing the implementation needs one. Emitting it here means the
        mapping from `PARAM_TYPES` exists once; a consumer that re-derived it
        would be a second source of truth for the same declaration.

        `additionalProperties` is false on purpose — a mistyped parameter name
        should be a rejected call, not a silently ignored one.
        """
        props: dict = {}
        required: list[str] = []
        for p in self.params:
            if isinstance(p, FileParam):
                schema = {"type": "string"}
                if p.multiple:
                    schema = {"type": "array", "items": schema}
            elif p.type == "enum":
                schema = {"enum": list(p.choices)}
            else:
                schema = {"type": _JSON_TYPES[p.type]}

            desc = " ".join(x for x in (p.help, f"Format: {p.fmt}."
                                        if getattr(p, "fmt", "") else "") if x)
            if desc:
                schema["description"] = desc
            if getattr(p, "default", None) is not None:
                schema["default"] = p.default

            props[p.name] = schema
            if p.required:
                required.append(p.name)

        out = {"type": "object", "properties": props,
               "additionalProperties": False}
        if required:
            out["required"] = required
        return out

    def to_dict(self) -> dict:
        """The wire form. `func` is dropped — a generator must never need to
        import the implementation to build a spec.

        `input_schema` is derived from `params` rather than declared, and is
        carried here so a consumer gets it without reimplementing the mapping.
        """
        return {
            "name": self.name,
            "summary": self.summary,
            "when": self.when,
            "guarantee": self.guarantee,
            "image": self.image,
            "params": [asdict(p) for p in self.params],
            "input_schema": self.input_schema(),
            "outputs": [asdict(a) for a in self.outputs],
            "resources": asdict(self.resources),
        }


_REGISTRY: dict[str, Capability] = {}


def capability(
    *,
    name: str,
    summary: str,
    params: Sequence[Param | FileParam] = (),
    outputs: Sequence[Artifact] = (),
    resources: Resources | None = None,
    image: str | None = None,
    when: str = "",
    guarantee: str = "",
):
    """Register the decorated function as a capability.

    Signature-compatible in spirit with KBUtilLib's `@capability`, so that if
    that library ever becomes pip-installable and token-free the two registries
    can be reconciled by renaming rather than rewriting. We do not depend on it
    today: it resolves its own dependencies via sibling git clones and sets
    KB_AUTH_TOKEN in a constructor, neither of which survives containerisation.
    """
    _check_name(name, "capability name")
    if not summary or not summary.strip():
        raise CapabilityError(f"capability {name!r}: summary is required — it is "
                              "what the agent sees when deciding whether to use it")

    seen: set[str] = set()
    for p in params:
        if p.name in seen:
            raise CapabilityError(f"capability {name!r}: duplicate parameter {p.name!r}")
        seen.add(p.name)

    keys: set[str] = set()
    for a in outputs:
        if a.key in keys:
            raise CapabilityError(f"capability {name!r}: duplicate artifact key {a.key!r}")
        keys.add(a.key)

    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        if name in _REGISTRY:
            raise CapabilityError(
                f"capability {name!r} is already registered by "
                f"{_REGISTRY[name].func!r}")
        _REGISTRY[name] = Capability(
            name=name,
            summary=summary.strip(),
            params=tuple(params),
            outputs=tuple(outputs),
            resources=resources or Resources(),
            image=image,
            when=" ".join(when.split()),
            guarantee=" ".join(guarantee.split()),
            func=func,
        )
        func.__plantseed_capability__ = name  # type: ignore[attr-defined]
        return func

    return decorate


_LOADED = False


def _load_entry_points(force: bool = False) -> None:
    """Import modules advertising the `plantseed.capabilities` entry point.

    Lets the delivery repo — or a third party — add a capability without
    editing this package. Failures are deliberately swallowed: a broken
    third-party plugin must not make `plantseed capabilities` unusable.

    Registration happens as an import side effect, and imports do not repeat:
    once a plugin module is in sys.modules, `ep.load()` hands back the cached
    module without re-running the decorator. So after `clear()` the
    registrations would be gone for good unless we reload deliberately. Hence
    `force`, which `clear()` uses to make itself reversible.
    """
    global _LOADED
    if _LOADED and not force:
        return
    try:
        from importlib.metadata import entry_points
    except ImportError:  # pragma: no cover
        return
    try:
        eps = entry_points(group="plantseed.capabilities")
    except TypeError:  # pragma: no cover - Python <3.10 signature
        eps = entry_points().get("plantseed.capabilities", [])  # type: ignore[attr-defined]
    import importlib
    import sys as _sys

    for ep in eps:
        try:
            module_name = ep.value.split(":")[0]
            if force and module_name in _sys.modules:
                importlib.reload(_sys.modules[module_name])
            else:
                ep.load()
        except Exception:  # pragma: no cover - defensive
            continue
    _LOADED = True


def reload_entry_points() -> None:
    """Re-import every plugin module, re-running its registrations.

    Needed after `clear()`, because registration is an import side effect and
    imports do not repeat.
    """
    _load_entry_points(force=True)


def get(name: str) -> Capability:
    if name not in _REGISTRY:
        _load_entry_points()
    if name not in _REGISTRY:
        raise CapabilityError(
            f"unknown capability {name!r}; known: {', '.join(sorted(_REGISTRY)) or '<none>'}")
    return _REGISTRY[name]


def names() -> list[str]:
    _load_entry_points()
    return sorted(_REGISTRY)


def all_capabilities() -> list[Capability]:
    return [_REGISTRY[n] for n in names()]


def export_manifest() -> dict:
    """The whole registry, JSON-serialisable.

    This is what `plantseed capabilities --json` prints, what the per-platform
    generators read, and what koros ingests. Keep it stable: it is a contract.
    """
    from .__about__ import DATA_VERSION, __version__

    return {
        "schema_version": 1,
        "plantseed_version": __version__,
        "data_version": DATA_VERSION,
        # A pointer, not the prose. The consuming harness injects the owner's
        # own agent-facing document; duplicating it into every manifest would
        # give it two places to rot.
        "self_description": {"source": SELF_DESCRIPTION},
        "capabilities": [c.to_dict() for c in all_capabilities()],
    }


def clear() -> None:
    """Empty the registry. Tests only.

    Reversible: call `reload_entry_points()` to bring plugin-registered
    capabilities back. Without that they would be gone for the life of the
    process, since registration is an import side effect.
    """
    global _LOADED
    _REGISTRY.clear()
    _LOADED = False
