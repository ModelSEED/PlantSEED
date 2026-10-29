# Citation review regeneration - 2026-09-07

All four photosynthetic-ETC subsystem reviews were regenerated from scratch. The 2026-08-12
versions are **superseded** and were moved out of the repository to
`plantseed-v3-curation/work/superseded_2026-08-12/`, i.e. beside the checkout, not inside it.

## Why they were redone

The August pass ran with only the PubMed MCP available. Citations PubMed could not resolve by
DOI were labelled `UNRESOLVED` - 15 citation-instances, covering 10 unique DOIs that the
per-role detail named explicitly. Rather than stopping there, that pass went on to assert what
each of those 10 papers "likely" was. Re-checking all 10 against Crossref, **seven were wrong** - three of them wrong about the organism, which is the
fact the whole classification turns on.

Crossref and Europe PMC MCP servers were registered on 2026-09-07. Crossref resolves
105/106 DOIs. (Europe PMC registers but its tool list fails schema validation at the
gateway, so it loads no tools; it was not used.)

## Method

1. Extract every role and publication for the four subsystems directly from
   `Data/PlantSEED_v3/PlantSEED_Roles.json` at tag v2.5 - 106 unique DOIs.
2. Resolve each DOI against the Crossref REST API for authoritative title, first author, year,
   journal and work type.
3. Resolve each DOI to a PMID via NCBI E-utilities (`<doi>[AID]`, falling back to a title search).
4. Fetch PubMed records for the 81 PMIDs and take **MeSH organism descriptors** as the
   organism evidence, rather than keyword-matching the title.
5. Hand-adjudicate the 46 records that had no usable PubMed MeSH organism descriptor (the 25 with
   no PubMed record at all, plus those whose MeSH carries only generic terms such as "Plants" or
   "Chloroplasts"), reading the Crossref title and abstract. Each adjudication is recorded inline in the report as an
   `_evidence:_` line.

Nothing in the new reports is inferred from a DOI string.

## What changed in the vocabulary

The August reports used a single conflated label per citation, with two different spellings
between files (`ARABIDOPSIS_ORIGINAL_OR_CHARACTERIZATION` in PSII vs `ARABIDOPSIS` in the other
three; `UNRESOLVED` vs `UNRESOLVED_OR_UNKNOWN`). That is replaced by three independent axes:

| axis | values |
|---|---|
| organism | Arabidopsis, Arabidopsis + other, other plant, alga, cyanobacterium, n/a |
| article type | primary, review, book chapter, off-topic |
| verification | PubMed, Crossref only, UNVERIFIABLE |

`UNRESOLVED` conflated "not in PubMed" (fine, per the curation norms) with "does not exist"
(a defect). Those are now separate: **24 citations are Crossref-only and acceptable**;
**1 is genuinely unverifiable**.

## Corpus totals (106 unique DOIs)

| organism | n |
|---|---|
| PLANT_OTHER | 51 |
| CYANOBACTERIUM | 22 |
| ARABIDOPSIS | 21 |
| ALGA | 5 |
| ARABIDOPSIS_PLUS | 4 |
| NONE | 2 |
| UNKNOWN | 1 |

| article type | n |
|---|---|
| primary | 101 |
| review | 3 |
| unknown | 1 |
| off topic | 1 |

| verification | n |
|---|---|
| PubMed | 81 |
| Crossref only | 24 |
| UNVERIFIABLE | 1 |

## Specific corrections to the August reports

