"use client";
import * as React from "react";
import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  Copy,
  Play,
  Puzzle,
  Search,
  Settings2,
  Sparkles,
  Upload,
} from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useConfigHealth } from "@/hooks/use-config-health";
import { cn } from "@/lib/utils";

type SourceKey = "hunter" | "apollo" | "linkedin_sales_nav";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = React.useState(false);
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // noop
    }
  };
  return (
    <button
      type="button"
      onClick={onCopy}
      className="inline-flex items-center gap-1.5 rounded-md border bg-background px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground"
    >
      {copied ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function StepCard({
  number,
  title,
  body,
  done,
}: {
  number: string;
  title: string;
  body: string;
  done: boolean;
}) {
  return (
    <Card className={cn("border-muted/60", done && "border-emerald-300 bg-emerald-50/40")}> 
      <CardHeader className="pb-2">
        <div className="text-xs font-medium text-muted-foreground">Step {number}</div>
        <CardTitle className="text-base flex items-center gap-2">
          {done && <CheckCircle2 className="h-4 w-4 text-emerald-600" />} {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0 text-sm text-muted-foreground">{body}</CardContent>
    </Card>
  );
}

export default function TutorialPage() {
  const { data } = useConfigHealth();
  const [source, setSource] = React.useState<SourceKey>("hunter");

  const sourceGuides: Record<
    SourceKey,
    {
      name: string;
      status: boolean;
      needs: string;
      demoSetting: string;
      why: string;
      queryExample: string;
    }
  > = {
    hunter: {
      name: "Hunter",
      status: !!data?.hunter,
      needs: "HUNTER_API_KEY",
      demoSetting: "Mode: API discovery | Sources: Hunter | Add domains",
      why: "Fast route to verified emails from known domains.",
      queryExample: "Domains: rockymtnroofing.com, summitplumbing.co",
    },
    apollo: {
      name: "Apollo",
      status: !!data?.apollo,
      needs: "APOLLO_API_KEY + plan access for mixed_people/search",
      demoSetting: "Mode: API discovery | Sources: Apollo",
      why: "Best for broad title + company discovery when plan allows people search.",
      queryExample:
        "Titles: owner, founder, ceo, advisor | Industry keywords: roofing, hvac, construction",
    },
    linkedin_sales_nav: {
      name: "LinkedIn Sales Navigator",
      status: !!data?.sales_navigator,
      needs: "SERPER_API_KEY (Sales Nav-style search operators)",
      demoSetting: "Mode: API discovery | Sources: LinkedIn Sales Navigator",
      why: "Strong for finding people pages and leadership context quickly.",
      queryExample:
        'site:linkedin.com/in "fractional cfo" "Colorado" OR site:linkedin.com/in "owner" "construction"',
    },
  };

  const selected = sourceGuides[source];

  const envSnippet = `OPENROUTER_API_KEY=...\nOPENROUTER_MODEL=deepseek/deepseek-v3.2\nOPENROUTER_RESEARCH_MODEL=deepseek/deepseek-v3.2\nSERPER_API_KEY=...\nHUNTER_API_KEY=...\nAPOLLO_API_KEY=...\nAPIFY_API_TOKEN=...\nAPIFY_LINKEDIN_ACTOR_ID=...`;

  const runChecklist = [
    !!data?.openrouter,
    !!data?.serper,
    selected.status,
  ];

  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-5xl space-y-8 px-6 py-10">
        <section className="space-y-3">
          <Badge variant="secondary">
            <Sparkles className="mr-1 h-3 w-3" /> Interactive setup guide
          </Badge>
          <h1 className="text-3xl font-semibold tracking-tight">Demo setup tutorial</h1>
          <p className="text-sm text-muted-foreground max-w-3xl">
            This walkthrough is now operational: pick your integration source, verify keys, run
            discovery, and validate that research signals flow into personalized drafts.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button asChild>
              <Link href="/demo">
                <Play className="mr-1.5 h-4 w-4" /> Open demo
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/samples">
                View samples <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </section>

        <section className="grid gap-3 md:grid-cols-3">
          <StepCard
            number="01"
            title="Configure keys"
            body="Set OpenRouter + Serper, then at least one prospect source (Hunter, Apollo, or Sales Nav)."
            done={!!data?.openrouter && !!data?.serper}
          />
          <StepCard
            number="02"
            title="Choose source"
            body="Use source-specific discovery based on your data and access level."
            done={selected.status}
          />
          <StepCard
            number="03"
            title="Run and verify"
            body="Check live activity feed and evidence hooks in sequence drawer before deploying."
            done={runChecklist.every(Boolean)}
          />
        </section>

        <Separator />

        <section className="space-y-4">
          <div className="flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-primary" />
            <h2 className="text-xl font-semibold tracking-tight">1) Environment setup</h2>
          </div>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">.env template</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="relative rounded-md border bg-muted/40 font-mono text-xs">
                <pre className="overflow-x-auto p-3 pr-20 leading-relaxed">{envSnippet}</pre>
                <div className="absolute right-2 top-2">
                  <CopyButton text={envSnippet} />
                </div>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                Minimum for research pipeline: <code>OPENROUTER_API_KEY</code> + <code>SERPER_API_KEY</code>.
              </p>
            </CardContent>
          </Card>
        </section>

        <Separator />

        <section className="space-y-4">
          <div className="flex items-center gap-2">
            <Puzzle className="h-4 w-4 text-primary" />
            <h2 className="text-xl font-semibold tracking-tight">2) Pick integration path</h2>
          </div>

          <div className="flex flex-wrap gap-2">
            {([
              ["hunter", "Hunter"],
              ["apollo", "Apollo"],
              ["linkedin_sales_nav", "LinkedIn Sales Navigator"],
            ] as const).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setSource(key)}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs font-medium",
                  source === key
                    ? "border-primary bg-primary/10 text-foreground"
                    : "border-border text-muted-foreground hover:text-foreground"
                )}
              >
                {label}
              </button>
            ))}
          </div>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center justify-between">
                <span>{selected.name}</span>
                <Badge variant={selected.status ? "success" : "muted"}>
                  {selected.status ? "Configured" : "Missing key"}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p><span className="font-medium">Required:</span> {selected.needs}</p>
              <p><span className="font-medium">Demo setting:</span> {selected.demoSetting}</p>
              <p><span className="font-medium">Why use it:</span> {selected.why}</p>
              <div className="rounded-md border bg-muted/30 p-2 text-xs font-mono">
                {selected.queryExample}
              </div>
            </CardContent>
          </Card>
        </section>

        <Separator />

        <section className="space-y-4">
          <div className="flex items-center gap-2">
            <Upload className="h-4 w-4 text-primary" />
            <h2 className="text-xl font-semibold tracking-tight">3) Run in demo</h2>
          </div>
          <Card>
            <CardContent className="pt-4 text-sm text-muted-foreground space-y-2">
              <p>In <Link href="/demo" className="underline">Demo</Link>:</p>
              <p>- Mode: <span className="text-foreground">API discovery</span> or <span className="text-foreground">CSV + API</span></p>
              <p>- Source: select <span className="text-foreground">{selected.name}</span></p>
              <p>- Keep <span className="text-foreground">Agentic research = ON</span> and set depth to <span className="text-foreground">Deep</span></p>
              <p>- Watch <span className="text-foreground">Live activity</span> for exact operations (queries, scraping, email lookup)</p>
            </CardContent>
          </Card>
        </section>

        <Separator />

        <section className="space-y-4">
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 text-primary" />
            <h2 className="text-xl font-semibold tracking-tight">4) Verify personalization quality</h2>
          </div>
          <Card>
            <CardContent className="pt-4 text-sm text-muted-foreground space-y-2">
              <p>- Open a contact row in Results.</p>
              <p>- Confirm <span className="text-foreground">Research evidence</span> shows grounded pages + hooks.</p>
              <p>- Check step 1 or 2 references a concrete research signal (not generic fluff).</p>
              <p>- If weak, increase depth or switch source (Apollo/Sales Nav often improves person context).</p>
            </CardContent>
          </Card>
        </section>

        <section className="rounded-xl border bg-muted/30 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold tracking-tight">Ready to run it now?</h3>
              <p className="text-sm text-muted-foreground">
                Open demo, pick source, run deep research, then review evidence-backed drafts.
              </p>
            </div>
            <Button asChild>
              <Link href="/demo">
                <Play className="mr-1.5 h-4 w-4" /> Go to demo
              </Link>
            </Button>
          </div>
        </section>
      </main>
    </>
  );
}
