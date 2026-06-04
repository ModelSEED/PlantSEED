# Homomethionine biosynthesis — curation review

PlantSEED subsystem: **`Homomethionine_biosynthesis`**

Scope: methionine → homomethionine (one cycle of methionine chain elongation), plus the additional 5 chain-elongation iterations that the same roles catalyse out to hexahomomethionine. Stopping point is the first non-methionine amino acid (homomethionine, `cpd17403`). The five subsequent chain extensions are listed in a "chain elongation" appendix because they reuse the same five roles.

Sources read:
- `Data/PlantSEED_v3/PlantSEED_Roles.json` (authoritative)
- `Curators/ricon001/Homomethionine/*.tsv` + `Update_Homomethionine_Roles.py`
- `Curators/tjcontant/notes`, `Curators/tjcontant/Glucosinolates/gls_enzymes`, `Curators/tjcontant/glucosinolate_psi.json`
- Generic-compound + IMDH NAD edits in `Curators/samseaver/template_reaction_curation_260602/glucosinolate_chemistry.tsv`

## Curated step sequence (methionine → homomethionine)

| # | Substrate → product | EC | PlantSEED role | Reaction(s) | A. thaliana genes |
|---|---|---|---|---|---|
| 1 | L-Methionine (`cpd00060`) → 4-methylthio-2-oxobutyrate (`cpd00869`) | 2.6.1.88 | **Methionine transaminase (EC 2.6.1.88)** | rxn05108 | BCAT4 (AT3G19710) |
| 2 | 4-methylthio-2-oxobutyrate (`cpd00869`) + AcCoA + H₂O → 2-(2′-methylthio)ethylmalate (`cpd17400`) | 2.3.3.17 | **Methylthioalkylmalate synthase, 5C-6C only (EC 2.3.3.17)** | rxn14004 | MAM1 (AT5G23010), MAM3 (AT5G23020) |
| 3 | 2-(2′-methylthio)ethylmalate (`cpd17400`) ↔ 3-(2′-methylthio)ethylmalate (`cpd17402`) | 4.2.1.170 | **Methylthioalkylmalate dehydratase large subunit (EC 4.2.1.170)** + **small subunit (EC 4.2.1.170)** | rxn13975 | LSU1 (AT4G13430); SSU2 (AT2G43100), SSU3 (AT3G58990) |
| 4 | 3-(2′-methylthio)ethylmalate (`cpd17402`) → 2-oxo-5-methylthiopentanoate (`cpd17401`) + CO₂ | 1.1.1.- | **Methylthioalkylmalate dehydrogenase (EC 1.1.1.-)** | rxn14172 | IMD1 (AT5G14200), IMD2 (AT1G31180) |
| 5 | 2-oxo-5-methylthiopentanoate (`cpd17401`) + Glu ↔ **L-Homomethionine (`cpd17403`)** + 2-oxoglutarate | 2.6.1.- | **2-oxo-5-methylthiopentanoate transaminase (EC 2.6.1.-)** | rxn23780 | BCAT3 (AT3G49680) |

This is the first pass-through of the methionine chain-elongation cycle. Steps 2-5 are repeated five more times with longer-chain substrates — see chain-elongation appendix below.

## Chain-elongation appendix (homomethionine → hexahomomethionine)

The same four enzymes (MAM, IPMI, IMDH, BCAT3) catalyse five further iterations. Reactions per role, mapped to the chain length produced by the BCAT3 step:

