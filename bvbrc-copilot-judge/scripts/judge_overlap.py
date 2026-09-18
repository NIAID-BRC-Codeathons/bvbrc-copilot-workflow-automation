#!/usr/bin/env python3
"""Compute the 3-way set overlap (Claude / Copilot / CSV ground truth) for one
stage-1 judge run, as used by the bvbrc-copilot-judge skill
(.claude/skills/bvbrc-copilot-judge/SKILL.md).

Resolves both models' freeform bv_brc_service names onto the CSV's service
keys via score_stage1_json.py's alias table (now covering all 43 services,
see references/bv-brc-methods-mined-csv-schema.md), then reports Jaccard
overlap and an agree/only-X breakdown across all three sets. A raw name that
resolves to nothing is kept in its own "unresolved" bucket per model and
reported explicitly rather than silently dropped, since it has no ground
truth to be judged against.

Usage:
    python3 scripts/judge_overlap.py \
        --pmid 37098958 --run unmasked \
        --claude work/judge_runs/37098958/unmasked.claude.json \
        --copilot work/judge_runs/37098958/unmasked.copilot.json \
        --out work/judge_runs/37098958/unmasked.overlap.json
"""
import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from score_stage1_json import (  # noqa: E402
    CSV_PATH, load_csv_rows, csv_hits, load_predictions, resolve_service,
)


def resolve_all(predictions):
    """Return (resolved_key_set, unresolved_raw_names, detail_list)."""
    keys = set()
    unresolved = []
    detail = []
    for item in predictions:
        raw = item.get("bv_brc_service")
        key, method = resolve_service(raw)
        detail.append({
            "step_description": item.get("step_description"),
            "raw_service": raw,
            "resolved_key": key,
            "match_method": method,
        })
        if key:
            keys.add(key)
        elif raw is not None:
            unresolved.append(raw)
    return keys, unresolved, detail


def jaccard(a, b):
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def compute_overlap(pmid, claude_predictions, copilot_predictions, csv_rows):
    row = csv_rows.get(str(pmid))
    if row is None:
        raise KeyError(f"pmid {pmid} not found in {CSV_PATH}")
    csv_keys = csv_hits(row)

    claude_keys, claude_unresolved, claude_detail = resolve_all(claude_predictions)
    copilot_keys, copilot_unresolved, copilot_detail = resolve_all(copilot_predictions)

    all_three = claude_keys & copilot_keys & csv_keys
    claude_copilot_not_csv = (claude_keys & copilot_keys) - csv_keys
    claude_csv_not_copilot = (claude_keys & csv_keys) - copilot_keys
    copilot_csv_not_claude = (copilot_keys & csv_keys) - claude_keys
    claude_only = claude_keys - copilot_keys - csv_keys
    copilot_only = copilot_keys - claude_keys - csv_keys
    csv_only = csv_keys - claude_keys - copilot_keys

    return {
        "pmid": str(pmid),
        "csv_keys": sorted(csv_keys),
        "claude_keys": sorted(claude_keys),
        "copilot_keys": sorted(copilot_keys),
        "claude_unresolved": claude_unresolved,
        "copilot_unresolved": copilot_unresolved,
        "jaccard": {
            "claude_vs_copilot": round(jaccard(claude_keys, copilot_keys), 3),
            "claude_vs_csv": round(jaccard(claude_keys, csv_keys), 3),
            "copilot_vs_csv": round(jaccard(copilot_keys, csv_keys), 3),
            "three_way": round(
                len(claude_keys & copilot_keys & csv_keys)
                / len(claude_keys | copilot_keys | csv_keys or {1}),
                3,
            ) if (claude_keys | copilot_keys | csv_keys) else 1.0,
        },
        "breakdown": {
            "all_three_agree": sorted(all_three),
            "claude_and_copilot_only": sorted(claude_copilot_not_csv),
            "claude_and_csv_only": sorted(claude_csv_not_copilot),
            "copilot_and_csv_only": sorted(copilot_csv_not_claude),
            "claude_only": sorted(claude_only),
            "copilot_only": sorted(copilot_only),
            "csv_only": sorted(csv_only),
        },
        "claude_detail": claude_detail,
        "copilot_detail": copilot_detail,
    }


def print_summary(result, run_label=None):
    label = f" ({run_label})" if run_label else ""
    j = result["jaccard"]
    b = result["breakdown"]
    print(f"pmid {result['pmid']}{label}")
    print(f"  claude keys:   {', '.join(result['claude_keys']) or '(none)'}")
    print(f"  copilot keys:  {', '.join(result['copilot_keys']) or '(none)'}")
    print(f"  csv keys:      {', '.join(result['csv_keys']) or '(none)'}")
    print(f"  jaccard  claude/copilot={j['claude_vs_copilot']}  "
          f"claude/csv={j['claude_vs_csv']}  copilot/csv={j['copilot_vs_csv']}  "
          f"three-way={j['three_way']}")
    print(f"  all three agree:       {', '.join(b['all_three_agree']) or '(none)'}")
    print(f"  claude+copilot only:   {', '.join(b['claude_and_copilot_only']) or '(none)'}")
    print(f"  claude+csv only:       {', '.join(b['claude_and_csv_only']) or '(none)'}")
    print(f"  copilot+csv only:      {', '.join(b['copilot_and_csv_only']) or '(none)'}")
    print(f"  claude only:           {', '.join(b['claude_only']) or '(none)'}")
    print(f"  copilot only:          {', '.join(b['copilot_only']) or '(none)'}")
    print(f"  csv only (both missed):{', '.join(b['csv_only']) or '(none)'}")
    if result["claude_unresolved"]:
        print(f"  claude unresolved (no ground truth): {', '.join(repr(n) for n in result['claude_unresolved'])}")
    if result["copilot_unresolved"]:
        print(f"  copilot unresolved (no ground truth): {', '.join(repr(n) for n in result['copilot_unresolved'])}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pmid", required=True)
    ap.add_argument("--claude", required=True, help="Path to Claude's step->service JSON")
    ap.add_argument("--copilot", required=True, help="Path to Copilot's step->service JSON")
    ap.add_argument("--run", choices=["masked", "unmasked"], help="Label for this run, shown in the summary")
    ap.add_argument("--csv", default=CSV_PATH)
    ap.add_argument("--out", help="Write the full JSON result here")
    args = ap.parse_args()

    csv_rows = load_csv_rows(args.csv)
    claude_predictions = load_predictions(args.claude)
    copilot_predictions = load_predictions(args.copilot)

    result = compute_overlap(args.pmid, claude_predictions, copilot_predictions, csv_rows)
    print_summary(result, args.run)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
