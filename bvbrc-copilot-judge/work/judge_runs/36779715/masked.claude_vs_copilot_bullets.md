# Claude vs. Copilot — PMID 36779715, masked

Two tool names are masked in this run: `InterProScan v5.91-91 and
[MASKED-SERVICE]` (was BLASTx) and `A [MASKED-SERVICE] search with the whole
genome` (was BLASTn).

- **Wet-lab / base-calling steps:** same pattern as unmasked — both null
  them, segmented slightly differently. Copilot maps base-calling itself to
  `genome_assembly` this time (a change from unmasked, where it was `null`);
  Claude keeps it `null` in both runs, since base-calling is a signal-to-FASTQ
  step upstream of any assembly service.
- **Quality filtering (Filtlong):** Copilot flips to `null` in the masked run
  (was `fastqutils` unmasked) even though the surrounding text describing
  Filtlong is untouched by masking — a segmentation/consistency wobble, not
  something the masking caused. Claude stays `fastq_utils` in both runs.
- **Assembly (Flye) / polishing (Medaka):** Copilot now maps both Flye and
  Medaka to `genome_assembly` (unmasked: Flye→`viral_assembly`, Medaka→
  `null`). Claude stays `viral_assembly` for both, unchanged from unmasked.
- **Annotation (BV-BRC pipeline / PHANOTATE):** both agree, unchanged.
- **InterProScan + masked BLASTx step:** Copilot again merges the two tools
  into one step and maps it to `genome_annotation`, unchanged from unmasked
  despite the second tool's name being hidden — consistent with Copilot
  reading "additional functional predictions" and defaulting to Annotation
  regardless of which specific tool is named. Claude again splits them:
  InterProScan → `null`, and independently *infers* (without seeing the name)
  that the masked tool is most likely a BLAST-style sequence search given its
  role pairing with InterProScan for functional refinement → `blast`. Same
  call as the unmasked run, made without the name.
- **PhageTerm:** Copilot drops this step entirely from the masked run (it
  appears unmasked as a `null`-mapped step); the surrounding text is
  identical, so this is a step Copilot lost rather than one masking removed.
  Claude keeps it as a `null` step in both runs.
- **Read mapping for coverage:** both agree `null`, unchanged.
- **Masked BLASTn-equivalent whole-genome search:** Copilot maps the masked
  step to `blast` — the same call it made unmasked, i.e. it inferred the tool
  from context/function rather than needing the name. Claude does the same
  and also infers `blast`.

**Net:** on the two literally-masked steps, both models land on the same
service call they made when the name was visible (`blast` for the
InterProScan-paired step, `blast` for the whole-genome search) — genuine
functional inference, not name-copying, for *those* two steps. But masking
also coincides with several *un*-masked steps changing in Copilot's output
(base-calling, Filtlong, Medaka) and one step disappearing (PhageTerm) with
no textual reason to change — that's re-run instability in Copilot's
segmentation/labeling, not a masking effect, and it lowers confidence in
treating any single run's step count/labels as fully deterministic.
