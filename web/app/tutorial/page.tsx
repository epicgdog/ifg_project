"use client";
import * as React from "react";
import Link from "next/link";
import {
  ArrowRight,
  Briefcase,
  CheckCircle2,
  Play,
  Sparkles,
  UserPlus,
  Users,
} from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useConfigHealth } from "@/hooks/use-config-health";
import { cn } from "@/lib/utils";

type SourceKey = "hunter" | "apollo" | "linkedin_sales_nav";

function JourneyStep({
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
      label: string;
      status: boolean;
      businessFit: string;
      setupText: string;
      quickStart: string;
    }
  > = {
    hunter: {
      label: "Hunter",
      status: !!data?.hunter,
      businessFit: "Best for verified-email-first prospecting from known target domains.",
      setupText: "Connect Hunter once, then use domain lists to generate contactable leads quickly.",
      quickStart: "In Demo: Find New Leads -> Source: Hunter -> Add target domains.",
    },
    apollo: {
      label: "Apollo",
      status: !!data?.apollo,
      businessFit: "Best for broad lead generation by title, industry, and company profile.",
      setupText: "Use Apollo when you need volume and richer account context.",
      quickStart: "In Demo: Find New Leads -> Source: Apollo -> Set audience and launch.",
    },
    linkedin_sales_nav: {
      label: "LinkedIn Sales Navigator",
      status: !!data?.sales_navigator,
      businessFit: "Best for finding high-value people and leadership context.",
      setupText: "Use title and company seed terms to guide people discovery.",
      quickStart:
        "In Demo: Find New Leads -> Source: LinkedIn Sales Navigator -> Add seed titles/companies.",
    },
  };

  const selected = sourceGuides[source];
  const launchReady = !!data?.openrouter && !!data?.serper && selected.status;

  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-5xl space-y-8 px-6 py-10">
        <section className="space-y-3">
          <Badge variant="secondary">
            <Sparkles className="mr-1 h-3 w-3" /> Campaign Launchpad
          </Badge>
          <h1 className="text-3xl font-semibold tracking-tight">Executive launch flow</h1>
          <p className="text-sm text-muted-foreground max-w-3xl">
            This page is designed for business leaders: choose your target source, set AI
            strategy, preview outcomes, and launch campaigns without technical setup complexity.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button asChild>
              <Link href="/demo">
                <Play className="mr-1.5 h-4 w-4" /> Open Campaign Launchpad
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/samples">
                Preview sample outputs <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </section>

        <section className="grid gap-3 md:grid-cols-4">
          <JourneyStep
            number="01"
            title="Define target"
            body="Choose where leads come from and align to your current GTM motion."
            done={selected.status}
          />
          <JourneyStep
            number="02"
            title="Set AI strategy"
            body="Pick research depth based on speed vs. personalization quality."
            done={!!data?.openrouter}
          />
          <JourneyStep
            number="03"
            title="Preview business output"
            body="Validate evidence-backed drafts before full deployment."
            done={!!data?.serper}
          />
          <JourneyStep
            number="04"
            title="Launch readiness"
            body="Confirm infrastructure and move into campaign execution."
            done={launchReady}
          />
        </section>

        <Separator />

        <section className="space-y-4">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-primary" />
            <h2 className="text-xl font-semibold tracking-tight">1) Define the target</h2>
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
              <CardTitle className="flex items-center justify-between text-base">
                <span>{selected.label}</span>
                <Badge variant={selected.status ? "success" : "muted"}>
                  {selected.status ? "Connected" : "Needs setup"}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p><span className="font-medium text-foreground">Business fit:</span> {selected.businessFit}</p>
              <p><span className="font-medium text-foreground">How to use:</span> {selected.setupText}</p>
              <p><span className="font-medium text-foreground">Quick start:</span> {selected.quickStart}</p>
            </CardContent>
          </Card>
        </section>

        <Separator />

        <section className="space-y-4">
          <div className="flex items-center gap-2">
            <Briefcase className="h-4 w-4 text-primary" />
            <h2 className="text-xl font-semibold tracking-tight">2) Set AI strategy</h2>
          </div>
          <Card>
            <CardContent className="pt-4 text-sm text-muted-foreground space-y-2">
              <p>- In Demo, choose <span className="text-foreground">Research Quality: Standard or Deep Analysis</span>.</p>
              <p>- Deep analysis gives stronger personalization and better executive-level relevance.</p>
              <p>- Keep <span className="text-foreground">Contact Readiness Filter</span> on to protect rep time.</p>
            </CardContent>
          </Card>
        </section>

        <Separator />

        <section className="space-y-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <h2 className="text-xl font-semibold tracking-tight">3) Preview drafts and ROI</h2>
          </div>
          <Card>
            <CardContent className="pt-4 text-sm text-muted-foreground space-y-2">
              <p>- Open results and verify: sourced leads to qualified targets to contactable leads to drafts ready.</p>
              <p>- Spot-check evidence-backed personalization in the sequence drawer before launch.</p>
              <p>- Use business impact cards to communicate time saved and conversion to leadership.</p>
            </CardContent>
          </Card>
        </section>

        <Separator />

        <section className="space-y-4">
          <div className="flex items-center gap-2">
            <UserPlus className="h-4 w-4 text-primary" />
            <h2 className="text-xl font-semibold tracking-tight">4) Connect infrastructure (delegate if needed)</h2>
          </div>
          <Card>
            <CardContent className="pt-4 text-sm text-muted-foreground space-y-2">
              <p>- Click the header settings button to review connection status for all systems.</p>
              <p>- If keys are missing, use the built-in <span className="text-foreground">Invite IT/admin to configure</span> action.</p>
              <p>- Once connected, campaign managers can run weekly without touching technical setup.</p>
            </CardContent>
          </Card>
        </section>

        <section className="rounded-xl border bg-muted/30 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold tracking-tight">Ready to launch?</h3>
              <p className="text-sm text-muted-foreground">
                Open the Campaign Launchpad and run your first executive-ready pipeline.
              </p>
            </div>
            <Button asChild>
              <Link href="/demo">
                <Play className="mr-1.5 h-4 w-4" /> Go to Launchpad
              </Link>
            </Button>
          </div>
        </section>
      </main>
    </>
  );
}
