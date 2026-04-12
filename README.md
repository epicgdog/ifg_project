# ForgeReach V1

CSV-first outbound prospecting MVP for IFG.

It ingests exported contact CSVs, classifies contacts as Owner or Referral Advocate,
enriches data from APIs (Apollo, Apify), builds context, generates personalized
outreach in Kory's voice via OpenRouter, validates output quality, and exports a
campaign-ready CSV with sequenced send timing and provenance tracking.

## What it does

- Accepts one or more input CSV files (Apollo/LinkedIn/Hunter style exports).
- Normalizes uneven field names into a consistent schema.
- **Enriches contacts from APIs** (Apollo.io, Apify LinkedIn) with caching and retries.
- Classifies audience type (`owner` vs `referral_advocate`) with explainable tags.
- Generates three-step email sequences tailored by audience.
- **Validates output** for length, tone compliance, spam patterns, and signature.
- **Replicates speaker voice** using a configurable voice profile (static exemplars now, RAG-ready for later).
- Produces `campaign_ready.csv` with contact info, copy, suggested send times, and provenance.

## Quick start

### 1. Create a virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add your environment variables

Copy `.env.example` to `.env` and fill in your API keys:

```env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=moonshotai/kimi-k2
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_HTTP_REFERER=https://ifg.local
OPENROUTER_TITLE=ForgeReach

# Optional: for live enrichment
APOLLO_API_KEY=your_apollo_key
HUNTER_API_KEY=your_hunter_key
APIFY_API_TOKEN=your_apify_token
APIFY_LINKEDIN_ACTOR_ID=your_actor_id
```

### 3. Run the pipeline

**Dry run** (no API calls, deterministic output):
```bash
python -m src.main --input data/sample_contacts.csv --output out/campaign_ready.csv --dry-run
```

**With live enrichment** (requires API keys):
```bash
python -m src.main --input data/sample_contacts.csv --output out/campaign_ready.csv --enrich
```

**With verbose output and report**:
```bash
python -m src.main --input data/sample_contacts.csv --output out/campaign_ready.csv \
    --enrich --verbose --report out/run_report.json
```

**With qualification controls and Instantly export**:
```bash
python -m src.main --input data/sample_contacts.csv --output out/campaign_ready.csv \
    --icp-profile data/icp_profile.json --min-qualification-score 60 \
    --instantly-output out/instantly_campaign.csv --dry-run
```

**Phase 2: API prospect discovery (Apollo/Hunter)**:
```bash
python -m src.main --prospect --prospect-source apollo hunter \
    --prospect-limit 25 --hunter-domain example.com acme.com \
    --output out/campaign_ready.csv --dry-run --verbose
```

**Phase 2: Prospect + merge with CSV leads**:
```bash
python -m src.main --prospect --prospect-source apollo \
    --input data/sample_contacts.csv --output out/campaign_ready.csv --dry-run
```

### 4. Run the Streamlit dashboard (Phase 1)

```bash
streamlit run app.py
```

The dashboard lets you upload a CSV, run the pipeline, review generated sequences,
and download a campaign-ready CSV for your sending platform.

## Input expectations

The tool maps common variants automatically:
- Names: `first_name`, `First Name`, `Owner Name`
- Company: `company`, `Company Name`, `account`
- Title: `title`, `Job Title`, `role`, `position`
- Contact: `email`, `email_address`, `work_email`
- LinkedIn: `linkedin`, `linkedin_url`, `profile_url`

## Output columns

### Contact fields
- `name`, `title`, `company`, `email`, `location`, `website`, `linkedin`

### Enrichment & Classification
- `audience`, `audience_reason`, `fit_score`, `fit_reason`
- `title_source`, `company_source`, `industry_source` (provenance)
- `enriched_at` (timestamp of enrichment)

### Email sequence
- `email_step_1`, `email_step_2`, `email_step_3`
- `voice_profile_version`, `generation_method`
- `validation_passed`, `validation_errors`

### Timing & Quality
- `send_at_step_1`, `send_at_step_2`, `send_at_step_3`
- `review_flag` (yes/no based on fit score and validation)

### Metadata
- `source_file`, `row_id`

## Voice Replication (Basic LLM, No RAG Yet)

The system uses a **static voice profile** to replicate speaking style. The profile includes:

- **Tone traits**: plainspoken, respectful, blue-collar credibility, no hype
- **Sentence patterns**: Direct openings, short declarative statements
- **Phrase preferences**: "I run", "compare notes", "tighten operations"
- **Taboo phrases**: "just checking in", "hope you're well", "circle back"
- **CTA style**: Single direct question, low pressure
- **Static exemplars**: Curated examples for few-shot prompting

### Customizing the voice

The default voice profile is automatically created at `data/voice_profile.json` on first run.
Edit this file to customize:

```json
{
  "version": "1.0",
  "name": "Kory Mitchell",
  "tone_traits": ["plainspoken", "respectful", ...],
  "phrase_preferences": ["I run", "compare notes", ...],
  "taboo_phrases": ["just checking in", "hope you're well", ...],
  "style_exemplars": [
    {"context": "referral_advocate_step_1", "exemplar": "..."}
  ]
}
```

