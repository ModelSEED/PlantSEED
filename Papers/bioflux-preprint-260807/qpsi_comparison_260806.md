# qpsi-260406 Sorghum reconstruction vs the new PlantSEED-v3 pipeline

Comparison of the Sorghum plastidial reconstruction currently used in the
preprint (`qpsi-260406-plastid-sorghum/inputs/Sbicolor-v3.1.1-plastidial-reconstruction.json`,
built 2026-05-15) against the new full-genome reconstruction produced by the
Aug 2026 `plantseed_annotation` pipeline (this directory).

## Headline numbers

|  | QPSI (May 2026) | New (Aug 2026) |
|---|---:|---:|
| Source ID | PlantSEED_v3 | PlantSEED_v3 |
| Model reactions | 393 | 1171 |
|   in `d0` (plastid stroma) | 370 | 446 |
|   in `c0` (cytosol) | 20 | 354 |
|   in `y0` (thylakoid) | 3 | 3 |
|   in other compartments | 0 | 368 |
| Model compounds | 440 | 1283 |
| Biomass reactions | 1 | 1 |
| GPR coverage on model reactions | 336/393 (85.5 %) | 782/1171 (66.8 %) |

The **absolute** GPR count is similar (336 vs 782 — but that counts
GPRs across the full multi-compartment reconstruction on the new
side). The interesting comparison is per-reaction GPR agreement on the
378 reactions both models contain.

## Per-reaction GPR agreement (378 shared reactions)

| Category | QPSI vs New | Interpretation |
|---|---:|---|
| Identical GPR | **296 (78.3 %)** | Same feature set — algorithm agrees. |
| QPSI ⊆ NEW (my new added features) | 22 | Paralog admission working — see below. |
| QPSI ⊇ NEW (my new dropped features) | 40 | Features present in QPSI but not in mine — see below. |
| Overlapping-but-not-subset | 20 | Some features shared, some in each direction. |
| Disjoint feature sets | 0 | No completely-different assignments. |

Compared against the older hand-vetted `sbicolor_..._250617.json`, the
same 3-way pattern holds: QPSI improved on OLD by adding ~16 reactions'
worth of features and dropping ~26; NEW improved on both by adding
another ~22 via paralog admission.

## What the "my NEW added features" case looks like (22 reactions)

These are the paralog-admission wins. Representative examples:

- `rxn25660_d0` / `rxn17803_d0`  Oleoyl-[acyl carrier protein] thioesterase (EC 3.1.2.14):
  QPSI had one feature; NEW adds `Sobic.004G088100`, `Sobic.010G033300`,
  `Sobic.010G180400` — additional Oleoyl-ACP thioesterase paralogs
  (this is a small gene family in grasses).
- `rxn00154_d0`  Pyruvate dehydrogenase complex (E1/E2/E3):
  QPSI had subunit set; NEW adds `Sobic.002G197500`, `Sobic.007G134800`.
- `rxn23780_d0` / `rxn27070–72_d0`  2-oxo-5-methylthiopentanoate transaminase
  (EC 2.6.1.-):
  All four reactions get `Sobic.006G176600` added. (This role only entered
  PlantSEED_Roles.json in the `homomethionine` curation that landed on
  dev after the QPSI model was built.)
- `rxn05345_d0` / `rxn05346_d0`  3-oxoacyl-[acyl-carrier-protein] synthase KASI
  (EC 2.3.1.41): NEW adds `Sobic.002G401301`.
- `rxn00710_c0`  Orotidine 5'-phosphate decarboxylase: NEW adds `Sobic.002G413750`.

**Pattern**: duplicated gene families where OrthoFinder's ortholog inference
alone missed paralogs. This is exactly what the Processing_v2 O+PAM
classifier was designed to recover.

## What the "my NEW dropped features" case looks like (40 reactions)

QPSI has features on reactions where NEW's annotation is empty or has a
different feature set. Investigating one representative case
(`rxn02507_d0` Indole-3-glycerol phosphate synthase, EC 4.1.1.48):

| | Athaliana curated IGPS | Sorghum in same OG | QPSI features on this rxn |
|---|---|---|---|
| PlantSEED_Roles.json (Ath) | `AT2G04400`, `AT5G48220` | — | — |
| OrthoFinder `Results_May26` | both in `OG0007601` | `Sobic.006G112600` (single ortholog) | — |
| QPSI reconstruction | — | — | `Sobic.002G160600`, `Sobic.004G143900`, `Sobic.007G086600` |

**None of QPSI's three Sorghum IGPS features are in the same OrthoFinder
orthogroup as Athaliana's curated IGPS genes.** They can't be reached by
OF-based ortholog/paralog propagation from `PlantSEED_Roles.json` on this
OrthoFinder run.

