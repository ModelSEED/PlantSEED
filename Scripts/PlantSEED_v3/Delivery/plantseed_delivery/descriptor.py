"""Keeping the agent-facing documents honest.

`when` and `guarantee` are declared on the capability, beside the code, because
every harness that renders them requires the owner to author them. But they
also have to appear in prose a human reads — `for-agents.md`, and a Claude Code
`SKILL.md` for interactive sessions — and three copies of the same sentence
diverge the first time one is edited.

So the prose files carry a *generated* region, delimited by the markers below,
and `check()` fails if it no longer matches the declaration. Edit the
capability, run `python -m plantseed_delivery.descriptor --write`, commit both.
Everything outside the markers is hand-written and untouched.

The declaration is the source; these documents are projections of it. That
direction matters: a harness reads `capabilities --json`, not the markdown.
"""

from __future__ import annotations

import os
import sys

from plantseed_core import registry

__all__ = ["MARK_START", "MARK_END", "contract_block", "check", "update",
           "documents", "main"]

MARK_START = "<!-- generated from the capability declarations: do not edit -->"
MARK_END = "<!-- end generated -->"

_REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))


def documents() -> list[str]:
    """Every file carrying a generated region. Absolute paths."""
    return [
        os.path.join(_REPO_ROOT, registry.SELF_DESCRIPTION),
        os.path.join(_REPO_ROOT, ".claude", "skills", "plantseed", "SKILL.md"),
    ]


def contract_block() -> str:
    """The declaration, rendered as markdown."""
    lines = [MARK_START, ""]
    for cap in registry.all_capabilities():
        lines.append(f"### `{cap.name}`")
        lines.append("")
        lines.append(cap.summary)
        lines.append("")
        if cap.when:
            lines.append(f"**Reach for it when:** {cap.when}")
            lines.append("")
        if cap.guarantee:
            lines.append(f"**What it preserves that hand-rolling loses:** "
                         f"{cap.guarantee}")
            lines.append("")
        params = ", ".join(
            f"`{p.name}`" + ("" if p.required else " (optional)")
            for p in cap.params) or "none"
        lines.append(f"**Parameters:** {params}")
        lines.append("")
    lines.append(MARK_END)
    return "\n".join(lines)


def _split(text: str, path: str) -> tuple[str, str]:
    """(before, after) around the generated region."""
    start = text.find(MARK_START)
    end = text.find(MARK_END)
    if start < 0 or end < 0 or end < start:
        raise ValueError(
            f"{path} has no generated region — expected {MARK_START!r} … "
            f"{MARK_END!r}")
    return text[:start], text[end + len(MARK_END):]


def check(path: str) -> str | None:
    """None if `path`'s generated region is current, else why it is not."""
    if not os.path.isfile(path):
        return f"{path} does not exist"
    text = open(path).read()
    try:
        before, after = _split(text, path)
    except ValueError as exc:
        return str(exc)
    if before + contract_block() + after != text:
        return (f"{path} is stale — the capability declarations have changed. "
                "Run `python -m plantseed_delivery.descriptor --write`.")
    return None


def update(path: str) -> bool:
    """Rewrite `path`'s generated region. True if the file changed."""
    text = open(path).read()
    before, after = _split(text, path)
    new = before + contract_block() + after
    if new == text:
        return False
    open(path, "w").write(new)
    return True


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Check or refresh the generated regions of the "
                    "agent-facing documents.")
    ap.add_argument("--write", action="store_true",
                    help="Rewrite the regions instead of just checking them.")
    args = ap.parse_args(argv)

    rc = 0
    for path in documents():
        rel = os.path.relpath(path, _REPO_ROOT)
        if args.write:
            print(f"{'updated' if update(path) else 'unchanged'}  {rel}")
        else:
            problem = check(path)
            print(f"{'STALE  ' if problem else 'current'}  {rel}")
            if problem:
                rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
