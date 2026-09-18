# references/papers/

Full-text corpus used by the judge pipeline. Not checked into git (large,
regenerable). To populate:

```
uv run python3 scripts/mine_bvbrc_methods.py
```

This reads `references/cite-bv-brc.csv`, pulls full text from the NCBI BioC
API for each PMID/PMCID, caches it here as `<pmid>.txt`, and (re)writes
`references/bv-brc-methods-mined.csv` — already included in this repo, so
you only need to re-run the miner if you want to regenerate the corpus
text files themselves or extend the paper list.

Then populate the masked counterpart:

```
uv run python3 scripts/mask_bvbrc_terms.py
```

which reads every file here and writes a redacted copy to
`references/papers_masked/<pmid>.txt`.