The other "dropped" reactions I sampled (Aspartate aminotransferase,
Alanine transaminase, 4-hydroxyphenylpyruvate dioxygenase,
1-deoxy-D-xylulose 5-phosphate synthase, etc.) show the same pattern.

## Where did QPSI's dropped features come from?

Almost certainly a **different annotation source** than the OF+PSI+PlantSEED
path this new pipeline uses. Options that fit the evidence:

1. **ProbModelSEED's plant annotator** (`p3.theseed.org`) — BLAST vs.
   `plants_nr` + `exemplar_families` / `isofunctional_families` and/or
   the 8-mer signature match. Both propagate function using homology
   models that don't depend on OrthoFinder OGs, and would produce
   different Sorghum candidate sets.
2. **`kb_orthofinder` running with a much lower user-supplied threshold**
   than 0.55 (the App's `threshold` param is user-supplied, no default),
   *and* against a different reference bundle.
3. **Manual curator additions** on top of an automated first pass —
   consistent with the "ComplexFix / RevFix" nomenclature on the older
   hand-vetted models.

QPSI's `genome_ref` field is empty (typical for locally-run reconstructions)
and no annotated-genome file traceable to it survives in the workspace,
so the exact provenance can't be recovered from files on disk.

## Recommendation for the preprint

If the preprint's methods can cite the new pipeline (Processing_v2-derived
O+PAM+PAH algorithm, per-phylum threshold gating only on paralogs, cached
per-OG PSI matrices), then the new reconstructions in this directory
are the more defensible artifact — every GPR is reproducible from the
recorded provenance (`provenance.json`) with a single `plantseed-annotate`
call.

If the preprint's method already references the QPSI reconstruction
specifically, the 40-reaction gap should be listed as a caveat, and
the ~15 % divergence characterized as "additional homology-based
propagation from ProbModelSEED-derived annotation, not present in the
current pipeline". A follow-up phase could investigate re-annotating
the 40 dropped GPRs via ProbModelSEED's BLAST/kmer path and merging back.

## Appendix — the 40 dropped-feature reactions in full

Every reaction where QPSI's GPR contains one or more Sorghum features
that my new pipeline's GPR does not. Grouped by role and by
Sorghum gene, then listed reaction-by-reaction.

### By Sorghum gene (28 distinct)

The 40 reactions actually collapse to only **28 distinct Sorghum
features**, because a single gene often shows up in many similar
plastidial reactions (e.g., FabZ dehydratase across the fatty-acid
elongation series).

| Sorghum feature | Reactions | Role |
|---|---:|---|
| `Sobic.007G079600` | 9 | (3R)-hydroxypalmitoyl-[acyl carrier protein] dehydratase / FabZ-family dehydratase (EC 4.2.1.-, 4.2.1.59) |
| `Sobic.003G169600` | 4 | NAD and other nucleotides transport (mitochondrial carrier family; TC 2.A.29.10.10) |
| `Sobic.003G108800` | 3 | Methylthioribulose-1-phosphate dehydratase (EC 4.2.1.109); 2,3-diketo-5-methylthiopentyl-1-phosphate enolase-phosphatase (EC 3.1.3.77) |
| `Sobic.001G392500.1.p` \* | 2 | Adenylosuccinate lyase (EC 4.3.2.2) |
| `Sobic.001G056601` | 2 | Tryptophan / Indole synthase alpha chain (EC 4.2.1.20 / 4.1.2.8) |
| `Sobic.001G512800` | 2 | Aconitate hydratase (EC 4.2.1.3) |
| `Sobic.003G303300` | 2 | Aspartate aminotransferase (EC 2.6.1.1) |
| `Sobic.001G260800` | 1 | Alanine transaminase (EC 2.6.1.2) |
| `Sobic.002G211300.1.p` \* | 1 | Alanine transaminase (EC 2.6.1.2) |
| `Sobic.002G211300.2.p` \* | 1 | Alanine transaminase (EC 2.6.1.2) |
| `Sobic.008G069500.1.p` \* | 1 | Phosphoribosylamine-glycine ligase (EC 6.3.4.13) |
| `Sobic.001G118700` | 1 | 6,7-dimethyl-8-ribityllumazine synthase (EC 2.5.1.78) |
| `Sobic.001G470000` | 1 | Cysteine synthase (EC 2.5.1.47) / Serine acetyltransferase (EC 2.3.1.30) |
| `Sobic.001G535500` | 1 | Folylpolyglutamate synthase (EC 6.3.2.17) |
| `Sobic.001G544600` | 1 | Ribose-phosphate pyrophosphokinase (EC 2.7.6.1) |
| `Sobic.002G064500` | 1 | 1-deoxy-D-xylulose 5-phosphate synthase (EC 2.2.1.7) |
| `Sobic.002G104200` | 1 | 4-hydroxyphenylpyruvate dioxygenase (EC 1.13.11.27) |
| `Sobic.002G105600` | 1 | 4-hydroxyphenylpyruvate dioxygenase (EC 1.13.11.27) |
| `Sobic.002G133100` | 1 | Prephenate dehydratase (EC 4.2.1.51) |
| `Sobic.002G160600` | 1 | Indole-3-glycerol phosphate synthase (EC 4.1.1.48) |
| `Sobic.004G054500` | 1 | Porphobilinogen deaminase (EC 2.5.1.61) |
| `Sobic.004G143900` | 1 | Indole-3-glycerol phosphate synthase (EC 4.1.1.48) |
| `Sobic.004G153300` | 1 | Putative acyl-ACP desaturase, Stearoyl-ACP desaturase (EC 1.14.19.2) |
| `Sobic.006G130300` | 1 | Phosphoglycolate phosphatase (EC 3.1.3.18) |
| `Sobic.006G261300` | 1 | Adenylate kinase (EC 2.7.4.3) |
| `Sobic.007G086600` | 1 | Indole-3-glycerol phosphate synthase (EC 4.1.1.48) |
| `Sobic.009G137700` | 1 | Isopentenyl-diphosphate delta-isomerase (EC 5.3.3.2) |
| `Sobic.010G160400` | 1 | Arogenate dehydrogenase (EC 1.3.1.78) |

