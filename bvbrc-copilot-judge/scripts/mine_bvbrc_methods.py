#!/usr/bin/env python3
"""Mine BV-BRC/PATRIC method usage from full text of citing papers (PMC OA subset only)."""
import csv
import json
import re
import sys
import time
import urllib.request
import urllib.error

import os

BUNDLE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BUNDLE_ROOT, "references", "cite-bv-brc.csv")
OUT_CSV = os.path.join(BUNDLE_ROOT, "references", "bv-brc-methods-mined.csv")
OUT_JSON = os.path.join(BUNDLE_ROOT, "references", "bv-brc-methods-mined-raw.json")
PAPERS_DIR = os.path.join(BUNDLE_ROOT, "references", "papers")

BIOC_URL = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/{pmcid}/unicode"

# service_key -> (label, [strong terms], [general terms])
SERVICES = {
    "cga": ("Comprehensive Genome Analysis", ["comprehensive genome analysis"], ["genome analysis service"]),
    "assembly": ("Genome Assembly Service", ["genome assembly service"], ["assembly", "assembled", "de novo assembly"]),
    "annotation": ("Genome Annotation Service / RASTtk", ["genome annotation service", "rasttk", "rast tool kit"], ["annotated", "annotation"]),
    "sgf": ("Similar Genome Finder", ["similar genome finder"], ["similar genomes"]),
    "proteome_cmp": ("Proteome Comparison", ["proteome comparison"], ["protein comparison"]),
    "variation": ("Variation Analysis Service", ["variation analysis service"], ["snp calling", "variant calling", "variants identified", "variant analysis"]),
    "metagenomics": ("Metagenomic Binning / Read Mapping", ["metagenomic binning", "metagenomic read mapping"], ["binned", "reads mapped", "read mapping"]),
    "rnaseq": ("RNA-Seq / Transcriptomics Analysis Service", ["rna-seq analysis service", "rnaseq analysis service"], ["differential expression", "transcriptomic analysis", "transcriptomics analysis"]),
    "phylo": ("Phylogenetic Tree Building / Codon Tree / Gene Tree", ["phylogenetic tree building service", "codon tree", "gene tree"], ["phylogenetic tree", "phylogenomic analysis"]),
    "crispr": ("CRISPR Finder", ["crispr finder"], ["crispr arrays", "crispr spacers"]),
    "subsystems": ("Subsystems", ["subsystem analysis"], ["subsystems", "functional categories"]),
    "specialty_genes": ("Specialty Genes", ["specialty genes"], ["virulence factors identified", "specialty gene"]),
    "amr": ("AMR Phenotype Prediction", ["amr phenotype prediction", "antimicrobial resistance phenotype prediction"], ["resistance phenotype predicted", "amr prediction"]),
    "taxclass": ("Taxonomic Classification Service", ["taxonomic classification service"], ["taxonomic classification"]),
    "docking": ("Docking Service", ["docking service"], ["molecular docking"]),
    "pfs": ("Protein Family Sorter", ["protein family sorter"], ["protein families"]),
    "pathway": ("Pathway / Comparative Pathway", ["comparative pathway", "pathway analysis"], ["metabolic pathway analysis"]),
    "p3tools": ("p3-tools / PATRIC CLI / Data API", ["p3-tools", "patric command line", "bv-brc data api", "patric data api"], []),
    "blast": ("BLAST", ["blastp", "blastn", "blastx", "tblastn", "protein blast", "nucleotide blast"], ["blast search", "sequence similarity search"]),
    "primer_design": ("Primer Design", ["primer design service"], ["primer design", "designed primers", "primers were designed"]),
    "genome_alignment": ("Genome Alignment", ["genome alignment service"], ["genome alignment", "whole genome alignment"]),
    "tnseq": ("Tn-Seq Analysis", ["tn-seq analysis", "tnseq analysis", "transposon insertion sequencing"], ["tn-seq", "transposon mutagenesis"]),
    "bact_genome_tree": ("Bacterial Genome Tree", ["bacterial genome tree"], []),
    "viral_genome_tree": ("Viral Genome Tree", ["viral genome tree"], []),
    "cgmlst": ("Core Genome MLST", ["core genome mlst", "cgmlst"], ["multilocus sequence typing"]),
    "wg_snp": ("Whole Genome SNP Analysis", ["whole genome snp analysis", "whole-genome snp analysis"], ["genome-wide snp analysis"]),
    "msa_snp": ("MSA and SNP Analysis", ["msa and snp analysis", "multiple sequence alignment and snp"], []),
    "metacats": ("Meta-CATS", ["meta-cats", "metacats"], []),
    "protein_structure": ("Protein Structure Prediction", ["protein structure prediction service", "protein structure prediction"], ["predicted protein structure", "structural modeling"]),
    "protein_stability": ("Protein Stability Prediction", ["protein stability prediction service", "protein stability prediction"], ["predicted protein stability"]),
    "comparative_systems": ("Comparative Systems", ["comparative systems service", "comparative systems analysis"], []),
    "mobile_element": ("Mobile Element Detection", ["mobile element detection", "mobile genetic element detection"], ["mobile genetic elements", "insertion sequences identified"]),
    "expression_import": ("Expression Import", ["expression import service", "expression import tool"], ["gene expression data imported"]),
    "fastq_utils": ("Fastq Utilities", ["fastq utilities", "fastq utility service"], ["fastq quality trimming", "read trimming"]),
    "id_mapper": ("ID Mapper", ["id mapper", "identifier mapper service"], ["id mapping", "gene id conversion"]),
    "sarscov2_genome": ("SARS-CoV-2 Genome Analysis", ["sars-cov-2 genome analysis service", "sars-cov-2 genome analysis"], []),
    "sarscov2_wastewater": ("SARS-CoV-2 Wastewater Analysis", ["sars-cov-2 wastewater analysis", "wastewater surveillance service"], ["wastewater sequencing"]),
    "flu_submission": ("Influenza Sequence Submission", ["influenza sequence submission service", "influenza sequence submission"], []),
    "flu_ha_subtype": ("Influenza HA Subtype Conversion", ["influenza ha subtype conversion", "ha subtype conversion tool"], []),
    "flu_reassortment": ("Influenza Reassortment Analysis", ["influenza reassortment analysis", "reassortment analysis service"], ["genome reassortment"]),
    "subspecies": ("Subspecies Classification", ["subspecies classification service", "subspecies classification"], ["lineage classification", "genotype classification"]),
    "viral_assembly": ("Viral Assembly", ["viral assembly service", "viral genome assembly service"], []),
    "outbreak_tracker": ("Outbreak Tracker", ["outbreak tracker", "outbreak tracking service"], ["outbreak surveillance", "outbreak investigation"]),
}

