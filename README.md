# ForgeReach V1

AI-powered prospecting and outreach for IFG. Upload Apollo/LinkedIn CSV exports, classify contacts, generate personalized 3-step email sequences in Kory Mitchell's voice, and export campaign-ready files.

## Current Architecture: Few-Shot Prompting (No RAG)

The system uses **rule-based few-shot prompting** to replicate Kory's voice:

- Static voice profile with tone traits, phrase preferences, and taboo phrases
- MASTER persona file (`MASTER.md`) parsed into style rules
- Curated few-shot example bank selected per audience + sequence step
- Rule-based example selection (by audience + step + keyword overlap)
- **No RAG or vector retrieval** — deliberately simple, fast, and controllable

## What It Does

- **CSV Processing**: Ingest Apollo/LinkedIn/Hunter exports with smart header normalization
- **API Discovery** (optional): Find Colorado referral advocates via Apollo/Hunter APIs
- **Classification**: Tag contacts as `owner` or `referral_advocate` with fit scoring
- **Qualification**: ICP-driven scoring with tiered output (high/medium/low)
- **Soft Owner Readiness**: Owner-side readiness tiering using title/industry/revenue/headcount proxies (no hard exclusions)
- **Generation**: 3-step sequences (intro → follow-up → break-up) using few-shot prompting
- **Validation**: Length, tone, spam pattern, and signature checks
- **Export**: `campaign_ready.csv` + `instantly_campaign.csv` for your sending platform

## Quick Start

### 1. Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment

Copy `.env.example` to `.env` and add keys:

```env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=deepseek/deepseek-v3.2
APOLLO_API_KEY=your_apollo_key      # Optional: for API discovery
HUNTER_API_KEY=your_hunter_key      # Optional: for domain lookup
```

### 3. Run from Streamlit (Recommended)

```bash
streamlit run app.py
```

**Three modes available:**
- **CSV only**: Process your Apollo/LinkedIn exports
- **API discovery only**: Find Colorado referral advocates via APIs
- **CSV + API merge**: Combine your CSV with discovered contacts

All controls in one place: upload CSVs, toggle enrichment, set qualification thresholds, inspect scoring logic, preview sequences, and download exports.
You can also configure MASTER-based few-shot prompting and the active OpenRouter model directly in the sidebar.

### 4. Or Run from CLI

**CSV-only workflow** (most common):
```bash
python -m src.main \
    --input data/your_apollo_export.csv \
    --output out/campaign_ready.csv \
    --instantly-output out/instantly_campaign.csv \
    --dry-run --verbose
```

**With live generation** (remove `--dry-run`):
```bash
python -m src.main \
    --input data/your_apollo_export.csv \
    --output out/campaign_ready.csv \
    --icp-profile data/icp_profile.json \
    --min-qualification-score 60
```

**API discovery** (Colorado referral advocates):
```bash
python -m src.main \
    --prospect-referral-advocates \
    --state CO --prospect-source apollo \
    --prospect-limit 50 \
    --output out/co_referral_advocates.csv
```

## Input: CSV Processing

The parser handles common Apollo/CRM header variations automatically:

| Our Field | Matches |
|-----------|---------|
| `first_name` | `first_name`, `firstname`, `First Name`, `person first name` |
| `last_name` | `last_name`, `lastname`, `Last Name`, `person last name` |
| `full_name` | `name`, `full_name`, `person name`, `contact name` |
| `title` | `title`, `job_title`, `person title`, `role` |
| `company` | `company`, `company_name`, `account`, `organization` |
| `email` | `email`, `email_address`, `work_email`, `Email` |
| `linkedin` | `linkedin`, `linkedin_url`, `person linkedin url` |
| `website` | `website`, `company_website`, `domain`, `organization website` |

Also handles: punctuation cleanup, underscores vs spaces, deriving first/last from full name.

## Few-Shot Voice Replication

Current approach (no RAG):

1. **Voice Profile** (`data/voice_profile.json`):
   - Tone traits: plainspoken, respectful, blue-collar credibility, no hype
   - Phrase preferences: "I run", "compare notes", "tighten operations"
   - Taboo phrases: "just checking in", "hope you're well", "circle back"
   - CTA style: single direct question, low pressure
   - Signature: dash + full name

2. **MASTER Persona Source** (`MASTER.md`):
   - Identity and tone rules are parsed from your master file
   - Lexicon and writing rules are injected into prompts

3. **Example Bank**: Few-shot exemplars selected by:
   - Audience (`owner` vs `referral_advocate`)
   - Step (intro/follow-up/break-up)
   - Keyword overlap with contact context

4. **Prompt Assembly**:
   - Voice constraints
   - MASTER persona rules
   - Top-k examples (default k=3)
   - Contact context + audience instructions
   - Strict output format

Model used for generation: `deepseek/deepseek-v3.2` (OpenRouter).

### Customizing Examples

Edit `data/voice_profile.json`:

```json
{
  "version": "1.0",
  "name": "Kory Mitchell",
  "tone_traits": ["plainspoken", "respectful", "blue-collar credibility", "no hype"],
  "phrase_preferences": ["I run", "compare notes", "tighten operations"],
  "taboo_phrases": ["just checking in", "hope you're well", "circle back"],
  "style_exemplars": [
    {"context": "referral_advocate_step_1", "exemplar": "..."},
    {"context": "owner_step_1", "exemplar": "..."}
  ]
}
```

