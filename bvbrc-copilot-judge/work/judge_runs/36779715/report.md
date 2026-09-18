# Stage-1 judge report — PMID 36779715

**Paper:** Complete Genome Sequence of the Lysogenic *Pseudomonas*
Bacteriophage Fyn8 (microbial genome announcement; ONT long-read sequencing
of a phage isolated from river water).

**Copilot input note:** the live Copilot API was unavailable for both runs
in this session (confirmed by two failed retries, including a retest against
the unmasked paper). Both Copilot answers were obtained manually — the exact
prompt was generated with `--print-prompt`, pasted into the BV-BRC Copilot UI
by the user, and the raw reply converted to JSON via `--manual-response`.
Same downstream contract as a live query, so this does not affect
comparability with other runs.

**Masking:** active. `references/papers/36779715.txt` and
`references/papers_masked/36779715.txt` differ — two tool mentions are
redacted to `[MASKED-SERVICE]`: the "InterProScan and BLASTx" functional
refinement step, and the whole-genome "BLASTn search" comparison step. Both
unmasked and masked runs were performed.

## Unmasked run

| Category | Services |
|---|---|
| All three agree (Claude ∩ Copilot ∩ CSV) | annotation, blast |
| Claude + Copilot only (not in CSV) | viral_assembly |
| Claude + CSV only | (none) |
| Copilot + CSV only | (none) |
| Claude only | fastq_utils |
| Copilot only | (none) |
| CSV only (both missed) | (none) |

**Jaccard:** Claude/Copilot = 0.75, Claude/CSV = 0.5, Copilot/CSV = 0.667,
three-way = 0.5

**Unresolved names:** Copilot's `"fastqutils"` (no separating underscore/
space) — no ground truth available for this exact string; it fails to
resolve onto the CSV's `fastq_utils` key even though the *intent* clearly
matches the Filtlong quality-filtering step Claude independently mapped to
`fastq_utils`. This is a scoring-alias gap, not a claim either model got
wrong.

### Reading the numbers

Claude and Copilot agree on the two CSV-confirmed services for this paper —
**Genome Annotation Service / RASTtk** (for the BV-BRC bacteriophage
pipeline / PHANOTATE step) and **BLAST** (for the BLASTn whole-genome
comparison) — matching the CSV's `annotation_general` and `blast_strong`
hits exactly. Neither model missed anything the CSV confirmed, and neither
over-claimed a CSV-confirmed key the other didn't also name.

Both models also independently named **Viral Assembly** for the Flye
assembly step, which the CSV does not confirm (no `viral_assembly` or
`assembly` hit in the row for this PMID at all) — plausible given this is
explicitly a phage genome and BV-BRC has a dedicated viral-assembly path,
and it looks like a CSV mining gap (the CSV's keyword rules likely require
an explicit "assembly service"-style phrase, and this paper only says
"assembled... with Flye") rather than either model over-generating.

The one real disagreement, once the alias gap is set aside, is **Medaka
polishing**: Claude folds it into the same `viral_assembly` call as the Flye
step (treating polishing as part of the assembly/finishing workflow);
Copilot leaves the Medaka step `null`. Both are defensible — BV-BRC's
assembly service does include a polishing stage, but a model could also
read "assembly" as covering only the initial contig-building call. A second,
smaller disagreement: Claude splits the "InterProScan and BLASTx" sentence
into two steps (InterProScan → `null`, no clean BV-BRC equivalent for
domain-level classification; BLASTx → `blast`), while Copilot merges both
tools into one step and calls it `genome_annotation`. This doesn't change
the resolved-key sets here (Claude's `blast` from BLASTx is already covered
by its BLASTn `blast` call), but it is a genuine difference in how each
model scopes "functional annotation" versus "sequence search."

## Masked run

| Category | Services |
|---|---|
| All three agree (Claude ∩ Copilot ∩ CSV) | annotation, blast |
| Claude + Copilot only (not in CSV) | (none) |
| Claude + CSV only | (none) |
| Copilot + CSV only | (none) |
| Claude only | fastq_utils, viral_assembly |
| Copilot only | assembly |
| CSV only (both missed) | (none) |

**Jaccard:** Claude/Copilot = 0.4, Claude/CSV = 0.5, Copilot/CSV = 0.667,
three-way = 0.4

**Unresolved names:** none for either model in this run — every service name
both models produced mapped cleanly onto a known key (Copilot's `fastqutils`
spelling issue from the unmasked run doesn't recur here because Copilot
nulled the Filtlong step instead of naming a service for it).

### Reading the numbers

On the two literally-masked steps, both models land on the *same* call they
made when the tool name was visible: for the InterProScan-paired step and
for the whole-genome comparison step, both independently infer `blast` from
function and phrasing alone ("additional functional predictions... and
[masked]"; "a [masked] search... showed... 94% identical"). Claude's
inference is explicit — it never saw "BLASTx"/"BLASTn" for this run and
still named `blast` from context — and Copilot's masked-run output shows the
same call, which is consistent with genuine functional recognition on *this
specific pair of masked terms* rather than pure name-copying.

That said, the run-to-run gap here is dominated by something else: Copilot's
labeling on several *unmasked* steps shifted between the two runs even
though the underlying text for those steps didn't change. Base-calling
(Guppy) went from `null` (unmasked) to `assembly`/`genome_assembly` (masked);
Flye assembly and Medaka polishing collapsed from
`viral_assembly`+`null` (unmasked) into a single `assembly` call covering
both (masked); the Filtlong quality-filtering step went from a
(malformed but clearly intended) `fastqutils` call to `null`; and the
PhageTerm step, present as a `null` entry unmasked, is missing entirely from
the masked output. Claude's independent read is stable across both runs —
identical resolved-key sets except that Claude, unlike Copilot, keeps
`fastq_utils` and `viral_assembly` in both runs. Because Copilot's own
segmentation and labeling aren't stable step-to-step on unrelated,
unmasked text, the masked-vs-unmasked Jaccard drop (0.75 → 0.4 for
Claude/Copilot) is not a clean signal about masking's effect specifically —
it's entangled with Copilot's apparent run-to-run inconsistency. The
narrower, cleaner signal — how the two *literally masked* steps were
resolved — points toward genuine service recognition rather than
name-copying, since both models made the same call with and without the
name visible.