# BV-BRC/PATRIC self-mentions - used to gate ambiguous general-tier hits
PLATFORM_TERMS = re.compile(r"\bbv-?brc\b|\bpatric\b", re.IGNORECASE)


def fetch_biocjson(pmcid):
    url = BIOC_URL.format(pmcid=pmcid)
    req = urllib.request.Request(url, headers={"User-Agent": "bvbrc-codeathon-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
            return json.loads(data)
    except Exception as e:
        return None


def extract_text(bioc_json):
    """Flatten BioC JSON into plain text, also return sentence list for snippet extraction."""
    texts = []
    try:
        docs = bioc_json[0]["documents"] if isinstance(bioc_json, list) else bioc_json["documents"]
    except Exception:
        return ""
    for doc in docs:
        for passage in doc.get("passages", []):
            t = passage.get("text", "")
            if t:
                texts.append(t)
    return "\n".join(texts)


def split_sentences(text):
    # crude sentence splitter, good enough for snippet extraction
    return re.split(r'(?<=[.!?])\s+', text)


def clean_snippet(s):
    return re.sub(r"\s+", " ", s).strip()


def find_hits(text, sentences):
    hits = {}
    lower = text.lower()
    platform_present = bool(PLATFORM_TERMS.search(text))
    for key, (label, strong_terms, general_terms) in SERVICES.items():
        strong_hits = []
        general_hits = []
        for term in strong_terms:
            if term.lower() in lower:
                snippet = next((clean_snippet(s) for s in sentences if term.lower() in s.lower()), "")
                strong_hits.append({"term": term, "snippet": snippet[:300]})
        for term in general_terms:
            if term.lower() in lower:
                # only count general-tier hits in sentences that also mention BV-BRC/PATRIC
                for s in sentences:
                    if term.lower() in s.lower() and PLATFORM_TERMS.search(s):
                        general_hits.append({"term": term, "snippet": clean_snippet(s)[:300]})
                        break
        if strong_hits or general_hits:
            hits[key] = {"label": label, "strong": strong_hits, "general": general_hits}
    return hits, platform_present


def main():
    rows = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"Total rows: {len(rows)}", file=sys.stderr)
    os.makedirs(PAPERS_DIR, exist_ok=True)

    results = []
    n_with_pmcid = 0
    n_fetched = 0
    n_failed = 0

    for i, row in enumerate(rows):
        pmcid = row.get("PMCID", "").strip()
        pmid = row.get("PMID", "").strip()
        title = row.get("Title", "").strip()
        if not pmcid:
            results.append({"pmid": pmid, "pmcid": "", "title": title, "fulltext": False, "hits": {}})
            continue
        n_with_pmcid += 1
        cached_path = os.path.join(PAPERS_DIR, f"{pmid}.txt") if pmid else None
        if cached_path and os.path.exists(cached_path):
            with open(cached_path, encoding="utf-8") as pf:
                text = pf.read()
        else:
            bioc = fetch_biocjson(pmcid)
            time.sleep(0.34)  # ~3 req/sec
            if not bioc:
                n_failed += 1
                results.append({"pmid": pmid, "pmcid": pmcid, "title": title, "fulltext": False, "hits": {}})
                continue
            text = extract_text(bioc)
            if not text or len(text) < 200:
                n_failed += 1
                results.append({"pmid": pmid, "pmcid": pmcid, "title": title, "fulltext": False, "hits": {}})
                continue
            if cached_path:
                with open(cached_path, "w") as pf:
                    pf.write(text)
        if not text or len(text) < 200:
            n_failed += 1
            results.append({"pmid": pmid, "pmcid": pmcid, "title": title, "fulltext": False, "hits": {}})
            continue
        n_fetched += 1
        sentences = split_sentences(text)
        hits, platform_present = find_hits(text, sentences)
        results.append({
            "pmid": pmid, "pmcid": pmcid, "title": title,
            "fulltext": True, "platform_mentioned": platform_present,
            "hits": hits,
        })
        if (i + 1) % 25 == 0:
            print(f"...processed {i+1}/{len(rows)} (fetched={n_fetched}, failed={n_failed})", file=sys.stderr)

    print(f"With PMCID: {n_with_pmcid}, full text fetched: {n_fetched}, failed/no-OA: {n_failed}", file=sys.stderr)

    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=2)

    # write CSV: one row per paper with full text, one column per service (strong_count, general_count), plus one example snippet column
    service_keys = list(SERVICES.keys())
    fieldnames = ["pmid", "pmcid", "title", "platform_mentioned"]
    for k in service_keys:
        fieldnames += [f"{k}_strong", f"{k}_general", f"{k}_example"]

    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            if not r.get("fulltext"):
                continue
            row = {"pmid": r["pmid"], "pmcid": r["pmcid"], "title": r["title"], "platform_mentioned": r.get("platform_mentioned", False)}
            for k in service_keys:
                h = r["hits"].get(k)
                if h:
                    row[f"{k}_strong"] = len(h["strong"])
                    row[f"{k}_general"] = len(h["general"])
                    ex = (h["strong"] + h["general"])
                    row[f"{k}_example"] = ex[0]["snippet"] if ex else ""
                else:
                    row[f"{k}_strong"] = 0
                    row[f"{k}_general"] = 0
                    row[f"{k}_example"] = ""
            writer.writerow(row)

    print(f"Wrote {OUT_CSV} and {OUT_JSON}", file=sys.stderr)


if __name__ == "__main__":
    main()
