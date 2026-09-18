#!/usr/bin/env python3
"""Score a Copilot stage-1 JSON output against bv-brc-methods-mined.csv.

Implements stage 1's leg 1 ("programmatic diff against the CSV") from
documents/p6-stage1-stage2-benchmark-design.md: normalizes Copilot's
freeform bv_brc_service names onto the CSV's 18 service keys via a static
alias table, then diffs against which services the CSV has a strong/
general keyword hit for on that paper, reporting two buckets:

- misses       - CSV has a hit for a service Copilot's JSON never named
- unsupported  - Copilot named a service the CSV has no hit for

Names that don't resolve to any of the 18 keys are reported separately as
"unresolved" (per the design: "not treated as an error").

Usage:
    # single Copilot output file, scored against one paper
    python3 scripts/score_stage1_json.py copilot_output.json --pmid 36525447 --run masked

    # a directory of output files, filenames like <pmid>.json,
    # <pmid>_masked.json, <pmid>-unmasked.json ...
    python3 scripts/score_stage1_json.py results/ --batch --out-csv summary.csv
"""
import argparse
import csv
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BUNDLE_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)
from mine_bvbrc_methods import SERVICES  # noqa: E402

CSV_PATH = os.path.join(BUNDLE_ROOT, "references", "bv-brc-methods-mined.csv")
SERVICE_KEYS = list(SERVICES.keys())

# Extra paraphrases beyond the labels/strong-terms already in SERVICES,
# covering how a model is likely to phrase a service name in freeform text
# (including the exact names used in documents/p6-stage1-copilot-prompt.md).
EXTRA_ALIASES = {
    "genome annotation service": "annotation",
    "rast": "annotation",
    "rast tool kit": "annotation",
    "genome assembly": "assembly",
    "assembly service": "assembly",
    "comprehensive genome analysis service": "cga",
    "cga": "cga",
    "similar genome finder service": "sgf",
    "proteome comparison service": "proteome_cmp",
    "variation analysis": "variation",
    "snp calling": "variation",
    "variant calling": "variation",
    "metagenomic binning": "metagenomics",
    "metagenomic read mapping": "metagenomics",
    "read mapping": "metagenomics",
    "rna-seq analysis": "rnaseq",
    "rnaseq analysis": "rnaseq",
    "transcriptomics analysis service": "rnaseq",
    "differential expression": "rnaseq",
    "phylogenetic tree building": "phylo",
    "phylogenetic tree building service": "phylo",
    "codon tree": "phylo",
    "gene tree": "phylo",
    "crispr finder service": "crispr",
    "subsystems analysis": "subsystems",
    "subsystem analysis": "subsystems",
    "specialty genes service": "specialty_genes",
    "amr phenotype prediction service": "amr",
    "antimicrobial resistance phenotype prediction": "amr",
    "taxonomic classification": "taxclass",
    "docking": "docking",
    "protein family sorter service": "pfs",
    "pathway analysis": "pathway",
    "comparative pathway analysis": "pathway",
    "comparative pathway": "pathway",
    "p3-tools": "p3tools",
    "patric cli": "p3tools",
    "patric command line": "p3tools",
    "patric command line interface": "p3tools",
    "bv-brc data api": "p3tools",
    "patric data api": "p3tools",
    "data api": "p3tools",
    "primer design service": "primer_design",
    "genome alignment service": "genome_alignment",
    "tn-seq analysis": "tnseq",
    "tnseq analysis": "tnseq",
    "transposon insertion sequencing": "tnseq",
    "bacterial genome tree": "bact_genome_tree",
    "bacterial genome tree service": "bact_genome_tree",
    "viral genome tree": "viral_genome_tree",
    "viral genome tree service": "viral_genome_tree",
    "core genome mlst": "cgmlst",
    "core genome mlst service": "cgmlst",
    "whole genome snp analysis": "wg_snp",
    "whole-genome snp analysis": "wg_snp",
    "msa and snp analysis": "msa_snp",
    "meta-cats": "metacats",
    "protein structure prediction": "protein_structure",
    "protein structure prediction service": "protein_structure",
    "protein stability prediction": "protein_stability",
    "protein stability prediction service": "protein_stability",
    "comparative systems": "comparative_systems",
    "comparative systems service": "comparative_systems",
    "mobile element detection": "mobile_element",
    "mobile genetic element detection": "mobile_element",
    "expression import": "expression_import",
    "expression import service": "expression_import",
    "fastq utilities": "fastq_utils",
    "id mapper": "id_mapper",
    "sars-cov-2 genome analysis": "sarscov2_genome",
    "sars-cov-2 genome analysis service": "sarscov2_genome",
    "sars-cov-2 wastewater analysis": "sarscov2_wastewater",
    "influenza sequence submission": "flu_submission",
    "influenza ha subtype conversion": "flu_ha_subtype",
    "influenza reassortment analysis": "flu_reassortment",
    "subspecies classification": "subspecies",
    "subspecies classification service": "subspecies",
    "viral assembly": "viral_assembly",
    "viral assembly service": "viral_assembly",
    "outbreak tracker": "outbreak_tracker",
}


