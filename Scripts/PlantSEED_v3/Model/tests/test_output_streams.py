"""stdout belongs to the caller; progress goes to stderr.

Every delivery surface parses this process's stdout. koros ingests
`plantseed capabilities --json` into the agent's orientation prompt, the
modelseed-api job scripts read a JSON job record, and a CTS container's stdout
is captured as a log artifact. A stray print() corrupts all three, silently and
only in production.

The engine used to print progress to stdout and ignore --quiet entirely, so
these are regression tests for a fixed bug, not aspirations.
"""

import io
import json
import os

import pytest

from plantseed_model import ReconstructAppImpl

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, "..", "..", "..", ".."))
_PAPER = os.path.join(_REPO, "Papers", "bioflux-preprint-260807")
_TEMPLATE = os.path.join(_REPO, "Scripts", "PlantSEED_v3", "Template",
                         "PlantSEED_Biomass_Template.json")
_COMPARTMENTS = os.path.join(_REPO, "Data", "PlantSEED_v3", "Compartments",
                             "PlantSEED_Compartments.json")

pytestmark = pytest.mark.skipif(
    not (os.path.isdir(_PAPER) and os.path.isfile(_TEMPLATE)
         and os.path.isfile(_COMPARTMENTS)),
    reason="preprint artifacts / template not present (installed wheel)",
)


def _load(path):
    with open(path) as fh:
        return json.load(fh)


def _run(capsys, *, quiet=False, log_stream=None):
    recon = ReconstructAppImpl()
    recon.quiet = quiet
    if log_stream is not None:
        recon.log_stream = log_stream
    recon._set_objects({
        "genome": _load(os.path.join(_PAPER, "Athaliana_TAIR10_annotated_genome.json")),
        "template": _load(_TEMPLATE),
    })
    model = recon.reconstruct_metabolism(
        {"id": "t", "name": "t", "cpts": _load(_COMPARTMENTS)})
    return model, capsys.readouterr()


def test_stdout_is_empty_during_reconstruction(capsys):
    model, captured = _run(capsys)
    assert captured.out == "", (
        "reconstruction wrote to stdout, which every platform parses:\n"
        + captured.out[:500]
    )
    assert model["modelreactions"], "sanity: the run should have produced a model"


def test_progress_still_goes_somewhere(capsys):
    """Silencing stdout must not mean losing the diagnostics."""
    _, captured = _run(capsys)
    assert "conditional" in captured.err.lower(), \
        "expected conditional-reaction progress on stderr"


def test_quiet_silences_both_streams(capsys):
    _, captured = _run(capsys, quiet=True)
    assert captured.out == ""
    assert captured.err == ""


def test_quiet_does_not_change_the_model(capsys):
    """Verbosity is presentation, never behaviour."""
    loud, _ = _run(capsys)
    quiet, _ = _run(capsys, quiet=True)
    assert {r["id"] for r in loud["modelreactions"]} == \
           {r["id"] for r in quiet["modelreactions"]}


def test_log_stream_is_redirectable(capsys):
    """A KBase app routing progress into a KBaseReport, or a test capturing it,
    should not have to monkeypatch sys.stderr."""
    sink = io.StringIO()
    _, captured = _run(capsys, log_stream=sink)
    assert captured.out == ""
    assert captured.err == ""
    assert "conditional" in sink.getvalue().lower()
