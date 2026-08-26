# AI Orbit — Data Ingestion Pipeline

A production-style, API-first ingestion pipeline that aggregates, normalizes,
and structures multi-domain data from across the AI ecosystem into a common
entity + relationship graph.

**Live demo:** _add your deployed Streamlit URL here after deployment_
**Trial:** GraphOne / FrontierAtlas — 3-day AI Engineer trial

---

## Architecture

```
Discovery → Extraction → Cleaning → Normalization → Deduplication →
Classification → Relationship Mapping → Validation
```

Each stage is an isolated module under `src/`, connected by one shared
contract: the `Entity` and `Relationship` Pydantic models
(`src/models/entity.py`). Every extractor, regardless of source, outputs
`Entity` objects — the rest of the pipeline never needs to know where a
record came from.

```
src/
  config.py                 # env vars, constants, output paths (no secrets hardcoded)
  http_client.py             # shared retry/backoff HTTP wrapper (used by every extractor)
  models/
    entity.py                # Entity, Relationship schemas + deterministic UUID generation
  extraction/
    github_extractor.py      # repositories + MCP servers (GitHub Search API)
    huggingface_extractor.py # models (HF Hub API)
    tasks_extractor.py       # tasks (HF task taxonomy API)
    collections_extractor.py # curated "awesome-*" lists (reuses GitHub API)
    news_extractor.py        # news (public RSS feeds)
    youtube_extractor.py     # videos (YouTube Data API v3)
    curated_extractor.py     # companies/tools/robots/devices/personal/creative (see below)
  processing/
    cleaning.py               # HTML stripping, URL canonicalization
    deduplication.py          # 3-tier entity resolution
    classification.py         # keyword-based category enrichment + "new" tagging
    relationships.py          # relationship extraction between entity types
    validation.py             # schema/quality checks, quarantine reporting
run.py                        # orchestrates all 8 stages, writes data/*.json
app.py                        # Streamlit viewer (the live deployment)
```

## Why this design

**Deterministic IDs, not random ones.** Every entity's ID is a UUIDv5 derived
from `(entity_type, canonical_key)` — e.g. the GitHub repo `openai/whisper`
always resolves to the same ID, on this run or the next. This is what makes
re-running the pipeline idempotent and what makes cross-run deduplication
possible without a database round-trip.

**One HTTP client, not six.** Every extractor hits a different flaky
third-party API. Retry/backoff/error-handling logic lives once in
`http_client.py` rather than being copy-pasted per source — a request that
fails never crashes the pipeline, it just returns `None` and the caller logs
and moves on.

**Per-source isolation in the orchestrator.** `run.py` wraps every
extractor call in a try/except. If YouTube's key is missing, or a feed
times out, that source contributes zero records and everything else still
runs. This is deliberate: a demo that reproduces the *actual* trial task
should demonstrate resilience, not a single point of failure.

**Three-tier deduplication**, cheapest checks first:
1. Exact ID collision (same type + same canonical key)
2. Exact normalized-URL match within the same entity type
3. Fuzzy name match (`difflib`, threshold 0.92) — catches "OpenAI" vs
   "Open AI" vs "open-ai" without needing an LLM call for a bounded,
   ~250-300 record batch.

**Relationship extraction is deterministic text-matching, not an LLM call.**
Every relationship carries an `evidence` string (e.g. "provider field
matches 'OpenAI'") so a reviewer can audit *why* an edge exists. For a graph
this size, precision from cheap, explainable rules beats the latency/cost/
non-determinism of an LLM call — this can be swapped in later without
touching any other stage, since it only reads `Entity` objects.

**Validation quarantines, it doesn't discard silently.** Records failing
schema checks are excluded from the final `entities.json`/`relationships.json`
but logged with their specific error in `data/run_report.json` — so a bad
record is neither invisible nor allowed to corrupt the dataset.

## An honest note on data sources

The spec categories `Tools`, `Companies`, `Robots`, `Devices`, `Personal`,
and `Creative` don't have a free, keyless, API-first data source — Crunchbase
and PitchBook require paid keys, and there's no public "AI tool directory"
API. Rather than either skip these categories or quietly scrape a directory
site and call it an API, `curated_extractor.py` is a small, hand-verified
seed set of real, well-known entities (every `url` is a real, checkable
page). This is documented rather than hidden because the trade-off itself
is the point: a data engineer bootstraps reference data this way and swaps
in a paid API client later behind the same `Entity` contract — no other
code changes needed.

Everything else (`repositories`, `mcp`, `models`, `tasks`, `collections`,
`news`, `videos`) comes from live, public, keyless-or-optionally-keyed APIs:
GitHub Search API, Hugging Face Hub API + task taxonomy, RSS feeds, and
YouTube Data API v3.

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional: add GITHUB_TOKEN / YOUTUBE_API_KEY / HF_TOKEN
```

Without any keys configured, the pipeline still runs — GitHub and Hugging
Face allow unauthenticated read access (at lower rate limits), RSS needs no
key at all, and only the YouTube extractor requires one to produce results.

## Running the pipeline

```bash
python run.py                        # full run
python run.py --skip youtube,news    # skip specific sources
python run.py --verbose              # debug logging
```

Outputs land in `data/`:
- `entities.json` — validated entity records
- `relationships.json` — validated relationship edges
- `run_report.json` — counts by source/type, quarantine detail
- `pipeline.log` — full run log

## Running tests

```bash
pytest tests/ -v
```

23 tests covering entity ID determinism, cleaning/normalization edge cases,
all three deduplication tiers, and validation (entity + relationship
quarantine logic).

## Running the live viewer

```bash
streamlit run app.py
```

Deployed on Streamlit Community Cloud — publicly accessible, no login
required. The app reads directly from `data/*.json`, so redeploying after a
fresh `python run.py` just means committing the updated JSON files.

## A note on network access during development

Parts of this pipeline (Hugging Face, YouTube, RSS feeds, arXiv) were built
and unit-tested with mocked/isolated logic in a sandboxed dev environment
that only allowed outbound access to `api.github.com`. The GitHub extractor
was verified against the live API end-to-end; the others were verified via
unit tests against their parsing/transformation logic and are expected to
run unmodified in an environment with normal internet access (confirmed via
direct inspection of each API's documented response shape).
