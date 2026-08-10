"""The function-string contract, and the guards that keep it intact.

PlantSEED's annotator and reconstructor communicate through a single string per
feature:

    role1 / role2 # cytosol # plastid

Roles are joined by ROLE_SEP; compartment names are appended, each preceded by
COMPARTMENT_SEP. `plantseed_annotation.algorithms.propagate` composes it and
`plantseed_model.reconstruct` splits it back apart on "#". Because it is a
delimited string rather than a structure, the delimiters are reserved
characters and any role text containing one silently corrupts the round trip.

Three delimiters matter, and one of them is not ours:

  " / "  ROLE_SEP           — ours
  " # "  COMPARTMENT_SEP    — ours
  "; "   KBASE_FUNCTION_SEP — KBase's

The third is the dangerous one. GenomeFileUtil's GenomeInterface.py migrates a
legacy singular `function` field to the plural `functions` list by splitting on
the literal "; ":

    if 'function' in feat and not isinstance(feat, list):
        feat['functions'] = feat['function'].split('; ')

That branch only fires for the singular key, and everything PlantSEED writes
uses the plural list form, so it does not fire today. It is a loaded gun, not a
fired one: it goes off the moment any path — a legacy import, an external tool,
a re-normalisation pass — routes one of our role strings through the singular
field. Exactly one of the 935 roles in PlantSEED_Roles.json contains "; "
(PS_role_41ed72, the mitochondrial NAD transporter, where it sits inside a
parenthetical before a TC number). Splitting it yields two fragments, one with
an unbalanced paren, neither of which matches any template role — so the
reaction associations would vanish silently rather than error.

Hence assert_kbase_safe(): call it at composition time and again at the KBase
write boundary. Guarding costs nothing; the failure it prevents is invisible.
"""

from __future__ import annotations

import re
import sys
from typing import Iterable, Mapping, Sequence

from .errors import ReservedDelimiterError

ROLE_SEP = " / "
COMPARTMENT_SEP = " # "

#: Substrings that must never appear inside a role name. Each maps to a short
#: reason, used in the error message so a curator sees *why* it is refused.
RESERVED_SUBSTRINGS: Mapping[str, str] = {
    "; ": "KBase GenomeInterface splits legacy function strings on this",
    " / ": "PlantSEED role separator",
    " # ": "PlantSEED compartment separator",
}

KBASE_FUNCTION_SEP = "; "

__all__ = [
    "ROLE_SEP",
    "COMPARTMENT_SEP",
    "KBASE_FUNCTION_SEP",
    "RESERVED_SUBSTRINGS",
    "assert_kbase_safe",
    "find_reserved",
    "compose_function_string",
    "parse_function_string",
]


def find_reserved(text: str) -> list[tuple[str, str]]:
    """Return every (delimiter, reason) pair present in `text`. Empty if clean.

    Non-raising, so callers that want to audit a whole roles file and report all
    offenders at once can do so without try/except per role.
    """
    return [(d, why) for d, why in RESERVED_SUBSTRINGS.items() if d in text]


def assert_kbase_safe(text: str, *, context: str = "role") -> str:
    """Return `text` unchanged, or raise ReservedDelimiterError if it contains a
    reserved delimiter.

    `context` is echoed in the message — pass a role id where you have one, so
    the error points at the curation record rather than just the string.
    """
    hits = find_reserved(text)
    if hits:
        detail = "; ".join(f"{d!r} ({why})" for d, why in hits)
        raise ReservedDelimiterError(
            f"{context} contains reserved delimiter(s): {detail} — in {text!r}"
        )
    return text


def compose_function_string(
    roles: Sequence[str],
    compartments: Iterable[str] = (),
    *,
    mapping: Mapping[str, str] | None = None,
    on_unknown: str = "warn",
    check: bool = True,
) -> str:
    """Build `role1 / role2 # cpt1 # cpt2`.

    `roles` are used in the order given — callers sort beforehand if they want
    determinism, matching what propagate.py does today.

    `compartments` are compartment *names* unless `mapping` is supplied, in
    which case they are keys to look up (the single-letter localization keys
    from PlantSEED_Roles.json, e.g. "d" -> "plastid").

    `on_unknown` controls unmapped keys: "warn" (default) prints to stderr and
    drops, matching current behaviour; "drop" is silent; "raise" fails loudly.
    Prefer "raise" in new code — silently dropping a compartment changes the
    model rather than the message.

    `check` runs assert_kbase_safe on each role. Leave it on.
    """
    if check:
        for r in roles:
            assert_kbase_safe(r)

    role_str = ROLE_SEP.join(roles)

    names: list[str] = []
    for cpt in compartments:
        if mapping is None:
            names.append(cpt)
            continue
        if cpt not in mapping:
            if on_unknown == "raise":
                raise KeyError(f"no compartment mapping for {cpt!r}")
            if on_unknown == "warn":
                print(f"WARNING: no compartment mapping for {cpt!r}", file=sys.stderr)
            continue
        names.append(mapping[cpt])

    if not names:
        return role_str
    return role_str + COMPARTMENT_SEP + COMPARTMENT_SEP.join(names)


def parse_function_string(text: str) -> tuple[list[str], list[str]]:
    """Inverse of compose_function_string: `(roles, compartment_names)`.

    Deliberately mirrors plantseed_model.reconstruct rather than being stricter
    than it: split on a bare "#" (not " # "), strip each field, then split the
    role head on ``\\s+/\\s+``. Both are whitespace-tolerant, so a hand-edited
    genome with irregular spacing parses the same way the reconstructor will
    parse it. Note this means a bare "/" inside a role name survives — only a
    slash flanked by whitespace separates roles, which is why " / " rather than
    "/" is the reserved delimiter.

    A string with no "#" yields an empty compartment list.
    """
    head, _, tail = text.partition("#")
    roles = [r for r in (s.strip() for s in re.split(r"\s+/\s+", head.strip())) if r]
    compartments = [c.strip() for c in tail.split("#") if c.strip()] if tail else []
    return roles, compartments
