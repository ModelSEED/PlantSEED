#!/usr/bin/env python3
"""Audit mass/charge balance of every reaction in a generated PlantSEED template.

Complementary to Generate_Core_ModelTemplate.py, which gates reactions on the
*deposited* ModelSEED status string -- a static field that is computed before
any PlantSEED curator modification is applied, and is never recomputed after.
This script closes that gap: it recomputes balance from the template itself,
which is the post-modification ground truth.

The balance engine is ModelSEEDDatabase's own BiochemPy.Reactions.balanceReaction,
so verdicts are directly comparable to the former status strings. BiochemPy is
fetched over HTTPS at the same commit the template was generated from and cached
locally; no checkout of ModelSEEDDatabase is required. Pass --biochempy to use a
local checkout instead (offline, or when testing uncommitted library changes).

Only the two library source files are fetched. Formulas and charges come from the
template, not from the database, so the audit reflects exactly what was built.

Verdicts:
  BOUND  a boundary reaction -- a drain or sink with a single reagent. Unbalanced
         by construction, the same way an exchange reaction is; excluded from the
         audit rather than reported as a defect.
  ERROR  imbalance on a curator-modified reaction -- the modification claims to
         balance the reaction and does not
  WARN   imbalance on a reaction that was never exempted -- it entered the template
         because the former status did not report the imbalance
  KNOWN  imbalance on a reaction exempted in Unbalanced_Reactions_to_Fix.txt --
         deliberately admitted, still outstanding upstream
  GATED  reaction balances only because of a curator modification, but its former
         status is still dirty, so the exemption is load-bearing: removing it would
         re-exclude the reaction. These are the cases that would be retired by having
         the generator trust curator stoichiometry overrides instead.
  STALE  reaction is exempted, balances, and its former status is clean too --
         the exemption does nothing, drop it
  NOTE   charge-only imbalance, which PlantSEED tolerates

Where the generator's Biochem_Cache/MS_Rxns.pickle is present, the deposited
ModelSEED status is shown alongside and marked [stale] when it reports the
reaction as mass-clean but the recomputed status disagrees. That combination is why an
imbalanced reaction can reach the template without an exemption.

Exit status is 1 if any ERROR was found, else 0.
"""

import argparse
import importlib.util
import json
import os
import re
import sys
import types
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
GENERATOR = os.path.join(HERE, "Generate_Core_ModelTemplate.py")
EXEMPTIONS = os.path.join(HERE, "Unbalanced_Reactions_to_Fix.txt")
COMPLEXES = os.path.normpath(
    os.path.join(HERE, "..", "..", "..", "Data", "PlantSEED_v3", "PlantSEED_Complexes.json"))
RAW = "https://raw.githubusercontent.com/ModelSEED/ModelSEEDDatabase/{sha}/Libs/Python/BiochemPy/{mod}.py"


def pinned_commit():
    """Read MSD_PINNED_COMMIT from the generator so the two cannot drift apart."""
    with open(GENERATOR) as fh:
        m = re.search(r'^MSD_PINNED_COMMIT\s*=\s*["\']([0-9a-f]{7,40})["\']', fh.read(), re.M)
    if not m:
        sys.exit("ERROR: could not find MSD_PINNED_COMMIT in %s" % GENERATOR)
    return m.group(1)


def load_biochempy(sha, local=None, cache_root=None):
    """Return (Compounds, Reactions) classes, from a local checkout or fetched by commit."""
    sources = {}
    if local:
        for mod in ("Compounds", "Reactions"):
            path = os.path.join(local, "BiochemPy", "%s.py" % mod)
            if not os.path.isfile(path):
                path = os.path.join(local, "%s.py" % mod)
            with open(path) as fh:
                sources[mod] = fh.read()
        origin = local
    else:
        cache = os.path.join(cache_root or os.path.join(HERE, "Biochem_Cache"),
                             "BiochemPy_%s" % sha[:10])
        os.makedirs(cache, exist_ok=True)
        for mod in ("Compounds", "Reactions"):
            path = os.path.join(cache, "%s.py" % mod)
            if not os.path.isfile(path):
                url = RAW.format(sha=sha, mod=mod)
                with urllib.request.urlopen(url) as resp:
                    text = resp.read().decode()
                with open(path, "w") as fh:
                    fh.write(text)
            with open(path) as fh:
                sources[mod] = fh.read()
        origin = cache

    # Synthesise the package so Reactions.py's `from BiochemPy import Compounds` resolves.
    pkg = types.ModuleType("BiochemPy")
    pkg.__path__ = []
    sys.modules["BiochemPy"] = pkg
    out = {}
    for mod in ("Compounds", "Reactions"):
        spec = importlib.util.spec_from_loader("BiochemPy.%s" % mod, loader=None)
        m = importlib.util.module_from_spec(spec)
        m.__dict__["__file__"] = os.path.join(origin, "%s.py" % mod)
        sys.modules["BiochemPy.%s" % mod] = m
        exec(compile(sources[mod], "BiochemPy/%s.py" % mod, "exec"), m.__dict__)
        out[mod] = getattr(m, mod)
        setattr(pkg, mod, out[mod])
    return out["Compounds"], out["Reactions"], origin


