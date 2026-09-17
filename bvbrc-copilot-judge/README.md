# bvbrc-copilot-judge

Stage-1 AI-judge pipeline for the BV-BRC Copilot workflow-automation
benchmark: for a given paper (PMID), query **BV-BRC Copilot** and
**Claude** independently for a step->BV-BRC-service JSON reconstruction
of the Methods section, score both against a keyword-mined ground-truth
CSV (43 BV-BRC/PATRIC services), and report a numeric 3-way overlap
(Claude vs. Copilot vs. CSV).

The pipeline also runs a **masked** variant of each paper (service names
redacted to `[MASKED-SERVICE]`) to check whether Copilot is recognizing a
method *by what it does* or just copying a name that's already sitting on
the page.

This is a standalone extraction of the judge pipeline originally built in
the codeathon prep repo - self-contained here with its own `uv` project,
scripts, ground-truth data, and Claude Code skills.

## Setup

```bash
uv sync
cp .env.example .env
# edit .env and set BVBRC_TOKEN to your BV-BRC auth token
```

`BVBRC_TOKEN` is required for any live Copilot API call
(`scripts/query_copilot_stage1.py` fails fast with a clear message if it's
unset). `COPILOT_API_URL` and `COPILOT_MODEL` are optional overrides - see
`.env.example` for their defaults.

## Populating the paper corpus

`references/papers/` and `references/papers_masked/` are not checked into
this repo (large, regenerable). Populate them before judging any PMID:

```bash
uv run python3 scripts/mine_bvbrc_methods.py     # -> references/papers/<pmid>.txt
uv run python3 scripts/mask_bvbrc_terms.py        # -> references/papers_masked/<pmid>.txt
```

The miner reads `references/cite-bv-brc.csv` (the paper list, already
included) and pulls full text from the NCBI BioC API. It also (re)writes
`references/bv-brc-methods-mined.csv`, the ground-truth file - already
included here, so you don't need to re-run the miner unless you're
extending the paper list or regenerating the corpus text. Column format is
documented in `references/bv-brc-methods-mined-csv-schema.md`.

## Running the full pipeline (recommended): via the Claude Code skill

With this folder open in Claude Code, invoke the `bvbrc-copilot-judge`
skill with a PMID that has a cached paper at
`references/papers/<pmid>.txt`, e.g.:

> Run the bvbrc-copilot-judge skill on PMID 37948307

Claude will orchestrate the full pipeline end to end per
[`.claude/skills/bvbrc-copilot-judge/SKILL.md`](.claude/skills/bvbrc-copilot-judge/SKILL.md):
query Copilot, read the paper itself and independently produce the same
JSON, score both against the ground truth, compute 3-way overlap, and
write `work/judge_runs/<pmid>/report.md` as the deliverable.

## Running the pipeline manually (without the skill)

Each stage is a standalone script if you want to drive it by hand or
script it further:

```bash
mkdir -p work/judge_runs/<pmid>

# 1. Query Copilot (live API)
uv run python3 scripts/query_copilot_stage1.py \
  --paper references/papers/<pmid>.txt \
  --out work/judge_runs/<pmid>/unmasked.copilot.json

# 2. Claude's own read: have Claude read references/papers/<pmid>.txt and
#    produce the same step->service JSON shape, following the prompt in
#    scripts/query_copilot_stage1.py's PROMPT_TEMPLATE (or use the
#    compare-with-copilot skill's prompt directly in Claude's UI, attaching
#    the paper as a file). Save the result to
#    work/judge_runs/<pmid>/unmasked.claude.json

# 3. Score each model against ground truth
uv run python3 scripts/score_stage1_json.py work/judge_runs/<pmid>/unmasked.claude.json \
  --pmid <pmid> --run unmasked
uv run python3 scripts/score_stage1_json.py work/judge_runs/<pmid>/unmasked.copilot.json \
  --pmid <pmid> --run unmasked

# 4. Compute 3-way overlap
uv run python3 scripts/judge_overlap.py \
  --pmid <pmid> --run unmasked \
  --claude work/judge_runs/<pmid>/unmasked.claude.json \
  --copilot work/judge_runs/<pmid>/unmasked.copilot.json \
  --out work/judge_runs/<pmid>/unmasked.overlap.json
```

Repeat steps 1-4 against `references/papers_masked/<pmid>.txt` (writing to
`masked.*` filenames) if `diff -q references/papers/<pmid>.txt
references/papers_masked/<pmid>.txt` shows a difference - if the files are
identical, masking is a no-op for that paper and the masked run adds
nothing.

## Manual Copilot-UI fallback mode

If the live Copilot API is down or you don't have a `BVBRC_TOKEN`, you can
still run the pipeline by getting Copilot's answer through its web UI by
hand and feeding the raw reply back into the same scoring pipeline:

```bash
# 1. Print the exact prompt Copilot would have been sent
uv run python3 scripts/query_copilot_stage1.py \
  --paper references/papers/<pmid>.txt --print-prompt

# 2. Paste that prompt into the BV-BRC Copilot chat UI in your browser.

# 3. Save Copilot's raw reply text to a file, e.g.:
#    work/judge_runs/<pmid>/unmasked.copilot.raw.txt

# 4. Parse it through the same validation/output path the live call uses
uv run python3 scripts/query_copilot_stage1.py \
  --paper references/papers/<pmid>.txt \
  --manual-response work/judge_runs/<pmid>/unmasked.copilot.raw.txt \
  --out work/judge_runs/<pmid>/unmasked.copilot.json
```

From here, `unmasked.copilot.json` is identical in shape and downstream
usage to a live-API result - continue with steps 3-4 of the manual
pipeline above (scoring and overlap) exactly as if the API call had
succeeded. This is the same fallback the `bvbrc-copilot-judge` skill uses
automatically when it detects the live API is unavailable.

## Output layout

Each judged PMID gets its own `work/judge_runs/<pmid>/` directory; see
[`work/judge_runs/README.md`](work/judge_runs/README.md) for the full
per-file contract and how to read `report.md`'s headline numbers. Nothing
under `work/judge_runs/` is checked into git - it's regenerated per run.

## Layout

```
.claude/skills/
  bvbrc-copilot-judge/SKILL.md   # orchestrates the full pipeline
  compare-with-copilot/SKILL.md  # Claude's own-read prompt (also usable standalone in Claude's chat UI)
scripts/
  query_copilot_stage1.py        # queries BV-BRC Copilot (live API + manual-UI fallback)
  score_stage1_json.py           # scores one model's JSON against the ground-truth CSV
  judge_overlap.py               # 3-way Claude/Copilot/CSV overlap
  mine_bvbrc_methods.py          # builds the paper corpus + ground-truth CSV from cite-bv-brc.csv
  mask_bvbrc_terms.py            # produces references/papers_masked/ from references/papers/
references/
  bv-brc-methods-mined.csv           # ground truth (43 services x paper)
  bv-brc-methods-mined-csv-schema.md # column documentation
  cite-bv-brc.csv                    # source paper list for the miner
  papers/, papers_masked/            # generated corpus (gitignored)
work/judge_runs/                     # per-PMID run output (gitignored)
```
