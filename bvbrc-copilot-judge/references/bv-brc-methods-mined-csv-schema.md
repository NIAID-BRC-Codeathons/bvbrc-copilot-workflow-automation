---
type: Reference
title: bv-brc-methods-mined.csv schema
description: How bv-brc-methods-mined.csv was generated and what each column means.
tags: [bv-brc, patric, literature-mining, data-dictionary]
status: draft
generated: { by: claude-code/claude-sonnet-5, at: 2026-09-14T00:00:00Z }
updated: { by: claude-code/claude-sonnet-5, at: 2026-09-17T00:00:00Z, note: "extended SERVICES from 18 to 43 keys; re-mined against locally cached references/papers/ text where available" }
sources:
  - id: mining-script
    resource: /scripts/mine_bvbrc_methods.py
    title: mine_bvbrc_methods.py — the script that produced this CSV
    last_modified: 2026-09-13T00:00:00Z
  - id: citing-papers
    resource: /references/cite-bv-brc.csv
    title: PubMed export of 739 papers citing the BV-BRC paper (Olson et al. 2023), the input list
    last_modified: 2026-09-10T00:00:00Z
  - id: raw-json
    resource: /references/bv-brc-methods-mined-raw.json
    title: Full per-paper mining output (all 739 papers) that this CSV is filtered/flattened from
    last_modified: 2026-09-13T00:00:00Z
---

# Purpose

A data dictionary for [bv-brc-methods-mined.csv](/references/bv-brc-methods-mined.csv):
how the file was produced and what each of its 61 columns means, so it can
be read or re-derived without reverse-engineering the mining script.

# How it was generated

[mine_bvbrc_methods.py](/scripts/mine_bvbrc_methods.py) starts from
[cite-bv-brc.csv](/references/cite-bv-brc.csv), the PubMed export of 739
papers that cite the BV-BRC paper. For each row with a PMCID it first
checks for a cached copy of the paper's full text at
`references/papers/<pmid>.txt` (written by an earlier run) and reads that
if present; otherwise it fetches the full text via NCBI's BioC API
(`pmcoa.cgi/BioC_json/<pmcid>/unicode`), which only succeeds for papers in
the PMC OA subset — most recent papers behind a publisher paywall have no
retrievable full text and are dropped at this step. As of the 2026-09-17
run, 651 of 739 papers yielded usable full text (up from 645 on
2026-09-13, since PMC's OA-subset membership isn't perfectly static); those
are the only rows that make it into this CSV (the raw JSON keeps all 739,
including the full-text failures, with `hits: {}`).

For each paper with full text, the script:

1. Splits the text into sentences with a regex sentence splitter.
2. For each of 43 known BV-BRC/PATRIC services (the `SERVICES` dict in the
   script — extended on 2026-09-17 from an initial 18 to the full 43-item
   service list used in the stage-1 judge prompt), searches for two tiers
   of terms:
   - **Strong terms** — the service's own name or abbreviation (e.g.
     "comprehensive genome analysis", "rasttk", "similar genome finder").
     Any sentence containing one counts, regardless of context.
   - **General terms** — generic action/output words that could describe
     the service but aren't distinctive on their own (e.g. "assembled",
     "annotated", "differential expression"). A general-term hit only
     counts in a sentence that *also* contains "bv-brc" or "patric"
     (case-insensitive), to avoid false positives from unrelated tools.
3. Records, per service, the count of strong hits, the count of general
   hits, and the first matching sentence (strong hits preferred) as an
   example snippet, truncated to 300 characters and collapsed to one line.

This CSV is the flattened, per-paper view of that output — one row per
paper with retrievable full text, one strong-count/general-count/example
triplet per service. The full nested detail (every matching sentence, not
just the first) is in
[bv-brc-methods-mined-raw.json](/references/bv-brc-methods-mined-raw.json).
Re-running the script re-fetches full text and can return slightly
different counts, since PMC's OA-subset membership isn't perfectly static
between runs (see [log.md](/log.md), 2026-09-13 entry: 618 → 645 papers
between two runs).

# Schema

652 rows: 1 header + 651 papers with retrievable PMC OA full text.

| Column | Type | Description |
|---|---|---|
| `pmid` | string | PubMed ID of the paper. |
| `pmcid` | string | PubMed Central ID (e.g. `PMC13417854`); the key used to fetch full text. |
| `title` | string | Paper title, from the PubMed export. |
| `platform_mentioned` | `True`/`False` | Whether the full text contains "bv-brc" or "patric" (case-insensitive) anywhere at all, independent of any specific service match. |

