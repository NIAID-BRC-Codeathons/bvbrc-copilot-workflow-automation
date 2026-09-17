You are analyzing the Methods section of an attached scientific paper to identify which BV-BRC service could have been used, to carry out each computational step described.

Before matching individual steps, first think about what organism(s) the paper's dataset comes from, and use your own knowledge of BV-BRC to judge whether data from that organism could actually be analyzed in BV-BRC at all. If the dataset is not something BV-BRC could realistically handle, set every step's "bv_brc_service" to `null`, regardless of how closely a step's method resembles a listed service by function. If the paper covers multiple organisms and only some of them are feasible in BV-BRC, apply this judgment per step, based on which organism that specific step's data belongs to.

Read the attached paper. For each distinct computational or analytical step, decide which single BV-BRC service best corresponds to it — subject to the feasibility judgment above:

- Comprehensive Genome Analysis
- Genome Assembly Service
- Genome Annotation Service / RASTtk
- Similar Genome Finder
- Proteome Comparison
- Variation Analysis Service
- Metagenomic Binning / Read Mapping
- RNA-Seq / Transcriptomics Analysis Service
- Phylogenetic Tree Building / Codon Tree / Gene Tree
- CRISPR Finder
- Subsystems
- Specialty Genes
- AMR Phenotype Prediction
- Taxonomic Classification Service
- Docking Service
- Protein Family Sorter
- Pathway / Comparative Pathway
- p3-tools / PATRIC CLI / Data API
- BLAST
- Primer Design
- Genome Alignment
- Tn-Seq Analysis
- Bacterial Genome Tree
- Viral Genome Tree
- Core Genome MLST
- Whole Genome SNP Analysis
- MSA and SNP Analysis
- Meta-CATS
- Protein Structure Prediction
- Protein Stability Prediction
- Comparative Systems
- Mobile Element Detection
- Expression Import
- Fastq Utilities
- ID Mapper
- SARS-CoV-2 Genome Analysis
- SARS-CoV-2 Wastewater Analysis
- Influenza Sequence Submission
- Influenza HA Subtype Conversion
- Influenza Reassortment Analysis
- Subspecies Classification
- Viral Assembly
- Outbreak Tracker

Output ONLY a JSON array, with no explanation, markdown, or text before
or after it, in exactly this format:

[
  { "step_description": "...", "bv_brc_service": "..." }
]

Rules:
- One object per distinct step in the Methods section, in the order the steps appear.
- "step_description" is a short, one-sentence description of what the authors did, in your own words, based on what the step accomplishes (e.g. "assembled paired-end Illumina reads into a draft genome") — not a restatement of a tool name found in the text.
- "bv_brc_service" is the single best-matching name from the list above, copied verbatim, or the JSON value `null` if no service on the list applies to that step. Always include the key, even when its value is `null`.
- Base the match on what the step does, not on whether a matching name literally appears in the text — infer the service from the method description itself.
- Do not invent steps that aren't in the Methods section, and do not merge multiple distinct steps into one entry.
- Never match a step to a service just because the underlying algorithm/method is generic (e.g., k-mer counting, BLAST, read alignment) if you judged that BV-BRC could not actually analyze data from that organism — see the feasibility judgment above.

Output to: work/json_outputs/unmasked/[PMID].claudesonnet.json
Compare with: work/json_outputs/unmasked/[PMID].copilot.json
Give bullet point summary of the comparison.
PMID: