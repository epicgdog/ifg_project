# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ForgeReach V1** — AI-powered B2B outreach pipeline for IFG. Ingests Apollo/LinkedIn CSV exports, classifies contacts as `owner` or `referral_advocate`, generates personalized 3-step email sequences in Kory Mitchell's voice via OpenRouter (default: `deepseek/deepseek-v3.2`), and exports campaign-ready CSVs.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add OPENROUTER_API_KEY at minimum
```

Required env var: `OPENROUTER_API_KEY`. All others (`APOLLO_API_KEY`, `HUNTER_API_KEY`, `APIFY_API_TOKEN`, `APIFY_LINKEDIN_ACTOR_ID`) are optional and only needed for API discovery/enrichment.

## Running

**Streamlit UI (recommended):**
```bash
streamlit run app.py
```

**CLI — dry run (no LLM calls):**
```bash
python -m src.main --input data/sample_contacts.csv --output out/campaign.csv --dry-run --verbose
```

**CLI — live generation:**
```bash
python -m src.main --input data/your_export.csv --output out/campaign.csv
```

**CLI — API discovery (Colorado referral advocates):**
```bash
python -m src.main --prospect-referral-advocates --state CO --output out/co_ra.csv --dry-run
```

## Architecture

The pipeline flows linearly through these stages:

```
CSV / API Discovery → Dedup → Enrich (optional) → Classify → Qualify → Generate → Validate → Export
```

**Key modules:**

| File | Role |
|------|------|
| `src/ingest.py` | CSV parsing with fuzzy header normalization (handles Apollo/LinkedIn/Hunter variants) |
| `src/scoring.py` | Rule-based audience classification (`owner` vs `referral_advocate`) + fit scoring (0–100) |
| `src/prospecting.py` | Apollo/Hunter API discovery, ICP qualification, deduplication |
| `src/enrichment.py` | Optional Apollo/Apify enrichment with TTL cache and retries |
| `src/messaging.py` | Few-shot prompt assembly and OpenRouter sequence generation |
| `src/validators.py` | Post-generation quality checks (length, CTA, taboo phrases, signature) |
| `src/pipeline.py` | Orchestrates all stages; writes `campaign_ready.csv` |
| `src/ui_service.py` | Bridges Streamlit UI to pipeline |
| `app.py` | Streamlit dashboard |
| `src/main.py` | CLI entry point |
| `src/config.py` | `Settings` dataclass loaded from env via `load_settings()` |

**Voice replication (no RAG):**
- `data/voice_profile.json` — tone traits, phrase preferences, taboo list, static exemplars
- `MASTER.md` — Kory's persona, parsed by `src/master_persona.py` into prompt sections and few-shot examples
- `src/messaging.py:build_sequence_prompt()` — assembles the full generation prompt: voice profile + MASTER rules + per-step few-shot examples (selected by audience + step + keyword overlap) + contact context
- `--dry-run` bypasses LLM and returns deterministic placeholder emails

**Classification logic (`src/scoring.py`):**
- Contacts with advisor-style keywords (wealth, insurance, CFO, EOS, etc.) → `referral_advocate`
- All others → `owner`
- Fit score built from: leadership title (+20), advisor keyword (+15), blue-collar vertical hint (+20), website present (+5), geo data (+5); base of 40; contacts scoring <55 are auto-flagged for review

**Output files:**
- `campaign_ready.csv` — full pipeline output with all columns
- `instantly_campaign.csv` — trimmed export for Instantly.ai import

## Data Files

- `data/sample_contacts.csv` — sample input for testing
- `data/voice_profile.json` — voice constraints and exemplars (edit to tune generation)
- `data/icp_profile.json` — ICP qualification criteria
- `MASTER.md` — primary persona source (expanding this improves output quality)