Then, repeated once per service key below, three columns named
`<service>_strong`, `<service>_general`, `<service>_example`:

| `<service>` key | Service (label in the raw JSON) |
|---|---|
| `cga` | Comprehensive Genome Analysis |
| `assembly` | Genome Assembly Service |
| `annotation` | Genome Annotation Service / RASTtk |
| `sgf` | Similar Genome Finder |
| `proteome_cmp` | Proteome Comparison |
| `variation` | Variation Analysis Service |
| `metagenomics` | Metagenomic Binning / Read Mapping |
| `rnaseq` | RNA-Seq / Transcriptomics Analysis Service |
| `phylo` | Phylogenetic Tree Building / Codon Tree / Gene Tree |
| `crispr` | CRISPR Finder |
| `subsystems` | Subsystems |
| `specialty_genes` | Specialty Genes |
| `amr` | AMR Phenotype Prediction |
| `taxclass` | Taxonomic Classification Service |
| `docking` | Docking Service |
| `pfs` | Protein Family Sorter |
| `pathway` | Pathway / Comparative Pathway |
| `p3tools` | p3-tools / PATRIC CLI / Data API |
| `blast` | BLAST |
| `primer_design` | Primer Design |
| `genome_alignment` | Genome Alignment |
| `tnseq` | Tn-Seq Analysis |
| `bact_genome_tree` | Bacterial Genome Tree |
| `viral_genome_tree` | Viral Genome Tree |
| `cgmlst` | Core Genome MLST |
| `wg_snp` | Whole Genome SNP Analysis |
| `msa_snp` | MSA and SNP Analysis |
| `metacats` | Meta-CATS |
| `protein_structure` | Protein Structure Prediction |
| `protein_stability` | Protein Stability Prediction |
| `comparative_systems` | Comparative Systems |
| `mobile_element` | Mobile Element Detection |
| `expression_import` | Expression Import |
| `fastq_utils` | Fastq Utilities |
| `id_mapper` | ID Mapper |
| `sarscov2_genome` | SARS-CoV-2 Genome Analysis |
| `sarscov2_wastewater` | SARS-CoV-2 Wastewater Analysis |
| `flu_submission` | Influenza Sequence Submission |
| `flu_ha_subtype` | Influenza HA Subtype Conversion |
| `flu_reassortment` | Influenza Reassortment Analysis |
| `subspecies` | Subspecies Classification |
| `viral_assembly` | Viral Assembly |
| `outbreak_tracker` | Outbreak Tracker |

For each service:

- `<service>_strong` (integer): number of sentences matching a strong term
  for that service.
- `<service>_general` (integer): number of sentences matching a general
  term for that service that also mention "bv-brc"/"patric".
- `<service>_example` (string): the first matching sentence (strong hits
  checked before general), whitespace-collapsed to one line and truncated
  to 300 characters; empty if both counts are 0.

A paper can have nonzero strong/general counts for multiple services at
once — the columns are independent per-service tallies, not a single
classification.

# Caveats

- Keyword matching, not NLP: a term match doesn't confirm the paper *used*
  the service (e.g. a background/related-work mention of "annotation"
  alongside "BV-BRC" would count as a general hit) — treat counts as
  signal for triage, not ground truth. See
  [bv-brc-methods-usage.md](/info/bv-brc-methods-usage.md) for the
  aggregate analysis built on this data and its own caveats.
- `p3tools`, `bact_genome_tree`, `viral_genome_tree`, `cgmlst` (partial),
  `msa_snp`, `metacats`, `comparative_systems`, `sarscov2_genome`,
  `flu_submission`, `flu_ha_subtype`, and `viral_assembly` have no
  general-term tier (empty list in the script) — only strong-term hits are
  possible for these, so they'll under-count relative to services with a
  general tier.
- `blast`'s strong terms are deliberately multi-word/specific (`blastp`,
  `protein blast`, etc., never a bare `"blast"`) because the script matches
  substrings, not word boundaries — a bare `"blast"` term would also match
  inside unrelated words like "blastocyst." Even so, BLAST is genuinely
  common outside BV-BRC, so treat this key's counts as noisier than most.
- Rows exist only for papers with retrievable full text; a paper's absence
  from this CSV does not mean it doesn't use BV-BRC, only that its full
  text wasn't fetchable from the PMC OA subset at run time.
