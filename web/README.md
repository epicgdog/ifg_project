# ForgeReach Web

Next.js 14 (App Router) + Tailwind + shadcn/ui dashboard for the ForgeReach outbound pipeline.

## Stack

- Next.js 14, App Router, TypeScript
- Tailwind CSS + shadcn/ui primitives
- TanStack Query v5
- Native `EventSource` for SSE live progress
- `react-dropzone`, `recharts`, `papaparse`, `lucide-react`

## Local dev

```bash
cd web
cp .env.local.example .env.local   # edit if backend not on :8000
npm install
npm run dev
```

Open http://localhost:3000.

### Environment

| Var | Default | Notes |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | FastAPI backend base URL |

With the backend offline the dashboard still renders; Config Health badges show `Offline`/`Missing`.

## Pages

- `/` — main dashboard: config health, run form, live SSE progress, results, downloads.
- `/samples` — gallery of sample sequences (public, no run required).

## Build

```bash
npm run build      # type-check + next build
npm run type-check # tsc --noEmit
```

## Deploy to Vercel

This frontend lives in a subdirectory of the monorepo. In Vercel project settings set:

- **Root Directory** = `web`
- **Framework Preset** = Next.js (auto-detected)
- **Environment Variables** → `NEXT_PUBLIC_API_URL` → your deployed FastAPI URL

Then:

```bash
cd web
vercel --prod
```

`vercel.json` is kept minimal; Vercel infers the build.

## Directory layout

```
web/
├── app/                    # App Router pages
│   ├── layout.tsx
│   ├── page.tsx            # dashboard
│   ├── samples/page.tsx
│   └── globals.css
├── components/
│   ├── ui/                 # shadcn primitives (button, card, ...)
│   ├── config-health.tsx
│   ├── run-form.tsx
│   ├── progress-panel.tsx
│   ├── results-panel.tsx
│   ├── contact-table.tsx
│   ├── sequence-drawer.tsx
│   ├── sample-card.tsx
│   ├── metric-card.tsx
│   ├── mode-badge.tsx
│   ├── providers.tsx
│   ├── site-header.tsx
│   └── theme-toggle.tsx
├── hooks/
│   ├── use-config-health.ts
│   └── use-run.ts
├── lib/
│   ├── api.ts              # typed fetch wrappers
│   ├── sse.ts              # useRunStream SSE hook
│   ├── csv.ts              # papaparse wrapper
│   ├── types.ts            # API contract types
│   └── utils.ts
├── components.json         # shadcn config
├── tailwind.config.ts
├── tsconfig.json
├── next.config.mjs
├── postcss.config.mjs
├── vercel.json
├── .env.local.example
└── package.json
```
