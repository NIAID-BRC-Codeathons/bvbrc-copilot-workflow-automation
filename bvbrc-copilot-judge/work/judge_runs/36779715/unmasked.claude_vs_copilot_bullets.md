# Claude vs. Copilot — PMID 36779715, unmasked

- **Wet-lab / non-computational steps (collection, DNA extraction, sequencing
  prep, base-calling):** both agree these get `null`. Copilot includes
  base-calling (Guppy) as its own step and nulls it; Claude splits collection,
  extraction/library prep, and base-calling into three null steps. Segmentation
  differs, service judgment doesn't.
- **Quality filtering (Filtlong):** both map to Fastq Utilities
  (`fastqutils`/`fastq_utils` — same key after normalization).
- **Assembly (Flye):** both pick Viral Assembly (`viral_assembly`), consistent
  with this being a phage genome rather than a bacterial one.
- **Polishing (Medaka):** Copilot nulls this as a separate step; Claude folds
  it into the same Viral Assembly call as the Flye step, treating polishing as
  part of the assembly/finishing workflow rather than a step with no BV-BRC
  equivalent. This is a genuine, not just segmentation, divergence.
- **Annotation (BV-BRC bacteriophage pipeline / PHANOTATE):** both agree,
  Genome Annotation Service.
- **InterProScan + BLASTx refinement:** Copilot merges both tools into one
  step and maps it to `genome_annotation`. Claude splits them: InterProScan
  (protein-domain classification, no clean BV-BRC equivalent) gets `null`;
  BLASTx gets `blast`. Real disagreement on InterProScan's mapping, not just
  segmentation — Copilot treats domain-refinement as part of annotation,
  Claude treats it as unsupported.
- **PhageTerm (failed termini call):** both agree `null`.
- **Read mapping for coverage:** both agree `null` — no listed service covers
  read-to-assembly coverage mapping specifically (distinct from a
  genome-to-genome alignment service).
- **BLASTn vs. public databases:** both agree, `blast`.

**Net:** high agreement on 6 of ~9 distinct methodological steps. The two
real divergences are (1) whether Medaka polishing counts toward Assembly or
is unsupported, and (2) whether InterProScan should be folded into
Annotation or left unsupported — both are judgment calls about step
granularity/scope, not disagreements about what BV-BRC offers.
