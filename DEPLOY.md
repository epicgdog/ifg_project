# Deploying ForgeReach to a Live URL

Architecture: **Next.js frontend on Vercel** + **FastAPI backend on Railway**. Judges get one Vercel URL and the Python pipeline runs on Railway behind the scenes.

Expected total time: **~15 minutes** the first time, ~2 minutes per update after.

---

## Prerequisites

1. GitHub repository with this code pushed
2. A Vercel account (free) — https://vercel.com/signup
3. A Railway account (free $5/month credit) — https://railway.app
4. API keys ready:
   - `OPENROUTER_API_KEY` (required)
   - `APOLLO_API_KEY` (optional — enables API discovery)
   - `HUNTER_API_KEY` (optional — enables domain search)
   - `APIFY_API_TOKEN` + `APIFY_LINKEDIN_ACTOR_ID` (optional — enables LinkedIn enrichment)

---

## Part 1: Deploy the Backend to Railway

### 1.1 Install the Railway CLI

```bash
npm install -g @railway/cli
railway login
```

### 1.2 Initialize the project

From the repo root:

```bash
railway init
# Select: "Empty Project"
# Name it: "forgereach-backend"
```

### 1.3 Point Railway at the backend Dockerfile

Railway auto-detects the Dockerfile at `backend/Dockerfile`. If it doesn't, open the project at https://railway.app, go to **Settings → Build**, and set:
- **Build method**: Dockerfile
- **Dockerfile path**: `backend/Dockerfile`
- **Root directory**: `/`

### 1.4 Set environment variables

Railway dashboard → **Variables** → add each:

```
OPENROUTER_API_KEY=<your key>
OPENROUTER_MODEL=deepseek/deepseek-v3.2
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_HTTP_REFERER=https://forgereach.vercel.app
OPENROUTER_TITLE=ForgeReach
APOLLO_API_KEY=<optional>
HUNTER_API_KEY=<optional>
APIFY_API_TOKEN=<optional>
APIFY_LINKEDIN_ACTOR_ID=<optional>
```

### 1.5 Deploy

```bash
railway up
```

Wait for the build to finish (~2–3 min). Then generate a public URL:

Railway dashboard → **Settings → Networking → Generate Domain**

Copy the URL — it looks like `https://forgereach-backend-production.up.railway.app`. You'll need this next.

### 1.6 Verify

```bash
curl https://<your-railway-url>/api/config/health
```

Should return `{"openrouter":true,...}`.

---

## Part 2: Deploy the Frontend to Vercel

### 2.1 Install the Vercel CLI

```bash
npm install -g vercel
vercel login
```

### 2.2 Configure the project

From the repo root:

```bash
cd web
vercel
```

Prompts:
- **Set up and deploy?** Y
- **Which scope?** (your account)
- **Link to existing project?** N
- **Project name?** `forgereach`
- **Directory with code?** `./` (you're already in `web/`)
- **Want to override the settings?** N

Vercel detects Next.js automatically.

### 2.3 Set the backend URL

Vercel dashboard → your project → **Settings → Environment Variables** → add:

```
NEXT_PUBLIC_API_URL=https://<your-railway-url>
```

(Use the URL from step 1.5. No trailing slash.)

Apply to **Production**, **Preview**, and **Development**.

### 2.4 Production deploy

```bash
vercel --prod
```

Vercel will give you two URLs:
- `https://forgereach.vercel.app` — production
- `https://forgereach-<hash>-<team>.vercel.app` — this specific deploy

Share the first one with the judges.

---

## Part 3: Post-Deploy Verification

Visit your Vercel URL and check:

1. **Config Health panel** — all four cards should reflect your Railway env vars. If OpenRouter shows "Missing" but you set the key, the frontend is probably pointing at the wrong backend — double-check `NEXT_PUBLIC_API_URL`.
2. **`/samples`** — loads 10 pre-generated examples with subject lines.
3. **Run a dry-run**: tick "Use sample file" → "Run Campaign Build". You should see live SSE progress (stage badges flip green), then results render with 12 contacts and downloadable CSVs.
4. **Run a live generation**: untick dry-run and re-run. Expect ~30–90 seconds for 12 contacts.
5. **EBITDA filter**: bump the slider to `$10,000,000` and run. Contacts without `annual_revenue` are kept; contacts with revenue below the threshold (revenue × 0.15) are dropped.

---

## Updating

After the first deploy, every `git push` to main triggers:
- Railway: auto-rebuild + redeploy backend
- Vercel: auto-build + deploy frontend to a preview URL (promote via dashboard or `vercel --prod`)

To disable auto-deploy on Railway: **Settings → Deploy → Deploy on push → Off**.

---

## Troubleshooting

**"Configured" shows Missing despite setting env vars.**
Restart the Railway service: dashboard → three-dot menu → Restart.

**CORS errors in the browser console.**
`backend/main.py` allows `https://*.vercel.app`. If your domain is custom, add it to the `allow_origin_regex` in `backend/main.py` and redeploy.

**SSE stream hangs.**
Railway's default proxy terminates idle connections at 30s. Long runs (100+ contacts) may need `--proxy-timeout` tuning or chunked heartbeat events. For the MVP sample size, this isn't an issue.

**Uploads lost between requests.**
Railway containers are ephemeral — uploads in `backend/uploads/` don't survive restarts. This is fine for single-session demos. For durability, swap to S3 / R2 (not implemented here).

**Build fails on Railway with "no space left on device".**
Restart the build: `railway up --detach`. Rare.

**Vercel build fails with TypeScript errors.**
Run `npm run build` locally in `web/` first to reproduce and fix.

---

## Costs

- Vercel Hobby: **$0** (sufficient for judge traffic).
- Railway Hobby: **$5/month credit**, which covers ~500 hours of a small container. The idle backend uses ~$3/month.
- OpenRouter: pay-per-call. `deepseek/deepseek-v3.2` runs about $0.0003 per 3-step sequence. 500 contacts = ~$0.15.

Total monthly for a live demo: **under $5**.