\* `.p`-suffixed ids are transcript-level protein ids (Sobic.NNN.T.p) that
QPSI's source annotation kept without collapsing to gene level. The new
pipeline emits gene-level ids matching PlantSEED_Roles.json, so even if
the underlying gene were annotated it would appear here under a
different id.

### Per reaction

Full list, 40 rows. `role` shows the canonical role name from the
current PlantSEED template; QPSI-only features are those present in
QPSI's GPR but not in the new pipeline's for the same reaction.

| Reaction | Role | Sorghum features in QPSI, missing in NEW |
|---|---|---|
| `rxn00060_d0` | Porphobilinogen deaminase (EC 2.5.1.61) | `Sobic.004G054500` |
| `rxn00097_d0` | Adenylate kinase (EC 2.7.4.3) | `Sobic.006G261300` |
| `rxn00191_d0` | Alanine transaminase (EC 2.6.1.2) | `Sobic.001G260800`, `Sobic.002G211300.1.p`, `Sobic.002G211300.2.p` |
| `rxn00260_d0` | Aspartate aminotransferase (EC 2.6.1.1) | `Sobic.003G303300` |
| `rxn00474_d0` | Tryptophan synthase alpha chain (EC 4.2.1.20) / beta chain (EC 4.2.1.20) | `Sobic.001G056601` |
| `rxn00493_d0` | Aspartate aminotransferase (EC 2.6.1.1) | `Sobic.003G303300` |
| `rxn00526_d0` | Arogenate dehydrogenase (EC 1.3.1.78) | `Sobic.010G160400` |
| `rxn00689_d0` | Folylpolyglutamate synthase (EC 6.3.2.17) | `Sobic.001G535500` |
| `rxn00770_d0` | Ribose-phosphate pyrophosphokinase (EC 2.7.6.1) | `Sobic.001G544600` |
| `rxn00800_d0` | Adenylosuccinate lyase (EC 4.3.2.2) | `Sobic.001G392500.1.p` |
| `rxn00830_d0` | Isopentenyl-diphosphate delta-isomerase (EC 5.3.3.2) | `Sobic.009G137700` |
| `rxn00974_d0` | Aconitate hydratase (EC 4.2.1.3) | `Sobic.001G512800` |
| `rxn00980_d0` | Phosphoglycolate phosphatase (EC 3.1.3.18) | `Sobic.006G130300` |
| `rxn01000_d0` | Prephenate dehydratase (EC 4.2.1.51) | `Sobic.002G133100` |
| `rxn01682_d0` | Indole synthase (EC 4.1.2.8) / Tryptophan synthase alpha chain | `Sobic.001G056601` |
| `rxn01827_d0` | 4-hydroxyphenylpyruvate dioxygenase (EC 1.13.11.27) | `Sobic.002G104200`, `Sobic.002G105600` |
| `rxn02507_d0` | Indole-3-glycerol phosphate synthase (EC 4.1.1.48) | `Sobic.002G160600`, `Sobic.004G143900`, `Sobic.007G086600` |
| `rxn02895_d0` | Phosphoribosylamine-glycine ligase (EC 6.3.4.13) | `Sobic.008G069500.1.p` |
| `rxn03080_d0` | 6,7-dimethyl-8-ribityllumazine synthase (EC 2.5.1.78) | `Sobic.001G118700` |
| `rxn03136_d0` | Adenylosuccinate lyase (EC 4.3.2.2) | `Sobic.001G392500.1.p` |
| `rxn03909_d0` | 1-deoxy-D-xylulose 5-phosphate synthase (EC 2.2.1.7) | `Sobic.002G064500` |
| `rxn05104_d0` | Methylthioribulose-1-phosphate dehydratase (EC 4.2.1.109) | `Sobic.003G108800` |
| `rxn05105_d0` | 2,3-diketo-5-methylthiopentyl-1-phosphate enolase-phosphatase (EC 3.1.3.77) | `Sobic.003G108800` |
| `rxn05106_d0` | 2,3-diketo-5-methylthiopentyl-1-phosphate enolase-phosphatase (EC 3.1.3.77) | `Sobic.003G108800` |
| `rxn05330_d0` | 3-hydroxyacyl-[ACP] dehydratase, FabZ form (EC 4.2.1.59) | `Sobic.007G079600` |
| `rxn05331_d0` | 3-hydroxyacyl-[ACP] dehydratase, FabZ form (EC 4.2.1.59) | `Sobic.007G079600` |
| `rxn05335_d0` | 3-hydroxyacyl-[ACP] dehydratase, FabZ form (EC 4.2.1.59) | `Sobic.007G079600` |
| `rxn13360_d0` | NAD and other nucleotides transport (mito carrier; TC 2.A.29.10.10) | `Sobic.003G169600` |
| `rxn13361_d0` | NAD and other nucleotides transport (mito carrier; TC 2.A.29.10.10) | `Sobic.003G169600` |
| `rxn15280_d0` | Aconitate hydratase (EC 4.2.1.3) | `Sobic.001G512800` |
| `rxn18935_d0` | 3-hydroxyacyl-[ACP] dehydratase, FabZ form (EC 4.2.1.59) | `Sobic.007G079600` |
| `rxn18936_d0` | 3-hydroxyacyl-[ACP] dehydratase, FabZ form (EC 4.2.1.59) | `Sobic.007G079600` |
| `rxn18937_d0` | (3R)-hydroxypalmitoyl-[ACP] dehydratase (EC 4.2.1.-) / FabZ dehydratase | `Sobic.007G079600` |
| `rxn19345_d0` | Cysteine synthase (EC 2.5.1.47) / Serine acetyltransferase (EC 2.3.1.30) | `Sobic.001G470000` |
| `rxn19686_d0` | 3-hydroxyacyl-[ACP] dehydratase, FabZ form (EC 4.2.1.59) | `Sobic.007G079600` |
| `rxn24508_d0` | Putative acyl-ACP desaturase, Stearoyl-ACP desaturase (EC 1.14.19.2) | `Sobic.004G153300` |
| `rxn25662_d0` | 3-hydroxyacyl-[ACP] dehydratase, FabZ form (EC 4.2.1.59) | `Sobic.007G079600` |
| `rxn25719_d0` | 3-hydroxyacyl-[ACP] dehydratase, FabZ form (EC 4.2.1.59) | `Sobic.007G079600` |
| `rxn29785_d0` | NAD and other nucleotides transport (mito carrier; TC 2.A.29.10.10) | `Sobic.003G169600` |
| `rxn33186_d0` | NAD and other nucleotides transport (mito carrier; TC 2.A.29.10.10) | `Sobic.003G169600` |

### Suggested follow-up

Two paths to close this gap without abandoning the OF+PSI+PlantSEED provenance:

1. Investigate each of the 28 distinct Sorghum genes case-by-case:
   confirm whether their annotation in the old ProbModelSEED /
   `kb_orthofinder` pipeline was biologically correct, and if so, add
   them as `Sbicolor_v3.1.1||...` curated features to
   PlantSEED_Roles.json under the correct role. The next reference-bundle
   build then picks them up naturally.

2. Investigate why they aren't in the same OrthoFinder OG as their
   Arabidopsis counterpart in Results_May26. Possibilities: OF params
   (min-seq-id, e-value) too strict for divergent monocot-eudicot pairs;
   FastTree-generated ML trees over-splitting large gene families;
   sequence errors in the Sobic protein set. Rerunning OrthoFinder
   with tuned parameters (or SHOOT-based placement, which is Phase 1d)
   could recover many of them.
