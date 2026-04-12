# ForgeReach V1

CSV-first outbound prospecting MVP for IFG.

It ingests exported contact CSVs, classifies contacts as Owner or Referral Advocate,
builds context, generates personalized outreach in Kory's voice via OpenRouter, and
exports a campaign-ready CSV with sequenced send timing.

## What it does

- Accepts one or more input CSV files (Apollo/LinkedIn/Hunter style exports).
- Normalizes uneven field names into a consistent schema.
- Classifies audience type (`owner` vs `referral_advocate`) with explainable tags.
- Generates three-step email sequences tailored by audience.
- Produces `campaign_ready.csv` with contact info, copy, and suggested send times.

## Quick start

1) Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Add your env vars (you can copy `.env.example` to `.env`):

```env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=moonshotai/kimi-k2
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_HTTP_REFERER=https://ifg.local
OPENROUTER_TITLE=ForgeReach
```

3) Run the pipeline:

```powershell
python -m src.main --input data/sample_contacts.csv --output out/campaign_ready.csv
```

If you want to test the pipeline structure without API calls:

```powershell
python -m src.main --input data/sample_contacts.csv --output out/campaign_ready.csv --dry-run
```

## Input expectations

The tool maps common variants automatically (for example: `first_name`, `First Name`,
`Owner Name`, `company`, `Company Name`, `title`, `Job Title`, `industry`, `city`).

## Output columns

- Contact fields: name, title, company, email, location, website, linkedin
- Enrichment: audience, audience_reason, fit_score, fit_reason
- Email sequence: `email_step_1..3`
- Timing: `send_at_step_1..3`
- Metadata: source_file, row_id, review_flag