| Cycle | MAM (synthase) | IPMI (isomerase) | IMDH (dehydrogenase) | BCAT3 (transaminase) | End-product amino acid |
|---|---|---|---|---|---|
| 1 (to Homomet) | rxn14004 | rxn13975 | rxn14172 | rxn23780 | Homomethionine (`cpd17403`, 6C) |
| 2 | rxn14183 | rxn14248 | rxn14182 | rxn27069 | Dihomomethionine (`cpd17407`, 7C) |
| 3 | rxn14308 | rxn14059 | rxn13977 | rxn27070 | Trihomomethionine (`cpd17411`, 8C) |
| 4 | rxn14205 | rxn14278 | rxn14122 | rxn27071 | Tetrahomomethionine (`cpd17415`, 9C) |
| 5 | rxn14347 | rxn13995 | rxn14244 | rxn27072 | Pentahomomethionine (`cpd17419`, 10C) |
| 6 | rxn14102 | rxn14156 | rxn13983 | rxn27073 | Hexahomomethionine (`cpd17423`, 11C) |

All 24 reactions are present in PlantSEED_Roles.json and consistently grouped under the four roles. The 5C-6C-only MAM sub-role (rxn14004, rxn14183) reflects the documented substrate preference of MAM1/MAM3 — assigned to AT5G23010 + AT5G23020 only; the full chain-length role accepts the broader set of orthologs.

## Curation actions still pending (gaps / open items)

1. **BCAT3 generic-compound edit not yet applied.** Six BCAT3 reactions (rxn23780, rxn27069-73) carry generic placeholders `cpd22369` and `cpd21904` for the amino donor/acceptor. The fix to substitute these for 2-oxoglutarate (`cpd00023`) and L-Glu (`cpd00024`) lives in `samseaver/template_reaction_curation_260602/glucosinolate_chemistry.tsv` (block 3) but the `REPLACE compound` action is one of three proposed actions waiting on apply-pipeline support. Until applied, BCAT3 steps appear chemically incomplete.
2. **IMDH NAD pair not yet applied.** All six IMDH reactions (rxn14172, rxn14182, rxn13977, rxn14122, rxn14244, rxn13983) need NAD⁺/NADH added (with the placeholder H⁺ removed). Curated in `glucosinolate_chemistry.tsv` (block 5) — also pending `ADD reagent` apply-pipeline support.
3. **Sub-step 3a/3b in `tjcontant/notes` not realised in PlantSEED.** The notes file decomposes step 3 into a separate dehydration (rxn46433) and re-hydration (rxn48196) via the maleate intermediate `cpd33422`. The current curation collapses both into a single isomerisation (rxn13975). Decide whether to keep the lumped reaction or split it out for the remaining five cycles too (none of which are split at present).
4. **PWY-1186 pathway tag missing on the IPMI roles.** Both IPMI subunit roles carry no MetaCyc pathway tag in `gls_enzymes` (column 7 blank), whereas every other step lists `PWY-1186`. Cosmetic but worth aligning.
5. **`tjcontant/notes` ends at "HOMOMETHIONINE CHAIN ELONGATION" with no body.** The narrative explanation of cycles 2-6 was never written; the actual reaction coverage in PlantSEED_Roles.json IS complete, so this is a documentation gap rather than a curation gap.
6. **No homomethionine → cytosol transport reaction.** Steps 2-5 are localised to the chloroplast / stroma (`d` compartment per `MAM1_Localization.tsv` and Sam's `glucosinolate_transport.tsv`). Sam's transport TSV (lines 30-43) defines `glucosinolates_1` (transport of `cpd00869` c→d), `glucosinolates_2` (`cpd17400` c→d) and `glucosinolates_3` (`cpd17403` c→d) but these are template-only reactions waiting on the `NEW reaction` action — apply-pipeline support still pending.
7. **No homomethionine sink demand reaction.** The pathway ends at homomethionine but homomethionine is consumed only by Homomethionine N-monooxygenase (see aliphatic GSL report). If the model is built without the downstream pathway, homomethionine has no sink.

## Cross-reference

- Downstream consumer of homomethionine (and chain-elongated homologues): see `02_aliphatic_glucosinolate_biosynthesis.md`.
- Indolic and phenolic glucosinolate pathways branch from tryptophan and phenylalanine respectively and do not use any homomethionine intermediates — see reports 03 and 04.
