# judge_runs/

Output of the [bvbrc-copilot-judge](../../.claude/skills/bvbrc-copilot-judge/SKILL.md)
skill: one AI-judge run per PMID, comparing BV-BRC Copilot's and Claude's
independent reads of a paper's Methods section against each other and
against [bv-brc-methods-mined.csv](../../references/bv-brc-methods-mined.csv)
(keyword-mined ground truth, 43 BV-BRC/PATRIC services). This is scratch
working output, not a canonical document - no frontmatter here or in the
per-run files below.

## How to run it

Invoke the `bvbrc-copilot-judge` skill with a PMID that already has a
cached full-text file at `references/papers/<pmid>.txt`. Requires
`BVBRC_TOKEN` set in the environment (or `.env`) for the live Copilot API
call - the skill checks for this up front and fails fast if it's missing.

The skill does not fetch new papers; if the PMID you want isn't in
`references/papers/`, run
[scripts/mine_bvbrc_methods.py](../../scripts/mine_bvbrc_methods.py) first
(see [references/papers/README.md](../../references/papers/README.md)).

## What the pipeline does

For a given PMID:

1. **Masking check.** Diffs `references/papers/<pmid>.txt` against
   `references/papers_masked/<pmid>.txt`. If they're identical, the paper
   has no BV-BRC/PATRIC service names to redact, so the masked run is
   skipped entirely (running an identical prompt twice would waste a
   Copilot call on a number that's already known to be meaningless). If
   they differ, both an **unmasked** and a **masked** run happen - the gap
   between the two is a diagnostic of whether Copilot is recognizing a
   method description or just copying a name already on the page.
2. **Two independent step->service reads**, per active run:
   - Copilot, queried programmatically via
     [scripts/query_copilot_stage1.py](../../scripts/query_copilot_stage1.py)
     (the placeholder-style prompt with the paper's text spliced in - not
     the "attached file" prompt variant [compare-with-copilot](../../.claude/skills/compare-with-copilot/SKILL.md)
     uses for manual, web-UI runs, since the programmatic API has no
     file-attachment mechanism).
   - Claude, reading the same text directly and independently (not shown
     Copilot's answer first).
3. **Ground-truth scoring**, per model per run, via
   [scripts/score_stage1_json.py](../../scripts/score_stage1_json.py): each
   model's freeform service names are resolved onto the CSV's 43 keys and
   diffed against that paper's CSV hits (misses / unsupported / unresolved).
4. **3-way overlap**, per run, via
   [scripts/judge_overlap.py](../../scripts/judge_overlap.py): the same
   resolved-key sets for Claude, Copilot, and the CSV, compared pairwise
   and three-way (Jaccard + an agree/only-X breakdown). Overlap is
   computed on **resolved service keys, not step-by-step** - Claude and
   Copilot will segment the Methods section differently, so aligning by
   step index would compare noise; comparing the *sets* of services each
   one named is the stable unit.
5. **Report**: a ground-truth-aware synthesis (not a raw tool dump) written
   to `report.md`.

## Files per PMID (`work/judge_runs/<pmid>/`)

| File | What it is |
|---|---|
| `unmasked.claude.json` | Claude's step->service JSON, unmasked paper |
| `unmasked.copilot.json` | Copilot's step->service JSON, unmasked paper |
| `masked.claude.json` | Same, masked paper - **absent if masking was a no-op for this PMID** |
| `masked.copilot.json` | Same, masked paper - absent under the same condition |
| `unmasked.copilot.raw.txt` | Present only when the manual Copilot-UI fallback was used: Copilot's raw pasted reply before `--manual-response` parsed it |
| `unmasked.claude_vs_copilot_bullets.md` | Intermediate: raw bullet-point Claude-vs-Copilot comparison (no ground truth). Scratch for building the report, not the deliverable. |
| `masked.claude_vs_copilot_bullets.md` | Same, masked run - absent if masking was a no-op |
| `unmasked.overlap.json` | Machine-readable 3-way overlap (Claude/Copilot/CSV key sets, Jaccard, breakdown) |
| `masked.overlap.json` | Same, masked run - absent if masking was a no-op |
| `report.md` | **The deliverable.** Ground-truth-aware synthesis with numeric overlap tables, one section per active run, plus a masked-vs-unmasked read if both ran. |

## Reading `report.md`

The headline numbers are the three Jaccard scores (Claude vs. Copilot,
Claude vs. CSV, Copilot vs. CSV) and the three-way agreement set. A high
Claude/Copilot Jaccard with a low */CSV Jaccard means the two models agree
with each other but not with the keyword-mined ground truth - worth
reading the CSV's caveats
([bv-brc-methods-mined-csv-schema.md](../../references/bv-brc-methods-mined-csv-schema.md))
before concluding either model is wrong, since the CSV is keyword-matched,
not NLP-confirmed, and can itself miss a plainly-described service or
false-positive on a background mention.

Any name either model produced that didn't resolve to one of the 43 CSV
keys is reported as "unresolved," never silently dropped - it means there's
no ground truth to judge that specific claim against, not that the claim
is wrong.