Or provide a custom profile path:
```bash
python -m src.main --input data/sample.csv --output out/campaign.csv --voice-profile profiles/custom.json
```

### Future: RAG Integration

The codebase is **RAG-ready**. Once you have transcripts processed:

1. The `voice_profile.py` module has a `get_exemplars_for_context()` method
2. Replace static exemplars with vector retrieval
3. Change `generation_method` from `"static"` to `"rag"`
4. No pipeline changes required

## CLI Options

```
--input FILE [FILE ...]     Input CSV file(s) (required)
--output FILE               Output CSV path (required)
--dry-run                   Skip API calls, use deterministic output
--prospect                  Discover net-new contacts via API
--prospect-source ...       Prospecting sources: apollo hunter
--prospect-limit N          Max discovered contacts (default: 25)
--hunter-domain ...         Hunter domains for discovery
--enrich                    Enable API enrichment (Apollo, Apify)
--no-enrich-cache           Disable enrichment caching
--enrich-cache-ttl HOURS    Cache TTL (default: 24)
--enrich-timeout SECONDS    API timeout (default: 60)
--enrich-retries N          Max retries (default: 3)
--clear-enrich-cache        Clear cache before running
--voice-profile PATH        Custom voice profile JSON
--icp-profile PATH          ICP profile JSON (default: data/icp_profile.json)
--min-qualification-score N Minimum score to mark qualified (default: 60)
--report PATH               Write run report JSON
--instantly-output PATH     Also export Instantly-formatted CSV
--verbose, -v               Print detailed output
```

## Qualification and Prospecting Layer

Phase 1 now includes an ICP-driven qualification layer before outreach export:

- `data/icp_profile.json` defines target industries, titles, geographies, and exclusions
- every contact receives `qualification_score`, `qualification_tier`, and `qualified`
- run report now includes `qualified_count` and `high_priority_count`

Phase 2 adds net-new contact discovery:

- Apollo people search based on ICP title/industry/headcount filters
- Hunter domain discovery for lower-cost email sourcing fallback
- dedupe logic that merges discovered contacts with CSV imports
- full discovered list runs through enrichment, scoring, and sequence generation

Output includes these additional columns:

- `qualified`
- `qualification_score`
- `qualification_tier`
- `qualification_reason`

## Instantly Export

Use `--instantly-output` to generate an import-ready file with:

- First Name, Last Name, Email, Company
- Step 1, Step 2, Step 3
- qualification tags for filtering before send

## Dashboard (Phase 1)

The Streamlit app in `app.py` is a presentation-ready interface for:

- Config health checks (OpenRouter, Apollo, Apify)
- Contact CSV upload and sample data runs
- Dry-run and enrichment toggles
- ICP profile and qualification threshold controls
- Prospect discovery controls (Apollo/Hunter + limits/domains)
- Executive metrics (enriched count, review flags, fit score)
- Qualification metrics (qualified count, high-priority count)
- Audience split and contact filtering
- Sequence preview (intro, follow-up, break-up)
- Download of `campaign_ready.csv` and `instantly_campaign.csv`

This phase intentionally does **not** send emails directly. It prepares campaign-ready
exports so you can review quality before loading into Instantly, Apollo, or Outlook.

## Testing Checklist

Run these before demoing:

```bash
# 1) Install dependencies in .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2) CLI smoke test (no API calls)
python -m src.main --input data/sample_contacts.csv --output out/campaign_ready.csv --dry-run --verbose

# 3) CLI with enrichment (if keys are set)
python -m src.main --input data/sample_contacts.csv --output out/campaign_ready.csv --enrich --verbose

# 4) Launch dashboard
streamlit run app.py
```

## Architecture

```
ingest.py      → Read and normalize CSVs
enrichment.py  → API orchestration (Apollo, Apify) with cache/retries
scoring.py     → Classify audience, calculate fit score
messaging.py   → Build prompts with voice profile, generate sequences
validators.py  → Quality checks (length, tone, spam patterns)
schedule.py    → Suggest send times
pipeline.py    → Orchestrate stages, produce output with provenance
```

## Data Provenance

Every field tracks its source:
- `csv`: Original import
- `apollo`: Enriched from Apollo.io
- `apify`: Enriched from Apify LinkedIn scraper

Enrichment cache is stored in `.cache/enrichment/` (gitignored).

## Troubleshooting

**Generation failures**: Check validation errors in output CSV. Common issues:
- Missing CTA question
- Taboo phrase detected
- Signature format incorrect

**Enrichment errors**: API timeouts or rate limits are non-fatal. Check:
- API keys in `.env`
- `--verbose` flag for error details
- Cache hit rate in run report

**Fit score too low**: Contacts with `fit_score < 55` are auto-flagged for review.

## Requirements

- Python 3.10+
- See `requirements.txt` for dependencies
