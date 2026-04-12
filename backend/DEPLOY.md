# Deploying the ForgeReach backend to Railway

These steps deploy the FastAPI backend (`backend/`) as a containerized
service on Railway. The Next.js frontend on Vercel then points at the
Railway URL via `NEXT_PUBLIC_API_URL`.

## Prerequisites

- Railway CLI: `npm i -g @railway/cli`
- GitHub repo pushed with this `backend/` directory at the root

## Steps

1. **Push the repo to GitHub** (make sure `backend/`, `src/`, `data/`, and
   `MASTER.md` are all committed).

2. **Log in** to Railway from the CLI:
   ```bash
   railway login
   ```

3. **Initialize** a project from the repo root (select
   `Empty Project` when prompted):
   ```bash
   railway init
   ```

4. **Link** the local workspace to the newly created project:
   ```bash
   railway link
   ```

5. **Set environment variables** via the Railway dashboard (Variables tab):
   - `OPENROUTER_API_KEY` (required)
   - `OPENROUTER_MODEL` (e.g., `deepseek/deepseek-v3.2`)
   - `APOLLO_API_KEY` (optional — enables Apollo prospecting/enrichment)
   - `HUNTER_API_KEY` (optional — enables Hunter domain search)
   - `APIFY_API_TOKEN` (optional — enables LinkedIn enrichment)
   - `APIFY_LINKEDIN_ACTOR_ID` (optional — pairs with `APIFY_API_TOKEN`)

6. **Point the build at the Dockerfile.** In the Railway service settings,
   set `Dockerfile Path` to `backend/Dockerfile` (or rely on
   `backend/railway.json`, which already specifies it).

7. **Deploy**:
   ```bash
   railway up
   ```

8. **Grab the URL.** Railway assigns a `*.up.railway.app` domain. Copy it
   and set it as `NEXT_PUBLIC_API_URL` in your Vercel project — the
   backend's CORS config already whitelists `https://*.vercel.app`.

## Verifying a deployment

```bash
curl https://<your-service>.up.railway.app/
curl https://<your-service>.up.railway.app/api/config/health
```

The health endpoint should report which provider keys Railway has loaded.
