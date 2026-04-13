"use client";
import * as React from "react";
import Link from "next/link";
import {
  ArrowRight,
  Check,
  Copy,
  Download,
  FileSpreadsheet,
  Globe,
  Mail,
  Play,
  Rocket,
  Search,
  Sparkles,
  Upload,
  Users,
  Wand2,
} from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

function CopyButton({ text, label }: { text: string; label?: string }) {
  const [copied, setCopied] = React.useState(false);
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  };
  return (
    <button
      type="button"
      onClick={onCopy}
      className="inline-flex items-center gap-1.5 rounded-md border bg-background px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? "Copied" : label || "Copy"}
    </button>
  );
}

function CodeBlock({ text }: { text: string }) {
  return (
    <div className="relative rounded-md border bg-muted/40 font-mono text-xs">
      <pre className="overflow-x-auto p-3 pr-20 leading-relaxed">{text}</pre>
      <div className="absolute right-2 top-2">
        <CopyButton text={text} />
      </div>
    </div>
  );
}

const STEPS = [
  {
    n: "01",
    icon: Upload,
    title: "Pick your input",
    body: "You have three options. Fastest is the built-in sample; most realistic is uploading a CSV; most powerful is API discovery.",
  },
  {
    n: "02",
    icon: Wand2,
    title: "Configure & run",
    body: "Choose target state, EBITDA floor, and audience. Hit Run. Watch the progress panel stream through ingest → classify → enrich → generate → validate.",
  },
  {
    n: "03",
    icon: Users,
    title: "Review the funnel",
    body: "The 4-KPI bar shows Total leads → Qualified targets → Emails verified → Outreach drafted. Click any contact row to see the full 3-step sequence.",
  },
  {
    n: "04",
    icon: Rocket,
    title: "Deploy",
    body: "Download the campaign CSV, push to Instantly with one click, import into Apollo, or open the first email straight into Outlook.",
  },
];

const HUNTER_DOMAINS = [
  "rockymtnroofing.com",
  "pritchettmech.com",
  "morenolandscape.com",
  "whitfieldelectric.com",
  "summitplumbing.co",
  "reevesconcrete.com",
];

const APOLLO_ENRICHMENT_EXAMPLE = `{
  "person": {
    "name": "Mike Torres",
    "title": "Owner / President",
    "company": "Rocky Mountain Roofing Co",
    "city": "Denver",
    "state": "CO",
    "email": "mike@rockymtnroofing.com",
    "email_status": "verified",
    "linkedin_url": "https://linkedin.com/in/miketorres-roofing"
  },
  "organization": {
    "employee_count": 42,
    "annual_revenue": 12000000,
    "industry": "Roofing",
    "founded_year": 1998,
    "website": "rockymtnroofing.com"
  }
}`;

const APIFY_LINKEDIN_EXAMPLE = `{
  "linkedin_url": "https://linkedin.com/in/miketorres-roofing",
  "headline": "Owner at Rocky Mountain Roofing | 20+ yrs Front Range Commercial Roofing",
  "about": "Third-generation roofer. We\\u2019ve grown from one truck in 1998 to 42 crew across Denver, Aurora, and Fort Collins. Quietly thinking about succession.",
  "experience": [
    { "title": "Owner / President", "company": "Rocky Mountain Roofing Co", "start": "2005-06" },
    { "title": "Foreman", "company": "Front Range Commercial Roofing", "start": "1998-03", "end": "2005-05" }
  ],
  "recent_posts": [
    "Hired our first full-time safety director. Best decision we\\u2019ve made in 5 years.",
    "2 new commercial bids closed this week \\u2014 both Class A industrial."
  ]
}`;