def modified_reactions():
    """Map base reaction id -> list of (enzyme, scope) for curator stoichiometry overrides.

    An enzyme-wide `stoichiometry` block applies to every reaction the complex
    catalyses, in every compartment. A `reaction_stoichiometry` block applies only
    to the reactions it names.
    """
    if not os.path.isfile(COMPLEXES):
        return {}
    with open(COMPLEXES) as fh:
        complexes = json.load(fh)
    mods = {}
    for entry in complexes:
        enzyme = entry.get("enzyme") or entry.get("abstract_enzyme") or "?"
        if entry.get("stoichiometry"):
            for block in entry.get("compartments_reactions", {}).values():
                for rxn in block.get("reactions", []):
                    mods.setdefault(rxn, []).append((enzyme, "enzyme-wide"))
        for rxn in (entry.get("reaction_stoichiometry") or {}):
            mods.setdefault(rxn, []).append((enzyme, "reaction-scoped"))
    return mods


def former_status():
    """Former (stored) MSD status per reaction, from the generator's cache if it exists.

    Only reactions are read. The companion MS_Cpds.pickle is NOT usable for balance
    work: the generator rewrites compounds, coercing null formula to 'R' and null
    charge to 0.0, which silently changes the arithmetic.
    """
    path = os.path.join(HERE, "Biochem_Cache", "MS_Rxns.pickle")
    if not os.path.isfile(path):
        return {}
    import pickle
    with open(path, "rb") as fh:
        return {k: (v.get("status") or "") for k, v in pickle.load(fh).items()}


