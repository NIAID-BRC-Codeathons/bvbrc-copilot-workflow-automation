# Stage-1 judge report — PMID 37948307

**Paper:** Draft genome sequences of two Pseudomonas strains isolated from
129I plumes at the Hanford Site (microbial genome announcement).

**Masking:** no-op. `references/papers/37948307.txt` and
`references/papers_masked/37948307.txt` are byte-identical, so this paper
has no maskable BV-BRC/PATRIC service terms — only the unmasked run was
performed.

**Copilot input note:** the live Copilot API was unavailable for this
run. Copilot's answer was obtained manually — the exact prompt was
generated with `--print-prompt`, pasted into the BV-BRC Copilot UI by the
user, and the raw reply converted to JSON via `--manual-response`. Same
downstream contract as a live query, so this does not affect
comparability with other runs.

## Unmasked run

| Category | Services |
|---|---|
| All three agree (Claude ∩ Copilot ∩ CSV) | annotation, assembly |
| Claude + Copilot only (not in CSV) | fastq_utils, sgf, taxclass |
| Claude + CSV only | (none) |
| Copilot + CSV only | (none) |
| Claude only | (none) |
| Copilot only | (none) |
| CSV only (both missed) | (none) |

**Jaccard:** Claude/Copilot = 1.0, Claude/CSV = 0.4, Copilot/CSV = 0.4,
three-way = 0.4

**Unresolved names:** none for either model — every service name both
models produced mapped cleanly onto a known key.

### Reading the numbers

Claude and Copilot produced **identical service sets** for this paper
(Jaccard 1.0) — both segmented the Methods into the same 7 steps and
assigned the same BV-BRC service to each one, including agreeing to
return `null` for the CheckM completeness/contamination step (no listed
BV-BRC service covers that function). This is the strongest possible
same-run agreement.

Against the ground-truth CSV, both models only get credit for 2 of the 5
services they named — **Genome Assembly Service** and **Genome
Annotation Service / RASTtk** — because the CSV keyword-mining only
picked up mentions that map to those two categories from this short
genome-announcement paper. The other 3 services both models named
(Fastq Utilities, Similar Genome Finder, Taxonomic Classification
Service) are not confirmed by the CSV, but all three are functionally
well-supported by the text: bcl-convert-based demultiplexing/QC/trimming
maps naturally onto Fastq Utilities, the ANI genome-comparison step maps
onto Similar Genome Finder, and both the 16S rRNA identification and the
TYGS dDDH species-ID step map onto Taxonomic Classification Service. The
CSV's narrower hit set here looks like a ground-truth mining gap (it
likely only fires on explicit BV-BRC tool-name mentions in the text, and
this paper only explicitly names BV-BRC for the assembly step) rather
than either model over-generating.

No service was missed by both models relative to the CSV, and no service
was uniquely named by only one of the two.

## Masking check

Not applicable — masking was a no-op for this paper (see above), so
there is no masked-vs-unmasked gap to interpret for name-copying vs.
genuine service recognition on this particular PMID.
