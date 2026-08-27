"""The agent-facing prose must not drift from the declaration.

`when` and `guarantee` are declared on the capability and rendered into two
documents a human reads. Three copies of a sentence diverge the first time one
is edited, and the failure is silent: an agent is told to reach for a tool
under conditions that no longer hold, or with a parameter that no longer
exists, and nothing errors.

The declaration is the source and the documents are projections of it, so the
check runs in that direction.
"""

import os

import pytest

from plantseed_core import registry
from plantseed_delivery import descriptor

DOCS = descriptor.documents()


def test_there_are_documents_to_check():
    """A rename that emptied this list would make everything below vacuous."""
    assert DOCS


@pytest.mark.parametrize("path", DOCS, ids=[os.path.basename(p) for p in DOCS])
def test_the_generated_region_is_current(path):
    problem = descriptor.check(path)
    assert problem is None, problem


@pytest.mark.parametrize("path", DOCS, ids=[os.path.basename(p) for p in DOCS])
def test_the_hand_written_prose_survives_a_regeneration(path, tmp_path):
    """Regenerating must touch only the marked region. If it rewrote the whole
    file, nobody would run it and the region would go stale anyway."""
    original = open(path).read()
    copy = tmp_path / os.path.basename(path)
    copy.write_text(original)
    descriptor.update(str(copy))
    assert copy.read_text() == original


class TestTheBlockItself:
    def test_it_carries_the_owners_when_verbatim(self):
        """Not a paraphrase: this is the text a harness injects as 'Reach for
        it when', and it is the owner's to write."""
        block = descriptor.contract_block()
        for cap in registry.all_capabilities():
            assert cap.when in block
            assert cap.guarantee in block

    def test_it_names_every_capability_and_parameter(self):
        block = descriptor.contract_block()
        for cap in registry.all_capabilities():
            assert f"`{cap.name}`" in block
            for p in cap.params:
                assert f"`{p.name}`" in block

    def test_optional_parameters_are_marked_as_such(self):
        block = descriptor.contract_block()
        cap = registry.get("reconstruct")
        assert "`genome`," in block                    # required: unmarked
        assert "`template` (optional)" in block


class TestStaleness:
    def test_an_edited_declaration_makes_the_documents_stale(self, tmp_path,
                                                             monkeypatch):
        """The test that gives the rest their teeth: change the declaration and
        the check must notice."""
        path = tmp_path / "doc.md"
        path.write_text("intro\n" + descriptor.contract_block() + "\noutro\n")
        assert descriptor.check(str(path)) is None

        monkeypatch.setattr(descriptor, "contract_block",
                            lambda: descriptor.MARK_START + "\nchanged\n"
                                    + descriptor.MARK_END)
        assert "stale" in descriptor.check(str(path))

    def test_a_document_without_markers_is_reported_not_ignored(self, tmp_path):
        path = tmp_path / "doc.md"
        path.write_text("no markers here\n")
        assert "no generated region" in descriptor.check(str(path))

    def test_a_missing_document_is_reported(self, tmp_path):
        assert "does not exist" in descriptor.check(str(tmp_path / "gone.md"))


class TestSkillFile:
    """The SKILL.md is for interactive Claude Code, which KIND*AI cannot use —
    its sessions omit the Skill tool. The file has to say so, or someone will
    write the load-bearing prose there and wonder why the harness ignores it."""

    @property
    def path(self):
        return [p for p in DOCS if p.endswith("SKILL.md")][0]

    def test_it_has_the_frontmatter_claude_code_requires(self):
        text = open(self.path).read()
        assert text.startswith("---\n")
        head = text.split("---", 2)[1]
        assert "name: plantseed" in head
        assert "description:" in head

    def test_the_description_says_when_to_use_and_when_not_to(self):
        head = open(self.path).read().split("---", 2)[1]
        assert "Use when" in head
        assert "Not a general genome annotator" in head

    def test_it_points_at_the_canonical_document(self):
        assert os.path.basename(registry.SELF_DESCRIPTION) in open(self.path).read()


def test_the_manifest_pointer_resolves():
    """`export_manifest()['self_description']['source']` is what a harness
    follows; a dangling path is worse than none."""
    source = registry.export_manifest()["self_description"]["source"]
    assert os.path.isfile(os.path.join(descriptor._REPO_ROOT, source)), source
