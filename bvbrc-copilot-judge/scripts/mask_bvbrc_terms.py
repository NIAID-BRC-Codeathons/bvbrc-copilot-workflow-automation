#!/usr/bin/env python3
"""Produce masked copies of references/papers/ for the stage-1 masked-vs-unmasked
comparison in documents/p6-stage1-stage2-benchmark-design.md.

Redacts each BV-BRC/PATRIC service's *strong* terms only (its proper name or
abbreviation, e.g. "RASTtk", "Comprehensive Genome Analysis", "Similar Genome
Finder") to [MASKED-SERVICE], reusing the SERVICES table from
mine_bvbrc_methods.py so the two scripts can't drift apart. General terms
("annotated", "assembled") and platform self-mentions ("BV-BRC", "PATRIC")
are left untouched: they're ordinary English / the platform name, not a
service name, and masking them would just mutilate the method description
Copilot is supposed to read.

Output: references/papers_masked/<PMID>.txt, one per input file in
references/papers/, whether or not any redaction applied (so masked and
unmasked runs use structurally identical file sets).
"""
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BUNDLE_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)
from mine_bvbrc_methods import SERVICES  # noqa: E402

PAPERS_DIR = os.path.join(BUNDLE_ROOT, "references", "papers")
OUT_DIR = os.path.join(BUNDLE_ROOT, "references", "papers_masked")
MASK_TOKEN = "[MASKED-SERVICE]"


def build_pattern():
    terms = {t for _, strong_terms, _ in SERVICES.values() for t in strong_terms}
    # longest first so multi-word terms aren't shadowed by a shorter substring alternative
    ordered = sorted(terms, key=len, reverse=True)
    return re.compile(r"\b(" + "|".join(re.escape(t) for t in ordered) + r")\b", re.IGNORECASE)


def main():
    pattern = build_pattern()
    os.makedirs(OUT_DIR, exist_ok=True)

    n_files = 0
    n_masked = 0
    n_redactions = 0
    for fname in sorted(os.listdir(PAPERS_DIR)):
        if not fname.endswith(".txt"):
            continue
        with open(os.path.join(PAPERS_DIR, fname), encoding="utf-8") as f:
            text = f.read()
        masked_text, count = pattern.subn(MASK_TOKEN, text)
        with open(os.path.join(OUT_DIR, fname), "w", encoding="utf-8") as f:
            f.write(masked_text)
        n_files += 1
        if count:
            n_masked += 1
            n_redactions += count

    print(
        f"Masked {n_files} papers -> {OUT_DIR} "
        f"({n_masked} had >=1 redaction, {n_redactions} redactions total)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
