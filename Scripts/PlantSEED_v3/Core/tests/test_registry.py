"""Tests for the capability registry.

The manifest this produces is a contract: five generators read it (KBase
spec.json, modelseed-api Pydantic models, CTS submit bodies, the koros
capability injection, and the CLI). Most of these tests exist to pin
properties those consumers depend on rather than to exercise Python.
"""

import json

import pytest

from plantseed_core import registry
from plantseed_core.errors import CapabilityError
from plantseed_core.registry import Artifact, FileParam, Param, Resources


@pytest.fixture
def clean_registry():
    """Isolate the global registry, then restore what was there.

    Restoring matters and is not trivial: the real `reconstruct` capability is
    registered as an import side effect of an entry-point module, and imports
    do not repeat. Force the load before snapshotting so the snapshot is
    complete, and restore by assignment rather than by re-importing.
    """
    registry.reload_entry_points()
    saved = dict(registry._REGISTRY)
    registry.clear()
    yield registry
    registry._REGISTRY.clear()
    registry._REGISTRY.update(saved)
    registry._LOADED = True


def _register(clean_registry, **kw):
    kw.setdefault("name", "thing")
    kw.setdefault("summary", "does a thing")

    @registry.capability(**kw)
    def _impl(**_):
        return None

    return registry.get(kw["name"])


class TestNames:
    @pytest.mark.parametrize("bad", ["Thing", "a-b", "1abc", "a b", "", "a.b", "_x"])
    def test_invalid_capability_names_rejected(self, clean_registry, bad):
        with pytest.raises(CapabilityError):
            _register(clean_registry, name=bad)

    @pytest.mark.parametrize("good", ["annotate", "reconstruct", "integrate_omics", "a1"])
    def test_valid_names_accepted(self, clean_registry, good):
        assert _register(clean_registry, name=good).name == good

    def test_parameter_names_held_to_the_same_rule(self, clean_registry):
        # they become CTS argv tokens and KBase spec ids, not just kwargs
        with pytest.raises(CapabilityError):
            _register(clean_registry, params=[Param("Bad-Name")])

    def test_duplicate_registration_is_an_error(self, clean_registry):
        _register(clean_registry, name="dup")
        with pytest.raises(CapabilityError, match="already registered"):
            _register(clean_registry, name="dup")


class TestSummary:
    def test_summary_is_required(self, clean_registry):
        with pytest.raises(CapabilityError, match="summary"):
            _register(clean_registry, summary="")

    def test_whitespace_only_summary_rejected(self, clean_registry):
        with pytest.raises(CapabilityError):
            _register(clean_registry, summary="   ")

    def test_summary_is_stripped(self, clean_registry):
        assert _register(clean_registry, summary="  hi  ").summary == "hi"


class TestParams:
    def test_unknown_type_rejected(self, clean_registry):
        with pytest.raises(CapabilityError, match="type"):
            _register(clean_registry, params=[Param("x", type="complex")])

    def test_enum_requires_choices(self, clean_registry):
        with pytest.raises(CapabilityError, match="choices"):
            _register(clean_registry, params=[Param("x", type="enum")])

    def test_default_must_be_one_of_the_choices(self, clean_registry):
        with pytest.raises(CapabilityError, match="default"):
            _register(clean_registry,
                      params=[Param("x", type="enum", choices=("a", "b"), default="c")])

    def test_required_param_cannot_have_a_default(self, clean_registry):
        with pytest.raises(CapabilityError, match="default"):
            _register(clean_registry, params=[Param("x", required=True, default="v")])

    def test_duplicate_parameter_rejected(self, clean_registry):
        with pytest.raises(CapabilityError, match="duplicate parameter"):
            _register(clean_registry, params=[Param("x"), FileParam("x")])

    def test_file_params_are_identifiable(self, clean_registry):
        cap = _register(clean_registry, params=[Param("a"), FileParam("b"), FileParam("c")])
        assert [p.name for p in cap.file_params] == ["b", "c"]

    def test_param_lookup_by_name(self, clean_registry):
        cap = _register(clean_registry, params=[Param("a")])
        assert cap.param("a").name == "a"
        with pytest.raises(KeyError):
            cap.param("nope")


