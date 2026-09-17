---
name: bvbrc-copilot-judge
description: Run the full stage-1 AI-judge pipeline for one paper (PMID) - query BV-BRC Copilot and Claude independently for step->BV-BRC-service JSON, score both against the mined-CSV ground truth, and report 3-way overlap. Use when asked to "judge," "grade," or "benchmark" Copilot against Claude and the ground truth on a specific paper.
---

# Purpose

Orchestrates the stage-1 leg of a two-stage benchmark design end to end for
a single PMID: get Copilot's and Claude's independent step->service JSON for
the paper (unmasked, and masked if masking actually changed the text),
score each against [bv-brc-methods-mined.csv](../../../references/bv-brc-methods-mined.csv)
(43 services), and produce a ground-truth-aware comparison report with
numeric 3-way overlap.

The benchmark idea in one line: compare whether Copilot recognizes a
BV-BRC service from its *function* in a paper's Methods section, or is
just pattern-matching on the service's name appearing verbatim in the
text - the masked run redacts service names to test which one it's doing.

This wraps three existing pieces rather than reimplementing them:
- [compare-with-copilot](../compare-with-copilot/SKILL.md) -
  the Claude-vs-Copilot bullet-comparison prompt (used here as the source
  of Claude's own read and the raw comparison bullets, not as a
  standalone entry point).
- [scripts/score_stage1_json.py](../../../scripts/score_stage1_json.py) - scores
  one model's JSON against the CSV.
- [scripts/judge_overlap.py](../../../scripts/judge_overlap.py) - the 3-way
  Claude/Copilot/CSV set-overlap metric this skill adds on top.

Full pipeline rationale, file layout, and how to read the outputs:
[work/judge_runs/README.md](../../../work/judge_runs/README.md) - read it once if
this is your first time running this skill.

# Invocation

Takes one PMID. The paper's full text must already exist at
`references/papers/<pmid>.txt` (see
[scripts/mine_bvbrc_methods.py](../../../scripts/mine_bvbrc_methods.py), which
populates `references/papers/` from `references/cite-bv-brc.csv`). If it
doesn't, run the miner first (or fetch that paper's text yourself into
`references/papers/<pmid>.txt`) - this skill does not fetch new papers.