def exempted():
    if not os.path.isfile(EXEMPTIONS):
        return set()
    with open(EXEMPTIONS) as fh:
        return {ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")}


def build_reagents(rxn, compcompounds, compounds, charge_source):
    """Assemble a BiochemPy rgts_array from a template reaction."""
    rgts = []
    for reagent in rxn.get("templateReactionReagents", []):
        ccid = reagent["templatecompcompound_ref"].split("/")[-1]
        cc = compcompounds.get(ccid)
        if cc is None:
            return None, "unresolved compcompound %s" % ccid
        cpd_id = cc["templatecompound_ref"].split("/")[-1]
        cpt = cc["templatecompartment_ref"].split("/")[-1]
        cpd = compounds.get(cpd_id)
        if cpd is None:
            return None, "unresolved compound %s" % cpd_id
        charge = cc.get("charge") if charge_source == "compcompound" else cpd.get("defaultCharge")
        rgts.append({"compound": cpd_id,
                     "compartment": cpt,
                     "coefficient": float(reagent["coefficient"]),
                     "formula": cpd.get("formula") or "",
                     "charge": float(charge or 0.0)})
    return rgts, None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", default=os.path.join(HERE, "PlantSEED_Biomass_Template.json"),
                    help="template JSON to audit (default: PlantSEED_Biomass_Template.json)")
    ap.add_argument("--biochempy", metavar="DIR",
                    help="local Libs/Python directory to import BiochemPy from, instead of fetching")
    ap.add_argument("--commit", help="override MSD commit (default: MSD_PINNED_COMMIT from the generator)")
    ap.add_argument("--charge-source", choices=("compound", "compcompound"), default="compound",
                    help="which charge the audit uses (default: compound -- the single "
                         "authoritative value; compcompound is retained for comparison)")
    ap.add_argument("--all", action="store_true", help="also list reactions that balance cleanly")
    ap.add_argument("--json", dest="as_json", metavar="FILE", help="write the full result set as JSON")
    args = ap.parse_args()

    sha = args.commit or pinned_commit()
    Compounds, Reactions, origin = load_biochempy(sha, args.biochempy)
    # balanceReaction only reaches self.CompoundsHelper.parseFormula, a @staticmethod,
    # so the expensive constructor (which needs a full checkout) is bypassed entirely.
    shim = types.SimpleNamespace(CompoundsHelper=Compounds)

    with open(args.template) as fh:
        tmpl = json.load(fh)
    compounds = {c["id"]: c for c in tmpl["compounds"]}
    compcompounds = {c["id"]: c for c in tmpl["compcompounds"]}
    mods, exempt, former = modified_reactions(), exempted(), former_status()

    divergent = sum(1 for cc in tmpl["compcompounds"]
                    if float(cc.get("charge") or 0) != float(
                        compounds[cc["templatecompound_ref"].split("/")[-1]].get("defaultCharge") or 0))

    print("Template   : %s (%d reactions, %d compounds)"
          % (os.path.basename(args.template), len(tmpl["reactions"]), len(tmpl["compounds"])))
    print("BiochemPy  : %s" % origin)
    print("MSD commit : %s" % sha)
    print("Charges    : %s (%d of %d compcompounds diverge from compound defaultCharge)"
          % (args.charge_source, divergent, len(tmpl["compcompounds"])))
    print("Modified   : %d reactions carry curator stoichiometry overrides" % len(mods))
    print("Exempted   : %d reactions in %s" % (len(exempt), os.path.basename(EXEMPTIONS)))
    print("Former sts : %s" % ("%d statuses available for cross-check" % len(former)
                               if former else "unavailable (no Biochem_Cache/MS_Rxns.pickle)"))
    print()

    buckets = {"ERROR": [], "WARN": [], "KNOWN": [], "GATED": [], "STALE": [], "NOTE": [], "BOUND": [], "OK": []}
    results = []
    for rxn in tmpl["reactions"]:
        tmpl_id = rxn["id"]
        base = tmpl_id.rsplit("_", 1)[0]
        rgts, err = build_reagents(rxn, compcompounds, compounds, args.charge_source)
        status = "UNRESOLVED:%s" % err if rgts is None else Reactions.balanceReaction(shim, rgts)

        # a single-reagent reaction is a boundary (drain/sink/exchange), not metabolism
        is_boundary = len(rxn.get("templateReactionReagents", [])) == 1
        is_mod, is_exempt = base in mods, base in exempt
        mass_bad = status.startswith(("MI:", "CPDFORMERROR", "Duplicate", "EMPTY", "UNRESOLVED"))
        charge_only = status.startswith("CI:")

        dep = former.get(base, "")
        dep_dirty = bool(dep) and dep.replace("|CK", "").replace("CK|", "").startswith(
            ("MI:", "CPDFORM", "Dup", "EMPTY"))

        if is_boundary:
            verdict = "BOUND"
        elif mass_bad:
            verdict = "ERROR" if is_mod else ("KNOWN" if is_exempt else "WARN")
        elif is_exempt:
            # Balances now -- but if the former status is still dirty the exemption
            # is what admits it, so it cannot simply be deleted.
            verdict = "GATED" if dep_dirty else "STALE"
        elif charge_only:
            verdict = "NOTE"
        else:
            verdict = "OK"

        dep_clean = bool(dep) and not dep_dirty
        row = {"template_reaction": tmpl_id, "reaction": base, "status": status,
               "verdict": verdict, "modified_by": mods.get(base, []), "exempted": is_exempt,
               "former": dep, "status_disagrees": bool(mass_bad and dep_clean),
               "name": rxn.get("name", "")}
        results.append(row)
        buckets[verdict].append(row)

    order = [("ERROR", "imbalanced DESPITE a curator modification -- the modification is wrong"),
             ("WARN", "imbalanced and never exempted -- entered the template unnoticed"),
             ("KNOWN", "imbalanced, deliberately exempted -- still outstanding upstream"),
             ("GATED", "balances only via a curator modification -- exemption still required"),
             ("STALE", "exemption does nothing (balances, and former status is clean too)"),
             ("NOTE", "charge-only imbalance (tolerated)"),
             ("BOUND", "boundary reaction (drain/sink) -- unbalanced by construction")]
    if args.all:
        order.append(("OK", "balanced"))

    for verdict, blurb in order:
        rows = buckets[verdict]
        if not rows:
            continue
        print("%s -- %d: %s" % (verdict, len(rows), blurb))
        for r in sorted(rows, key=lambda x: x["template_reaction"]):
            who = ""
            if r["modified_by"]:
                who = "   <- %s" % "; ".join("%s (%s)" % (e, s) for e, s in r["modified_by"])
            dep = ""
            if r["former"]:
                dep = "   former=%s%s" % (r["former"], " <-- DISAGREES" if r["status_disagrees"] else "")
            print("   %-16s %-26s %-30s%s%s"
                  % (r["template_reaction"], r["status"], r["name"][:30], dep, who))
        print()

    stale_n = sum(1 for r in results if r["status_disagrees"])
    print("Summary: " + "  ".join("%s=%d" % (k, len(buckets[k]))
                                  for k in ("ERROR", "WARN", "KNOWN", "GATED", "STALE", "NOTE", "BOUND", "OK")))
    if stale_n:
        print("         %d reaction(s) are mass-imbalanced while their former "
              "status reports them clean." % stale_n)

    if args.as_json:
        with open(args.as_json, "w") as fh:
            json.dump(results, fh, indent=2)
        print("Wrote %s" % args.as_json)

    return 1 if buckets["ERROR"] else 0


if __name__ == "__main__":
    sys.exit(main())
