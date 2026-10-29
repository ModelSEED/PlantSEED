# Glucosinolate biosynthesis — known gaps after the v2.6 expansion

Accepted limitations in the Arabidopsis reconstruction as of the glucosinolate
expansion (PR #56, merged to `dev` 2026-09-30, tagged `v2.6`). None of these
block the release; recorded so they aren't re-discovered as surprises.

## Research gaps (no curatable gene/reaction exists)

- **Gluconasturtiin** (homophenylalanine-derived phenolic GSL). The
  aldoxime-forming enzyme acting on homophenylalanine is unidentified in
  Arabidopsis — this is a literature gap, not a PlantSEED gap. Cannot be
  curated until the enzymology is published.
- **6-(Methylthio)hexyl isothiocyanate.** A measured myrosinase breakdown
  product (not a glucosinolate itself) blocked upstream: the compound does
  not exist in ModelSEED Biochemistry, and glucolesquerellin (its glucosinolate
  precursor) has no hydrolysis reaction defined. Needs new ModelSEED compounds
  + reactions before it can be curated at all.
- **Aliphatic myrosinase, more generally.** TGG1 (`AT5G26000`) / TGG2
  (`AT5G25980`) are approved genes (Pelletier: "I feel great about the TGGs")
  but have nothing to attach to yet — no aliphatic glucosinolate hydrolysis
  reaction exists in the current template.
- **cysteinylglycine-S-conjugate dipeptidase (EC 3.4.13.23), gene-less across
  all three branches (aliphatic, indolic, phenolic).** The reactions are
  curated and carry flux; no Arabidopsis gene is identified for this enzyme
  anywhere in the literature surveyed. Flagged explicitly rather than guessed
  at — "don't go after the gene" per curator decision 2026-09-17.
- **Tyrosine-derived phenolic branch (sinalbin / glucosinalbin).** No roles or
  reactions exist for L-tyrosine → p-hydroxyphenylacetaldoxime → sinalbin.
  Out of scope for this expansion; flagged only if "phenolic glucosinolate"
  is read broadly enough to include it.

## Biologically absent in Col-0 (correctly blocked, not a model defect)

- **Sinigrin and other alkenyl glucosinolates.** AOP2 (`AT4G03060`) is kept in
  the role/reaction set (its gene and reactions, `rxn23785`/`rxn27066`, are
  curated), but UniProt annotates the Col-0 allele as a "Probable INACTIVE
  2-oxoglutarate-dependent dioxygenase." Col-0 does not accumulate alkenyl
  glucosinolates, and sinigrin is absent from the 21 Col-0-measured compounds
  referenced during curation — so zero flux to sinigrin in a Col-0-genotype
  reconstruction is the biologically correct answer, not a gap. A future
  ecotype with active AOP2 would need this revisited at the metabolic
  reconstruction stage (genotype-level gene inactivation), not at the
  PlantSEED role level.
- **2-hydroxy-3-butenyl derivatives.** Same AOP2-dependence; correctly
  blocked for the same reason.

## Secondary modifications explicitly out of scope

Scope for this expansion was "first fully formed glucosinolate" (through the
SOT step); everything past that point was excluded by design, not missed:

- **Benzoylated / sinapoylated glucosinolate modifications**
  (`Hydroxyalkylglucosinolate benzoyltransferase` / `...sinapoyltransferase`,
  reactions `rxn21838`/`rxn21837`/`rxn23787` and
  `rxn21839`/`rxn21840`/`rxn21835`). SCPL17 (`AT3G12203`) is assigned to both
  roles on knockout evidence (Lee 2012, PMID 22762247 — mutant loses both
  product classes, accumulates precursors, no in vitro assay). **None of
  these six reactions are in the current template** (confirmed: not in
  `PlantSEED_Biomass_Template.json`), so the benzoylated/sinapoylated end
  products do not carry flux in the model built from this release. This is a
  template-generation gap on top of the role assignment, not resolved by this
  PR.
- **Indolic secondary modifications downstream of glucobrassicin**
  (4-hydroxylation, 4-methoxylation, 1-methoxylation, 1-hydroxylation via
  CYP81F family + IGMTs): confirmed producible in the merged model
  (neoglucobrassicin, 4-hydroxy-, and 1-hydroxyglucobrassicin all carry flux
  in the v2.6 reconstruction — see FBA check), but biochemically these are
  decorations of the core pathway and were reviewed separately from the
  "first fully formed GSL" scope.
- **AOP-family S-oxygenation/alkenyl/hydroxyalkyl modifications** beyond the
  two balanced in this PR (3-hydroxypropyl-, 4-hydroxybutyl-GSL): covered by
  the methanesulfonate sink fix, confirmed producible.

## Open nomenclature / data-quality items (cosmetic, not blocking)

See the companion report `Curators/samseaver/modelseeddb_report_260930/` for
the upstream ModelSEEDDatabase duplicate-compound and unbalanced-reaction
issues, and `Curators/samseaver/role_capitalization_260930/` for the two role
names fixed for capitalization. Still open after this release:

- `abstract_enzyme` field `"Oxime metabolizining monooxygenase in Trp, Phe,
  Tyr-derived glucosinolates biosynthesis"` carries a typo ("metabolizining")
  — present in `PlantSEED_Roles.json` and `PlantSEED_Complexes.json`. Cosmetic;
  not fixed in this pass because `abstract_enzyme` is a complex grouping key
  and renaming it requires a `CPX_REASSIGN`, not a role-level `UPDATE`.
- Both `Alkylthiohydroximate C-S lyase` and `Aliphatic desulfoglucosinolate
  sulfotransferase` serve all three pathway branches (aliphatic, indolic,
  phenolic) despite their aliphatic-sounding names. Not renamed in this pass;
  flagged for a future naming pass since it would touch role names referenced
  by multiple complexes.