Requires `BVBRC_TOKEN`, read from the environment or a `.env` file in the
working directory via `python-dotenv`
([scripts/query_copilot_stage1.py](../../../scripts/query_copilot_stage1.py) loads
it automatically and fails with a clear message if it's unset either way).
Copy `.env.example` to `.env` and fill it in before your first run.

# Steps

1. **Set up the output directory.** `work/judge_runs/<pmid>/` (create if
   missing).

2. **Masking no-op check.** `diff -q references/papers/<pmid>.txt
   references/papers_masked/<pmid>.txt`. If identical, this paper has no
   maskable BV-BRC/PATRIC service terms in it - skip the masked run
   entirely for every step below, and record `"masking": "no-op"` in the
   final report instead of a masked-run section. If different, both
   `unmasked` and `masked` runs proceed for every step below. If
   `references/papers_masked/<pmid>.txt` doesn't exist yet, run
   `python3 scripts/mask_bvbrc_terms.py` first to populate it from
   `references/papers/`.

3. **Query Copilot**, once per active run:
   ```
   python3 scripts/query_copilot_stage1.py \
     --paper references/papers/<pmid>.txt \
     --out work/judge_runs/<pmid>/unmasked.copilot.json
   # and, if masked run is active:
   python3 scripts/query_copilot_stage1.py \
     --paper references/papers_masked/<pmid>.txt \
     --out work/judge_runs/<pmid>/masked.copilot.json
   ```
   If this fails (bad token, HTTP error, no JSON array in the response),
   stop and surface the error - don't fabricate a Copilot answer to keep
   going.

   **If the live API is down** and the user offers to supply Copilot's
   answer themselves: get the exact prompt with `--print-prompt` (no
   `--out` needed), have the user run it through the BV-BRC Copilot UI
   directly and paste the raw response into a text file, then pass that
   file via `--manual-response` in place of the live query - same `--out`
   contract either way, so every downstream step is unaffected:
   ```
   python3 scripts/query_copilot_stage1.py --paper references/papers/<pmid>.txt --print-prompt
   # user pastes the prompt into Copilot's UI, saves the raw reply to
   # work/judge_runs/<pmid>/unmasked.copilot.raw.txt
   python3 scripts/query_copilot_stage1.py \
     --paper references/papers/<pmid>.txt \
     --manual-response work/judge_runs/<pmid>/unmasked.copilot.raw.txt \
     --out work/judge_runs/<pmid>/unmasked.copilot.json
   ```

4. **Claude's own read**, once per active run. Read
   `references/papers/<pmid>.txt` (and `references/papers_masked/<pmid>.txt`
   if masked is active) yourself and produce the same step->service JSON
   Copilot was asked for, using the identical 43-service list, feasibility
   gate, and output rules from
   [scripts/query_copilot_stage1.py](../../../scripts/query_copilot_stage1.py)'s
   `PROMPT_TEMPLATE` (same list and same organism-feasibility judgment
   Copilot was given, so the two are comparable) - do this as your own
   independent read of the Methods section, not by looking at Copilot's
   output first. Apply the feasibility gate yourself: first judge whether
   BV-BRC could realistically analyze data from the paper's organism(s)
   before matching any step, and set `bv_brc_service` to `null` for every
   step whose organism isn't feasible, even if the step's method
   resembles a listed service by function. Save each to
   `work/judge_runs/<pmid>/unmasked.claude.json` /
   `masked.claude.json`.

5. **Raw bullet comparison** (intermediate artifact, per run). Compare
   your JSON against Copilot's the way
   [compare-with-copilot](../compare-with-copilot/SKILL.md)
   does - a bullet-point list of where they agree, where they diverge, and
   why (different segmentation vs. genuinely different service choice).
   Save to `work/judge_runs/<pmid>/unmasked.claude_vs_copilot_bullets.md`
   (and `masked...` if active). This is scratch for building the final
   report, not the deliverable - don't spend excess effort polishing it.

6. **Score each model against ground truth**, once per model per active run:
   ```
   python3 scripts/score_stage1_json.py work/judge_runs/<pmid>/unmasked.claude.json \
     --pmid <pmid> --run unmasked
   python3 scripts/score_stage1_json.py work/judge_runs/<pmid>/unmasked.copilot.json \
     --pmid <pmid> --run unmasked
   # + masked.* variants if active
   ```

7. **Compute 3-way overlap**, once per active run:
   ```
   python3 scripts/judge_overlap.py \
     --pmid <pmid> --run unmasked \
     --claude work/judge_runs/<pmid>/unmasked.claude.json \
     --copilot work/judge_runs/<pmid>/unmasked.copilot.json \
     --out work/judge_runs/<pmid>/unmasked.overlap.json
   # + masked variant if active
   ```

8. **Write the final report**, `work/judge_runs/<pmid>/report.md`. This is
   the deliverable - synthesize, don't just concatenate the tool output:
   - One section per active run (unmasked, masked), each with:
     - The `judge_overlap.py` breakdown as a table (all-three-agree,
       claude+copilot-only, claude+csv-only, copilot+csv-only,
       claude-only, copilot-only, csv-only), plus the four Jaccard numbers.
     - Any `claude_unresolved`/`copilot_unresolved` names, explicitly
       labeled "no ground truth available for this name" - never silently
       dropped.
     - A short prose read of what the breakdown means for this paper
       (e.g. "Copilot named 2 services CSV keyword-matching doesn't
       confirm - Genome Alignment and BLAST - both plausible given the
       Methods text; Claude and Copilot agree on 5 of 7 CSV-documented
       services").
   - If masking was a no-op, say so plainly instead of a masked section.
   - A closing note on what the masked-vs-unmasked gap (if both ran)
     suggests about whether Copilot's stage-1 skill is name-copying vs.
     genuine service recognition, per the benchmark idea in the Purpose
     section above.
   Do not write OKF frontmatter on this file - `work/` is scratch, not a
   canonical deliverable.

9. **Tell the user** where `report.md` landed and give a one-paragraph
   summary of the headline numbers - don't just say "done."