class TestArtifacts:
    def test_nested_output_paths_rejected(self, clean_registry):
        """CTS collects results with `find <mount> -type f` and strips the mount
        prefix; nesting buys nothing and costs portability."""
        with pytest.raises(CapabilityError, match="flat"):
            _register(clean_registry, outputs=[Artifact("k", "sub/dir/out.json")])

    def test_duplicate_artifact_key_rejected(self, clean_registry):
        with pytest.raises(CapabilityError, match="duplicate artifact"):
            _register(clean_registry,
                      outputs=[Artifact("k", "a.json"), Artifact("k", "b.json")])


class TestResources:
    @pytest.mark.parametrize("kw", [{"cpus": 0}, {"memory_gb": 0}, {"runtime_h": 0}])
    def test_nonsense_resources_rejected(self, kw):
        with pytest.raises(CapabilityError):
            Resources(**kw)

    def test_cpu_hours_is_what_cts_bills(self):
        """CTS bills cpus x containers x runtime against a default 100 cap."""
        assert Resources(cpus=8, runtime_h=12).cpu_hours == 96


class TestManifest:
    def test_manifest_is_json_serialisable(self, clean_registry):
        _register(clean_registry, params=[Param("x", type="enum", choices=("a",))],
                  outputs=[Artifact("o", "o.json")])
        json.dumps(registry.export_manifest())  # must not raise

    def test_manifest_carries_versions(self, clean_registry):
        m = registry.export_manifest()
        assert m["schema_version"] == 1
        assert m["plantseed_version"] and m["data_version"]

    def test_implementation_is_not_in_the_wire_form(self, clean_registry):
        """A generator must be able to build a spec without importing the code."""
        cap = _register(clean_registry)
        assert cap.func is not None
        assert "func" not in cap.to_dict()

    def test_capabilities_are_sorted(self, clean_registry):
        for n in ("zeta", "alpha", "mid"):
            _register(clean_registry, name=n)
        got = [c["name"] for c in registry.export_manifest()["capabilities"]]
        assert got == sorted(got)

    def test_unknown_capability_lists_the_known_ones(self, clean_registry):
        _register(clean_registry, name="known")
        with pytest.raises(CapabilityError, match="known"):
            registry.get("nope")


class TestTheRealReconstructCapability:
    """The declaration must keep matching reconstruct_cli's actual interface."""

    def test_it_is_registered_via_entry_point(self):
        assert "reconstruct" in registry.names()

    def test_required_input_is_the_annotated_genome(self):
        cap = registry.get("reconstruct")
        required = [p.name for p in cap.params if p.required]
        assert required == ["genome"]

    def test_declares_the_outputs_the_cli_writes(self):
        keys = {a.key for a in registry.get("reconstruct").outputs}
        assert {"model", "provenance"} <= keys

    def test_outputs_are_flat(self):
        assert all("/" not in a.filename for a in registry.get("reconstruct").outputs)

    def test_needs_no_refdata(self):
        """Template and compartments ship in the wheel, so this capability can
        run on CTS without an admin-registered refdata bundle."""
        assert registry.get("reconstruct").resources.refdata is None

    def test_fits_well_inside_the_cts_cpu_hour_cap(self):
        assert registry.get("reconstruct").resources.cpu_hours <= 100

    def test_parameter_names_match_the_cli_flags(self):
        """reconstruct_cli exposes --genome/--template/--compartments/--model-id.
        argparse maps a hyphen to an underscore, so the declaration uses the
        underscored form; anything else means the two have drifted."""
        got = {p.name for p in registry.get("reconstruct").params}
        assert got == {"genome", "template", "compartments", "model_id"}


class TestClearIsReversible:
    """clear() must not permanently destroy entry-point registrations.

    Registration is an import side effect, and `ep.load()` on an
    already-imported module returns the cached module without re-running it —
    so a naive clear() empties the registry for the life of the process. This
    pins the fix.
    """

    def test_reload_restores_plugin_capabilities_after_clear(self):
        assert "reconstruct" in registry.names()
        saved = dict(registry._REGISTRY)
        try:
            registry.clear()
            assert registry._REGISTRY == {}
            registry.reload_entry_points()
            assert "reconstruct" in registry.names()
        finally:
            registry._REGISTRY.clear()
            registry._REGISTRY.update(saved)
            registry._LOADED = True