def normalize(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def build_alias_map():
    alias_map = {}
    for key, (label, strong_terms, _general_terms) in SERVICES.items():
        names = {label, key}
        for part in re.split(r"[/,]", label):
            names.add(part.strip())
        names.update(strong_terms)
        for n in names:
            norm = normalize(n)
            if norm:
                alias_map.setdefault(norm, key)
    for name, key in EXTRA_ALIASES.items():
        alias_map.setdefault(normalize(name), key)
    return alias_map


ALIAS_MAP = build_alias_map()


def resolve_service(raw_name):
    """Return (service_key_or_None, match_method) for a freeform service name."""
    if raw_name is None:
        return None, "null"
    norm = normalize(str(raw_name))
    if not norm:
        return None, "empty"
    if norm in ALIAS_MAP:
        return ALIAS_MAP[norm], "exact"
    # fuzzy: longest alias contained in (or containing) the predicted name
    best_key, best_alias, best_len = None, None, -1
    for alias, key in ALIAS_MAP.items():
        if alias in norm or norm in alias:
            if len(alias) > best_len:
                best_key, best_alias, best_len = key, alias, len(alias)
    if best_key:
        return best_key, f"fuzzy:{best_alias}"
    return None, "no_csv_match"


def load_csv_rows(csv_path):
    rows = {}
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows[row["pmid"]] = row
    return rows


def csv_hits(row):
    """Set of service keys with a strong or general hit for this paper."""
    hits = set()
    for key in SERVICE_KEYS:
        strong = int(row.get(f"{key}_strong") or 0)
        general = int(row.get(f"{key}_general") or 0)
        if strong + general > 0:
            hits.add(key)
    return hits


def load_predictions(json_path):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{json_path}: expected a JSON array, got {type(data).__name__}")
    for item in data:
        if not isinstance(item, dict) or "step_description" not in item or "bv_brc_service" not in item:
            raise ValueError(
                f"{json_path}: each item must be an object with "
                f"'step_description' and 'bv_brc_service' keys, got {item!r}"
            )
    return data


def score(pmid, predictions, csv_rows):
    row = csv_rows.get(str(pmid))
    if row is None:
        raise KeyError(
            f"pmid {pmid} not found in {CSV_PATH} "
            f"(no retrievable full text, or not part of the mined corpus)"
        )
    hits = csv_hits(row)

    predicted_keys = set()
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
            predicted_keys.add(key)
        elif raw is not None:
            unresolved.append(raw)

    return {
        "pmid": str(pmid),
        "n_steps": len(predictions),
        "csv_hits": sorted(hits),
        "predicted_keys": sorted(predicted_keys),
        "misses": sorted(hits - predicted_keys),
        "unsupported": sorted(predicted_keys - hits),
        "unresolved_names": unresolved,
        "detail": detail,
    }


def print_summary(result, run_label=None):
    label = f" ({run_label})" if run_label else ""
    print(f"pmid {result['pmid']}{label}: {result['n_steps']} steps")
    print(f"  csv hits:      {', '.join(result['csv_hits']) or '(none)'}")
    print(f"  predicted:     {', '.join(result['predicted_keys']) or '(none)'}")
    print(f"  misses:        {', '.join(result['misses']) or '(none)'}")
    print(f"  unsupported:   {', '.join(result['unsupported']) or '(none)'}")
    if result["unresolved_names"]:
        print(f"  unresolved:    {', '.join(repr(n) for n in result['unresolved_names'])}")


FILENAME_RE = re.compile(r"^(\d+)(?:[_-]?(masked|unmasked))?$", re.IGNORECASE)


def infer_pmid_run(filename):
    stem = os.path.splitext(filename)[0]
    m = FILENAME_RE.match(stem)
    if not m:
        return None, None
    return m.group(1), (m.group(2).lower() if m.group(2) else None)


def run_single(json_path, pmid, run_label, csv_rows, out_path):
    predictions = load_predictions(json_path)
    result = score(pmid, predictions, csv_rows)
    print_summary(result, run_label)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Wrote {out_path}", file=sys.stderr)


def run_batch(dir_path, csv_rows, out_csv):
    summary_rows = []
    for fname in sorted(os.listdir(dir_path)):
        if not fname.endswith(".json"):
            continue
        pmid, run_label = infer_pmid_run(fname)
        if not pmid:
            print(f"skip {fname}: couldn't infer a PMID from the filename", file=sys.stderr)
            continue
        try:
            predictions = load_predictions(os.path.join(dir_path, fname))
            result = score(pmid, predictions, csv_rows)
        except (ValueError, KeyError) as e:
            print(f"skip {fname}: {e}", file=sys.stderr)
            continue
        print_summary(result, run_label)
        summary_rows.append({
            "pmid": result["pmid"],
            "run": run_label or "",
            "n_steps": result["n_steps"],
            "n_csv_hits": len(result["csv_hits"]),
            "n_predicted": len(result["predicted_keys"]),
            "n_misses": len(result["misses"]),
            "n_unsupported": len(result["unsupported"]),
            "n_unresolved": len(result["unresolved_names"]),
            "misses": ";".join(result["misses"]),
            "unsupported": ";".join(result["unsupported"]),
        })

    if out_csv and summary_rows:
        fieldnames = list(summary_rows[0].keys())
        with open(out_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_rows)
        print(f"Wrote {out_csv} ({len(summary_rows)} rows)", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json_path", help="A single Copilot JSON output file, or (with --batch) a directory of them")
    ap.add_argument("--pmid", help="PMID to score against (single-file mode; ignored with --batch)")
    ap.add_argument("--run", choices=["masked", "unmasked"], help="Label for this run, shown in the summary")
    ap.add_argument("--csv", default=CSV_PATH, help="Path to bv-brc-methods-mined.csv")
    ap.add_argument("--out", help="Single-file mode: write the full JSON result here")
    ap.add_argument("--batch", action="store_true", help="Treat json_path as a directory of output files")
    ap.add_argument("--out-csv", help="Batch mode: write a per-paper summary CSV here")
    args = ap.parse_args()

    csv_rows = load_csv_rows(args.csv)

    if args.batch:
        run_batch(args.json_path, csv_rows, args.out_csv)
        return

    if not args.pmid:
        ap.error("--pmid is required unless --batch is given")
    try:
        run_single(args.json_path, args.pmid, args.run, csv_rows, args.out)
    except (ValueError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