## Output Columns

**Contact**: `full_name`, `first_name`, `last_name`, `email`, `title`, `company`, `industry`, `website`, `linkedin`, `city`, `state`

**Classification**: `audience`, `audience_reason`, `fit_score`, `fit_reason`, `fit_breakdown_json`, `matched_signals`

**Qualification**: `qualified`, `qualification_score`, `qualification_tier`, `qualification_reason`, `qualification_breakdown_json`

**Owner Readiness (soft gate)**: `owner_readiness_tier`, `owner_readiness_confidence`

**Sequence**: `email_step_1`, `email_step_2`, `email_step_3`, `send_at_step_1`, `send_at_step_2`, `send_at_step_3`

**Quality**: `review_flag`, `voice_profile_version`, `generation_method`, `validation_passed`, `validation_errors`

**Provenance**: `title_source`, `company_source`, `industry_source`, `enriched_at`

**Metadata**: `source_file`, `row_id`

## Instantly Export

`instantly_campaign.csv` includes:
- First Name, Last Name, Email, Company
- Step 1, Step 2, Step 3
- Qualified, Qualification Tier

Ready to import into Instantly.ai or similar platforms.

## Score Inspector (Streamlit)

The dashboard now includes a Score Inspector per selected contact:

- Fit Score and Qualification Score side-by-side
- Rule-by-rule score adjustments with matched evidence
- Matched signal list (owner/RA/blue-collar hints)
- Waterfall-style progression from base score to final score
- Owner readiness tier and confidence for Audience A prioritization

This makes scoring transparent so you can explain exactly why each contact was prioritized.

## Audience A and B Workflow

The MVP supports both outbound channels:

- **Audience A: Blue-collar owners**
  - founder/operator messaging tone
  - soft owner-readiness scoring (no strict rejection if financial data is missing)
- **Audience B: Referral advocates**
  - advisor-first relationship outreach
  - Colorado-focused API discovery path available

You can operate both channels in the same run and filter by audience/tier in the dashboard.

## CLI Reference

```
--input FILE [FILE ...]      Input CSV file(s)
--output FILE                Output CSV path (required)
--dry-run                    Skip LLM calls, use deterministic output
--prospect                   Enable API discovery
--prospect-referral-advocates   Colorado RA mode (API only)
--prospect-source ...        apollo, hunter
--prospect-limit N           Max contacts to discover (default: 25)
--state STATE                State filter for RA mode (default: CO)
--hunter-domain ...          Domains for Hunter lookup
--enrich                     Enable API enrichment
--no-enrich-cache            Disable enrichment cache
--voice-profile PATH         Custom voice profile
--master-persona-path PATH   Master persona markdown path (default: MASTER.md)
--disable-master-persona     Disable MASTER-based few-shot
--few-shot-k N               Few-shot examples per step (default: 3)
--icp-profile PATH           Custom ICP profile
--min-qualification-score N  Threshold (default: 60)
--instantly-output PATH      Export Instantly-formatted CSV
--report PATH                Write JSON run report
--verbose, -v                Detailed output
```

## Architecture

```
ingest.py          → CSV parsing with header normalization
prospecting.py     → API discovery (Apollo/Hunter), dedupe, qualification
enrichment.py      → API enrichment (Apollo/Apify) with cache/retries
scoring.py         → Audience classification (owner vs referral_advocate)
messaging.py       → Few-shot prompt building, sequence generation
validators.py      → Quality checks (length, tone, spam, signature)
schedule.py        → Send time suggestions
pipeline.py        → Stage orchestration
exporters.py       → Campaign + Instantly CSV exports
ui_service.py      → Streamlit backend service
app.py             → Streamlit UI
```

## Troubleshooting

**Generation failures**: Check `validation_errors` in output. Common issues:
- Missing CTA question
- Taboo phrase detected
- Signature format wrong

**Empty discovery results**: Check API keys in `.env` or sidebar. Apollo free tier may limit search.

**Low fit scores**: Contacts scoring <55 are auto-flagged for review.

**Owner readiness seems low**: Missing revenue/headcount/industry data can reduce confidence; this is a soft gate, not an auto-drop.

**Apollo credits are limited**: Use the in-app Apollo Credit Estimator and start with low `prospect_limit` (10-25) before scaling.

**CSV parsing issues**: Check `source_file` and `row_id` columns to trace back to originals.

## Data Flow

```
CSV Upload / API Discovery
    ↓
Deduplication (email → linkedin → name+company)
    ↓
Enrichment (optional, with cache)
    ↓
Classification + Qualification
    ↓
Few-Shot Sequence Generation
    ↓
Validation
    ↓
Export (campaign_ready.csv + instantly_campaign.csv)
```

## Requirements

- Python 3.10+
- See `requirements.txt`

## Next: CEO Speech Integration

To improve voice replication with few-shot prompting:

1. Expand `MASTER.md` with more high-quality speech snippets and phrasing examples
2. Add more audience-specific few-shot examples for each sequence step
3. Tune few-shot selection weights in `src/messaging.py`
4. Evaluate on 20–30 contacts before scaling

No RAG needed — keep it simple, fast, and controllable.