| DOI | August claim | Verified | Consequence |
|---|---|---|---|
| `10.1016/S0021-9258(18)98849-6` | Yamamoto 1984, PsbO purification, spinach | Philbrick, Diner & Zilinskas 1991, cyanobacterial MSP-null mutants, JBC | organism other plant -> cyanobacterium (PsbO) |
| `10.1016/0014-5793(89)81446-2` | psbI/psbL in spinach | Ikeuchi 1989, *Synechococcus vulcanus* | organism other plant -> cyanobacterium (PsbI, PsbL) |
| `10.1016/0167-4838(92)90484-U` | Bricker review on CP43/CP47 | Mori & Yamamoto 1992, Tris-treatment of PSII membranes | article type review -> primary (PsbB, PsbC) |
| `10.1016/0005-2728(82)90271-7` | Berthold/Babcock/Yocum BBY-particle paper | Akerlund, Jansson & Andersson 1982, inside-out thylakoid vesicles | wrong paper entirely |
| `10.1016/0005-2728(83)90227-X` | Kuwabara & Murata, 33/23/16-kDa OEC | Miyao & Murata 1983, 24/18-kDa binding | wrong author and subunits |
| `10.1016/S0021-9258(19)81479-5` | Ljungberg 1986, PsbR | Lautner 1988, 10-kDa PSII precursor, spinach | wrong author and year |
| `10.1093/oxfordjournals.pcp.a077628` | PCP 1994, Kapazoglou, PsbTn precursor | PCP 1988, a 4.8-kDa intrinsic PSII RC polypeptide | wrong year; **probable mis-assignment**, see below |

Three of the ten held up: `10.1016/0014-5793(84)80949-7` (Herrmann 1984),
`10.1016/0014-5793(88)81280-8` (Murata 1988) and `10.1016/0005-2728(86)90102-7` (Ljungberg 1986).

## Defects found across all four subsystems

| Subsystem | Role | Citation | Problem |
|---|---|---|---|
| Photosystem_I | Photosystem I subunit Ib PsaB | `10.21577/0103-5053.20170238` | off-topic - benzopyran chemistry in *Piper gaudichaudianum*; no connection to photosynthesis |
| Photosystem_I | Photosystem I PsaN | `10.1071/SA0403172` | DOI returns 404 at Crossref and has no PubMed record - cannot confirm it exists |
| Photosystem_I | Photosystem I assembly related protein Ycf3 | (empty string) | empty string in the `publications` array |
| Photosystem_I | Photosystem I assembly related protein Ycf4 | (empty string) | empty string in the `publications` array |

### Resolved 2026-09-07: PsbTn -> PsbI reassignment

`10.1093/oxfordjournals.pcp.a077628` (Ikeuchi & Inoue 1988, *Plant Cell Physiol.* 29:1233) was
cited on **PsbTn**. The paper characterises the 4.8-kDa polypeptide intrinsic to the PSII
reaction centre; the authors' companion paper that year, *A new photosystem II reaction center
component (4.8 kDa protein) encoded by chloroplast genome*
([10.1016/0014-5793(88)81039-1](https://doi.org/10.1016/0014-5793(88)81039-1)), assigns that
protein to **psbI**, and their 1989 follow-up states it directly: "a new low-molecular-mass
component of 4.8 kDa encoded by a chloroplast gene, psbI". Authorship was confirmed from the
reference list of that 1989 paper, since Crossref carries no author names for the PCP record and
PCP 1988 is not indexed in PubMed.

The citation was therefore **moved from PsbTn (`PS_role_a1c0a6`) to PsbI (`PS_role_f1057a`)** in
`PlantSEED_Roles.json`. PsbTn retains three valid citations, including Chen 2018 (Arabidopsis) and
Ljungberg 1986, whose 5 kDa hydrophilic spinach PSII polypeptide is PsbTn. PsbI gains the original
identification of its gene product.

**Suggested follow-up (not applied):** add
[10.1016/0014-5793(88)81039-1](https://doi.org/10.1016/0014-5793(88)81039-1) to PsbI as well - it
is the paper that actually makes the psbI gene assignment, and is arguably the stronger primary
citation of the two.

The two empty strings were reported in August as "Non-DOI URL" - they are not URLs, they are
empty strings, and they inflate the apparent citation count for Ycf3 and Ycf4 (both actually
have exactly one real citation).

## Not yet reviewed in the photosynthetic apparatus

NDH / cyclic electron flow, and the LHCA/LHCB light-harvesting antenna.

## Reproducing

Scripts are in `work/` beside the checkout, not in the repository:
`resolve.py` (Crossref), `pmids.py` (DOI->PMID), `mesh.py` (PubMed records), `final.py`
(classification + adjudications), `report.py` (report generation). Caches: `crossref.json`,
`pmid.json`, `pubmed.json`, `final.json`.

---

_Citation metadata retrieved from PubMed (NCBI E-utilities) and Crossref. All PubMed-derived
records are cited with their PMID and DOI in the per-subsystem reports._
