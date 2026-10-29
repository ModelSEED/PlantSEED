# Sam Pelletier — gene evidence notes, 2026-09-15

On the glucosinolate expansion. Genes and papers only; reactions and compounds are
handled separately.

**GS-OX.** "Make sure that GS-OX5 is not one of the genes for the 4 carbon aliphatic,
and the other GSL it was directly tested on (8 carbons) — it definitely works on this
guy. The rest of the chain lengths don't have direct enzymatic evidence."

Done — GS-OX5 (`AT1G12140`) is off the short chain and on the long chain only. It had
been grouped with the other FMOs, so it was assigned by association rather than
evidence.

*Resolved 2026-09-16:* middle chain lengths carry GS-OX1-4, on the strength of Li 2008
([PMID 18799661](https://pubmed.ncbi.nlm.nih.gov/18799661/)) reporting them active
"independent of chain length". GS-OX5 stays long-chain only.

**TGGs.** "I feel great about the TGGs, those are well documented, and those papers
seem appropriate."

Approved. `AT5G26000` and `AT5G25980`, neither currently in PlantSEED. Not added yet
— blocked for a reason unrelated to the genes.

**BZO1 / SCPL17.** "From what I can tell, BZO1 has been biochemically characterized
but SCPL17 has not. So I'm not sure what to do there..."

Both correct, and together they settle it. Lee 2012
([PMID 22762247](https://pubmed.ncbi.nlm.nih.gov/22762247/)) finds BZO1 (`AT1G65880`)
does something other than the step it was assumed to do — characterised, but not our
gene. SCPL17 (`AT3G12203`) has knockout evidence only: mutant loses the products,
accumulates the precursors, no in vitro assay.

*Resolved 2026-09-16:* knockout evidence accepted. SCPL17 assigned to both roles,
which are renamed off "unresolved step". Evidence class recorded in
`CURATION_RATIONALE_260916.md` so it can be revisited if the enzymology lands.