export default function TutorialPage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-4xl space-y-10 px-6 py-10">
        {/* Hero */}
        <section>
          <Badge variant="secondary" className="mb-3">
            <Sparkles className="mr-1 h-3 w-3" /> 5-minute walkthrough
          </Badge>
          <h1 className="text-3xl font-semibold tracking-tight">
            ForgeReach end-to-end tutorial
          </h1>
          <p className="mt-2 max-w-2xl text-muted-foreground">
            Follow this page and you'll have a reviewable, Instantly-ready outbound campaign
            in under five minutes. Sample data is provided for every step — no real keys or
            credentials required for the dry run.
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-2">
            <Button asChild>
              <Link href="/demo">
                <Play className="mr-1.5 h-4 w-4" /> Open the live demo
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <a href="/forgereach-sample-contacts.csv" download>
                <Download className="mr-1.5 h-4 w-4" /> Download sample CSV
              </a>
            </Button>
            <Button variant="ghost" asChild>
              <Link href="/samples">
                See sample outputs <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </section>

        {/* Overview steps */}
        <section className="grid gap-3 sm:grid-cols-2">
          {STEPS.map((s) => {
            const Icon = s.icon;
            return (
              <Card key={s.n} className="border-muted/60">
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-primary">
                      <Icon className="h-4 w-4" />
                    </span>
                    <div className="text-xs font-medium text-muted-foreground">
                      Step {s.n}
                    </div>
                  </div>
                  <CardTitle className="mt-1 text-base">{s.title}</CardTitle>
                </CardHeader>
                <CardContent className="pt-0 text-sm text-muted-foreground">
                  {s.body}
                </CardContent>
              </Card>
            );
          })}
        </section>

        <Separator />

        {/* Step 1 */}
        <section className="space-y-4">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">
              1. Pick your input
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Head to <Link href="/demo" className="underline">Demo</Link> and choose one of
              the three paths below. You can always run a second pass with a different input.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <Sparkles className="h-3.5 w-3.5" /> Fastest
                </div>
                <CardTitle className="text-base">Built-in sample</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm text-muted-foreground">
                <p>
                  Toggle <span className="font-medium text-foreground">Use sample file</span>
                  {" "}on the run form. 12 curated contacts, ready in seconds.
                </p>
                <Badge variant="outline" className="text-xs">No upload required</Badge>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <FileSpreadsheet className="h-3.5 w-3.5" /> Most realistic
                </div>
                <CardTitle className="text-base">Upload a CSV</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm text-muted-foreground">
                <p>
                  Drop our downloadable sample CSV or your own Apollo / LinkedIn / Hunter
                  export. Headers are fuzzy-matched automatically.
                </p>
                <Button size="sm" variant="outline" asChild>
                  <a href="/forgereach-sample-contacts.csv" download>
                    <Download className="mr-1.5 h-3.5 w-3.5" />
                    forgereach-sample-contacts.csv
                  </a>
                </Button>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <Globe className="h-3.5 w-3.5" /> Most powerful
                </div>
                <CardTitle className="text-base">API discovery</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm text-muted-foreground">
                <p>
                  Switch mode to <span className="font-medium text-foreground">API discovery</span>,
                  pick Hunter or Apollo, and pass a target state and domains.
                </p>
                <Badge variant="outline" className="text-xs">Needs API key</Badge>
              </CardContent>
            </Card>
          </div>

          <Card className="border-dashed">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Inside the sample CSV</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              <p className="mb-2">
                12 contacts — 6 blue-collar <span className="text-foreground">Owners</span>{" "}
                (roofing, HVAC, landscaping, electrical, plumbing, concrete) and 6{" "}
                <span className="text-foreground">Referral Advocates</span> (fractional CFOs,
                wealth advisors, CEPAs, EOS implementers, CPAs, commercial insurance brokers).
                All fictional.
              </p>
              <p>
                Columns: <code className="text-xs">First Name, Last Name, Title, Company,
                Email, Website, LinkedIn URL, City, State, Industry, Employee Count,
                Annual Revenue, Audience Type, Context</code>.
              </p>
            </CardContent>
          </Card>
        </section>

        <Separator />

        {/* Step 2: Hunter domains */}
        <section className="space-y-4">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">
              2. Try API discovery with Hunter
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              In <span className="font-medium text-foreground">API discovery</span> mode,
              select <span className="font-medium text-foreground">Hunter</span> as the source
              and paste the comma-separated domains below into{" "}
              <span className="font-medium text-foreground">Hunter domains</span>. State:{" "}
              <span className="font-medium text-foreground">CO</span>.
            </p>
          </div>

          <Card>
            <CardContent className="pt-4">
              <div className="mb-2 flex items-center justify-between">
                <div className="text-xs font-medium text-muted-foreground">
                  Example Hunter domains
                </div>
                <CopyButton text={HUNTER_DOMAINS.join(", ")} label="Copy all" />
              </div>
              <div className="flex flex-wrap gap-2">
                {HUNTER_DOMAINS.map((d) => (
                  <Badge key={d} variant="secondary" className="font-mono text-xs">
                    {d}
                  </Badge>
                ))}
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                Hunter returns verified emails for people listed at those domains. ForgeReach
                then classifies, fit-scores, and routes each contact into an outreach sequence.
              </p>
            </CardContent>
          </Card>

          <Card className="border-dashed">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-1.5">
                <Search className="h-4 w-4" /> Not seeing contacts return?
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>
                If fit scores come back low across the board, toggle{" "}
                <span className="text-foreground">Enrich with Apollo/Apify</span> and disable{" "}
                <span className="text-foreground">Require verified email</span> — blue-collar
                operators often don't have public verified emails.
              </p>
            </CardContent>
          </Card>
        </section>

        <Separator />

        {/* Step 3: Enrichment */}
        <section className="space-y-4">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">
              3. What enrichment looks like
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              When enrichment is enabled, ForgeReach hydrates each contact through two
              providers. Here is a sample of what each returns for one of our sample contacts.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Apollo person + organization</CardTitle>
              </CardHeader>
              <CardContent>
                <CodeBlock text={APOLLO_ENRICHMENT_EXAMPLE} />
                <p className="mt-2 text-xs text-muted-foreground">
                  Used to fill missing employee count, revenue, industry, and verified email.
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Apify LinkedIn profile</CardTitle>
              </CardHeader>
              <CardContent>
                <CodeBlock text={APIFY_LINKEDIN_EXAMPLE} />
                <p className="mt-2 text-xs text-muted-foreground">
                  Headline, about, experience, and recent posts flow into the personalization
                  facts block of the prompt.
                </p>
              </CardContent>
            </Card>
          </div>
        </section>

        <Separator />

        {/* Step 4: Results */}
        <section className="space-y-4">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">
              4. Read the results dashboard
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Once the run finishes you'll see a business-focused dashboard — not dev logs.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Business funnel (4 KPIs)</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Total leads processed → Qualified targets → Emails verified → Outreach
                drafted. Tells you at a glance where the pipeline narrowed.
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Contacts table</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Audience pill (Owner / Referral Advocate), fit indicator (High / Medium /
                Low), AI outreach preview with subject + first two sentences, and a status
                chip. Click any row to review or edit the full 3-step sequence.
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Deploy action bar</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Primary Download Campaign CSV, plus 1-click deploy to Instantly, Apollo, or
                Outlook. The Instantly dialog includes a copy-pastable CLI command.
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Developer logs</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Collapsed by default behind a <span className="font-mono">⚙︎ View developer
                logs</span> accordion. Everything technical lives there — timings, API
                counters, Apify attempts, validator failures.
              </CardContent>
            </Card>
          </div>
        </section>

        <Separator />

        {/* Step 5: Deploy */}
        <section className="space-y-4">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">
              5. Ship the campaign
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Pick whichever destination your team already uses.
            </p>
          </div>

          <Card>
            <CardContent className="space-y-3 pt-4 text-sm">
              <div className="flex items-start gap-3">
                <Rocket className="mt-0.5 h-4 w-4 text-primary" />
                <div>
                  <div className="font-medium">Instantly.ai</div>
                  <p className="text-muted-foreground">
                    Paste your Instantly campaign ID, hit Push, and we POST qualified leads in
                    batches of 50 with retry / Retry-After handling. Or run the printed CLI
                    command on a server.
                  </p>
                </div>
              </div>
              <Separator />
              <div className="flex items-start gap-3">
                <FileSpreadsheet className="mt-0.5 h-4 w-4 text-primary" />
                <div>
                  <div className="font-medium">Apollo</div>
                  <p className="text-muted-foreground">
                    Download the trimmed Instantly CSV and import straight into an Apollo
                    sequence — column headers align out of the box.
                  </p>
                </div>
              </div>
              <Separator />
              <div className="flex items-start gap-3">
                <Mail className="mt-0.5 h-4 w-4 text-primary" />
                <div>
                  <div className="font-medium">Outlook (single-send test)</div>
                  <p className="text-muted-foreground">
                    One-click opens the first ready contact in a{" "}
                    <span className="font-mono">mailto:</span> draft — perfect for sanity-
                    checking voice and formatting before rolling out.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* CTA */}
        <section className="rounded-xl border bg-muted/30 p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold tracking-tight">Ready to try it?</h3>
              <p className="text-sm text-muted-foreground">
                The fastest path: open the demo, toggle the built-in sample, hit Run.
              </p>
            </div>
            <div className="flex gap-2">
              <Button asChild>
                <Link href="/demo">
                  <Play className="mr-1.5 h-4 w-4" /> Go to demo
                </Link>
              </Button>
              <Button variant="outline" asChild>
                <a href="/forgereach-sample-contacts.csv" download>
                  <Download className="mr-1.5 h-4 w-4" /> Sample CSV
                </a>
              </Button>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
