#!/usr/bin/env python3
"""Run the stage-1 method->BV-BRC-service prompt against BV-BRC Copilot's
/copilot-agent SSE endpoint, for one paper, and save the resulting JSON array.

Uses the placeholder-style prompt from documents/p6-stage1-copilot-prompt.md
("Prompt" section, not the "Prompt modified" attached-file variant used by
the .claude/skills/compare-with-copilot skill) with the paper's full text
spliced in, since prompt_copilot.py's /copilot-agent call has no file-upload
mechanism -- only a plain text "query" field.

Usage:
    # BVBRC_TOKEN is read from the environment or a .env file in the
    # working directory (via python-dotenv); export it directly if you'd
    # rather not use a .env file.
    python3 scripts/query_copilot_stage1.py \
        --paper references/papers/37098958.txt \
        --out work/judge_runs/37098958/unmasked.copilot.json

    # If the live API is unavailable, paste Copilot's raw response
    # (from the BV-BRC Copilot UI, run against the same prompt this
    # script would have sent -- see --print-prompt) into a text file and
    # pass it here instead. Runs the same JSON extraction and shape
    # validation as the live path; no network call is made.
    python3 scripts/query_copilot_stage1.py \
        --paper references/papers/37098958.txt \
        --manual-response work/judge_runs/37098958/unmasked.copilot.raw.txt \
        --out work/judge_runs/37098958/unmasked.copilot.json

    # To get the exact prompt to paste into the Copilot UI:
    python3 scripts/query_copilot_stage1.py --paper references/papers/37098958.txt --print-prompt
"""
import argparse
import json
import os
import re
import sys
import uuid

import requests  # pip install requests
from dotenv import load_dotenv  # pip install python-dotenv

load_dotenv()

BASE_URL = os.environ.get(
    "COPILOT_API_URL",
    "https://dev-6.bv-brc.org/copilot-api/chatbrc",
)
TOKEN = os.environ.get("BVBRC_TOKEN", "")
MODEL = os.environ.get("COPILOT_MODEL", "Qwen/Qwen3.6-35B-A3B")

PROMPT_TEMPLATE = """You are analyzing the Methods section of a scientific paper to identify
which BV-BRC (Bacterial and Viral Bioinformatics Resource Center) service
was used, or could have been used, to carry out each computational step
described.

Before matching individual steps, first think about what organism(s) the
paper's dataset comes from, and use your own knowledge of BV-BRC to judge
whether data from that organism could actually be analyzed in BV-BRC at
all. If the dataset is not something BV-BRC could realistically handle,
set every step's "bv_brc_service" to `null`, regardless of how closely a
step's method resembles a listed service by function. If the paper covers
multiple organisms and only some of them are feasible in BV-BRC, apply
this judgment per step, based on which organism that specific step's data
belongs to.

Read the Methods section below. For each distinct computational or
analytical step, decide which single BV-BRC service best corresponds to
it — subject to the feasibility judgment above — if any of the following
apply:

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
  {{ "step_description": "...", "bv_brc_service": "..." }}
]

Rules:
- One object per distinct step in the Methods section, in the order the
  steps appear.
- "step_description" is a short, one-sentence description of what the
  authors did, in your own words, based on what the step accomplishes
  (e.g. "assembled paired-end Illumina reads into a draft genome") -- not
  a restatement of a tool name found in the text.
- "bv_brc_service" is the single best-matching name from the list above,
  copied verbatim, or the JSON value `null` if no service on the list
  applies to that step. Always include the key, even when its value is
  `null`.
- Base the match on what the step does, not on whether a matching name
  literally appears in the text -- infer the service from the method
  description itself.
- Do not invent steps that aren't in the Methods section, and do not
  merge multiple distinct steps into one entry.
- Never match a step to a service just because the underlying
  algorithm/method is generic (e.g., k-mer counting, BLAST, read
  alignment) if you judged that BV-BRC could not actually analyze data
  from that organism -- see the feasibility judgment above.

Paper:
{paper_text}
"""


def build_prompt(paper_text: str) -> str:
    return PROMPT_TEMPLATE.format(paper_text=paper_text)


def query_copilot(prompt: str) -> str:
    """Send the prompt to /copilot-agent, stream the SSE response, return the
    concatenated final_response text."""
    if not TOKEN:
        sys.exit("Error: set BVBRC_TOKEN env var to your BV-BRC auth token.")

    url = f"{BASE_URL}/copilot-agent"
    session_id = str(uuid.uuid4())
    payload = {
        "query": prompt,
        "model": MODEL,
        "session_id": session_id,
        "stream": True,
        "save_chat": False,
        "include_history": False,
    }
    headers = {"Authorization": TOKEN, "Content-Type": "application/json"}

    chunks = []
    with requests.post(url, json=payload, headers=headers, stream=True, timeout=600) as resp:
        if resp.status_code != 200:
            sys.exit(f"HTTP {resp.status_code}: {resp.text}")

        event_type = None
        data_buf = ""
        for raw_line in resp.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            if raw_line.startswith(":"):
                continue
            if raw_line.startswith("event:"):
                event_type = raw_line[len("event:"):].strip()
                continue
            if raw_line.startswith("data:"):
                data_buf += raw_line[len("data:"):].strip()
                continue
            if raw_line == "" and event_type:
                _handle_event(event_type, data_buf, chunks)
                event_type = None
                data_buf = ""

    return "".join(chunks)


def _handle_event(event_type, raw_data, chunks):
    try:
        data = json.loads(raw_data) if raw_data else {}
    except json.JSONDecodeError:
        data = {"_raw": raw_data}

    if event_type == "final_response":
        chunks.append(data.get("chunk", ""))
    elif event_type == "error":
        print(f"[error] {data.get('error', data)}", file=sys.stderr)
    elif event_type in ("tool_selected", "tool_executed", "queued"):
        print(f"[{event_type}] {data}", file=sys.stderr)


def extract_json_array(text: str):
    """Pull the JSON array out of Copilot's response, tolerating stray
    markdown fences or commentary the model wasn't supposed to add."""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON array found in Copilot's response:\n{text[:1000]}")
    return json.loads(match.group(0))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paper", required=True, help="Path to the paper's plain-text file")
    ap.add_argument("--out", help="Where to write the extracted JSON array")
    ap.add_argument(
        "--manual-response",
        help=(
            "Path to a text file containing Copilot's raw response, pasted "
            "in manually (e.g. from the BV-BRC Copilot UI) instead of "
            "querying the live API. Skips the network call entirely."
        ),
    )
    ap.add_argument(
        "--print-prompt",
        action="store_true",
        help="Print the exact prompt for --paper to stdout and exit, without querying anything.",
    )
    args = ap.parse_args()

    with open(args.paper, encoding="utf-8") as f:
        paper_text = f.read()

    prompt = build_prompt(paper_text)

    if args.print_prompt:
        print(prompt)
        return

    if not args.out:
        sys.exit("error: --out is required unless --print-prompt is given")

    if args.manual_response:
        with open(args.manual_response, encoding="utf-8") as f:
            raw_response = f.read()
    else:
        raw_response = query_copilot(prompt)

    try:
        data = extract_json_array(raw_response)
    except (ValueError, json.JSONDecodeError) as e:
        sys.exit(f"error: {e}")

    for item in data:
        if not isinstance(item, dict) or "step_description" not in item or "bv_brc_service" not in item:
            sys.exit(f"error: malformed item in Copilot's JSON output: {item!r}")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {args.out} ({len(data)} steps)", file=sys.stderr)


if __name__ == "__main__":
    main()