class TestInputSchema:
    """`input_schema()` is what MCP tool signatures and KING's explorer form
    are built from. The mapping exists once here; a consumer re-deriving it
    would be a second source of truth for the same declaration."""

    def test_scalars_map_to_json_types(self, clean_registry):
        cap = _register(clean_registry, params=[
            Param("s", type="str"), Param("i", type="int"),
            Param("f", type="float"), Param("b", type="bool"),
        ])
        props = cap.input_schema()["properties"]
        assert [props[k]["type"] for k in ("s", "i", "f", "b")] == [
            "string", "integer", "number", "boolean"]

    def test_every_param_type_is_covered(self, clean_registry):
        """A new PARAM_TYPES entry must not silently emit a broken schema."""
        for t in registry.PARAM_TYPES:
            if t == "file":
                p = FileParam("x")
            elif t == "enum":
                p = Param("x", type="enum", choices=("a", "b"))
            else:
                p = Param("x", type=t)
            schema = _register(clean_registry, name=f"c_{t}",
                               params=[p]).input_schema()["properties"]["x"]
            assert "type" in schema or "enum" in schema, t

    def test_enum_emits_choices_and_no_type(self, clean_registry):
        """Choices need not be strings, so pinning a `type` would be wrong."""
        cap = _register(clean_registry, params=[
            Param("mode", type="enum", choices=("fast", "thorough"))])
        assert cap.input_schema()["properties"]["mode"] == {
            "enum": ["fast", "thorough"]}

    def test_files_are_strings_and_multiple_is_an_array(self, clean_registry):
        cap = _register(clean_registry, params=[
            FileParam("one"), FileParam("many", multiple=True)])
        props = cap.input_schema()["properties"]
        assert props["one"]["type"] == "string"
        assert props["many"] == {"type": "array", "items": {"type": "string"}}

    def test_required_lists_only_required_params(self, clean_registry):
        cap = _register(clean_registry, params=[
            FileParam("needed", required=True), Param("opt", default="x")])
        assert cap.input_schema()["required"] == ["needed"]

    def test_required_is_absent_when_nothing_is(self, clean_registry):
        """An empty `required: []` is legal JSON Schema but noisy; omit it."""
        assert "required" not in _register(clean_registry).input_schema()

    def test_help_and_fmt_become_the_description(self, clean_registry):
        cap = _register(clean_registry, params=[
            FileParam("genome", fmt="plantseed_annotated_genome_json",
                      help="The genome.")])
        desc = cap.input_schema()["properties"]["genome"]["description"]
        assert "The genome." in desc and "plantseed_annotated_genome_json" in desc

    def test_defaults_pass_through(self, clean_registry):
        cap = _register(clean_registry, params=[Param("n", type="int", default=4)])
        assert cap.input_schema()["properties"]["n"]["default"] == 4

    def test_unknown_parameters_are_rejected(self, clean_registry):
        """A mistyped parameter name should fail the call, not be ignored."""
        assert _register(clean_registry).input_schema()["additionalProperties"] is False

    def test_the_wire_form_carries_it(self, clean_registry):
        """So a consumer gets the schema without reimplementing the mapping."""
        cap = _register(clean_registry, params=[FileParam("g", required=True)])
        assert cap.to_dict()["input_schema"] == cap.input_schema()

    def test_the_real_reconstruct_schema_is_usable(self):
        """Against the shipped declaration, not a fixture."""
        schema = registry.get("reconstruct").input_schema()
        assert schema["required"] == ["genome"]
        assert set(schema["properties"]) == {
            "genome", "template", "compartments", "model_id"}

    def test_it_validates_as_json_schema(self):
        """Skipped unless jsonschema is installed — it is not a dependency."""
        js = pytest.importorskip("jsonschema")
        schema = registry.get("reconstruct").input_schema()
        js.Draft202012Validator.check_schema(schema)
        js.validate({"genome": "g.json"}, schema)
        with pytest.raises(js.ValidationError):
            js.validate({"genome": "g.json", "typo": 1}, schema)
        with pytest.raises(js.ValidationError):
            js.validate({}, schema)
