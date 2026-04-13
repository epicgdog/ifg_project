"use client";
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Download,
  Send,
  Mail,
  Rocket,
  ChevronDown,
  ChevronUp,
  Users,
  Target,
  MailCheck,
  Sparkles,
  Copy,
  ExternalLink,
  Check,
  Settings,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MetricCard } from "@/components/metric-card";
import { ContactTable } from "@/components/contact-table";
import { SequenceDrawer } from "@/components/sequence-drawer";
import {
  csvDownloadUrl,
  getCampaignCsv,
  instantlyDownloadUrl,
} from "@/lib/api";
import { parseContactsCsv } from "@/lib/csv";
import type { ContactRow, DoneEvent } from "@/lib/types";

function numMetric(report: DoneEvent["report"], keys: string[]): number {
  for (const k of keys) {
    const v = report?.[k];
    if (typeof v === "number") return v;
    if (typeof v === "string") {
      const n = Number(v);
      if (Number.isFinite(n)) return n;
    }
  }
  return 0;
}

function pickMetric(
  report: DoneEvent["report"],
  keys: string[]
): string | number {
  for (const k of keys) {
    const v = report?.[k];
    if (typeof v === "number" || typeof v === "string") return v;
  }
  return "—";
}

export function ResultsPanel({ done }: { done: DoneEvent }) {
  const [selected, setSelected] = React.useState<ContactRow | null>(null);
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [devOpen, setDevOpen] = React.useState(false);
  const [reportOpen, setReportOpen] = React.useState(false);
  const [instantlyOpen, setInstantlyOpen] = React.useState(false);
  const [apolloOpen, setApolloOpen] = React.useState(false);
  const [outlookOpen, setOutlookOpen] = React.useState(false);

  const csvQuery = useQuery({
    queryKey: ["campaign-csv", done.run_id],
    queryFn: () => getCampaignCsv(done.run_id),
    enabled: !!done.run_id,
  });

  const rows: ContactRow[] = React.useMemo(
    () => (csvQuery.data ? parseContactsCsv(csvQuery.data) : []),
    [csvQuery.data]
  );

  const audienceData = React.useMemo(() => {
    const counts = { owner: 0, referral: 0 };
    for (const r of rows) {
      const isRef = (r.audience || "").toLowerCase().includes("referral");
      if (isRef) counts.referral += 1;
      else counts.owner += 1;
    }
    return [
      { name: "Owner", count: counts.owner },
      { name: "Referral Advocate", count: counts.referral },
    ];
  }, [rows]);

  const r = done.report || {};

  const total = numMetric(r, ["total", "total_contacts"]);
  const qualified = numMetric(r, ["qualified", "qualified_count"]);
  const emailsVerified = numMetric(r, ["research_emails_verified"]);
  const outreachDrafted = rows.length;

  return (
    <div className="space-y-6">
      <div>
        <div className="mb-3 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">
              Campaign results
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Personalized 3-step sequences generated in Kory Mitchell's voice.
              Review below, then deploy to your sending tool of choice.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Total leads processed"
            value={total}
            hint="Contacts ingested this run"
            icon={<Users className="h-5 w-5" />}
            accent="sky"
          />
          <MetricCard
            label="Qualified targets"
            value={qualified}
            hint="Met $3M+ EBITDA proxy or RA criteria"
            icon={<Target className="h-5 w-5" />}
            accent="emerald"
          />
          <MetricCard
            label="Emails verified"
            value={emailsVerified}
            hint="Deliverable contact emails found"
            icon={<MailCheck className="h-5 w-5" />}
            accent="violet"
          />
          <MetricCard
            label="Outreach drafted"
            value={outreachDrafted}
            hint="3-step sequences written in Kory's voice"
            icon={<Sparkles className="h-5 w-5" />}
            accent="amber"
          />
        </div>
      </div>

      <Card className="border-primary/30 bg-gradient-to-br from-primary/5 via-transparent to-transparent">
        <CardContent className="flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Rocket className="h-5 w-5" />
            </div>
            <div>
              <div className="text-sm font-semibold">Deploy this campaign</div>
              <div className="text-xs text-muted-foreground">
                Download or push directly into your sending tool.
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <a href={csvDownloadUrl(done.run_id)} download>
              <Button variant="default" className="gap-2">
                <Download className="h-4 w-4" />
                Download Campaign CSV
              </Button>
            </a>

            <span className="mx-1 hidden text-xs font-medium uppercase tracking-wider text-muted-foreground md:inline">
              1-click deploy
            </span>

            <div className="flex items-center gap-1.5 rounded-lg border bg-background p-1 shadow-sm">
              <Button
                variant="ghost"
                size="sm"
                className="gap-2"
                onClick={() => setInstantlyOpen(true)}
              >
                <Send className="h-4 w-4 text-sky-600" />
                Push to Instantly.ai
              </Button>
              <span className="h-5 w-px bg-border" aria-hidden />
              <Button
                variant="ghost"
                size="sm"
                className="gap-2"
                onClick={() => setApolloOpen(true)}
              >
                <Rocket className="h-4 w-4 text-orange-600" />
                Sync to Apollo.io
              </Button>
              <span className="h-5 w-px bg-border" aria-hidden />
              <Button
                variant="ghost"
                size="sm"
                className="gap-2"
                onClick={() => setOutlookOpen(true)}
              >
                <Mail className="h-4 w-4 text-indigo-600" />
                Send to Outlook Drafts
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
          <div>
            <CardTitle>Contacts</CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              Click a row to review and edit the full 3-step sequence.
            </p>
          </div>
        </CardHeader>
        <CardContent>
          {csvQuery.isLoading ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              Loading contacts…
            </div>
          ) : csvQuery.isError ? (
            <div className="text-sm text-red-500">
              Failed to load CSV: {(csvQuery.error as Error).message}
            </div>
          ) : (
            <ContactTable
              rows={rows}
              onSelect={(row) => {
                setSelected(row);
                setDrawerOpen(true);
              }}
            />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Audience split</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={audienceData}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar
                  dataKey="count"
                  fill="hsl(var(--primary))"
                  radius={[6, 6, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <SequenceDrawer
        contact={selected}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
      />

      {/* Developer logs — collapsed by default */}
      <Card>
        <CardHeader>
          <button
            type="button"
            onClick={() => setDevOpen((v) => !v)}
            className="flex w-full items-center justify-between gap-2 text-left"
          >
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Settings className="h-4 w-4" />
              View developer logs
            </CardTitle>
            {devOpen ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            )}
          </button>
        </CardHeader>
        {devOpen && (
          <CardContent className="space-y-6">
            <div className="rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground">
              <div className="font-medium text-foreground">Quality gate applied</div>
              <div className="mt-1 font-mono">
                {typeof r.quality_gate_formula === "string"
                  ? r.quality_gate_formula
                  : "verified_email && (linkedin || decision_maker_name)"}
              </div>
              <div className="mt-1">
                verified email:{" "}
                {r.require_verified_email === false ? "optional" : "required"} |
                identity:{" "}
                {r.require_identity_confirmation === false
                  ? " optional"
                  : " required"}
              </div>
            </div>

            <div>
              <div className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Pipeline metrics
              </div>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <MetricCard
                  label="Skipped (low fit)"
                  value={pickMetric(r, ["skipped_low_fit_count"])}
                />
                <MetricCard
                  label="Skipped (no identity)"
                  value={pickMetric(r, ["skipped_no_identity_count"])}
                />
                <MetricCard
                  label="Skipped (unverified)"
                  value={pickMetric(r, ["skipped_unverified_email_count"])}
                />
                <MetricCard
                  label="Enriched"
                  value={pickMetric(r, ["enriched", "enriched_count"])}
                />
                <MetricCard
                  label="High priority"
                  value={pickMetric(r, ["high_priority", "high_priority_count"])}
                />
                <MetricCard
                  label="Review flagged"
                  value={pickMetric(r, [
                    "review_flagged",
                    "review_flagged_count",
                    "review_flag_count",
                  ])}
                />
                <MetricCard
                  label="Avg fit score"
                  value={pickMetric(r, ["avg_fit_score", "average_fit_score"])}
                />
                <MetricCard
                  label="Discovered"
                  value={pickMetric(r, ["discovered_count"])}
                />
              </div>
            </div>

            <div>
              <div className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Discovery
              </div>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <MetricCard
                  label="Apollo attempts"
                  value={pickMetric(r, ["apollo_search_attempts"])}
                />
                <MetricCard
                  label="Apollo failures"
                  value={pickMetric(r, ["apollo_search_failures"])}
                />
                <MetricCard
                  label="Apollo empty batches"
                  value={pickMetric(r, ["apollo_empty_batches"])}
                />
                <MetricCard
                  label="Fallback successes"
                  value={pickMetric(r, ["apollo_fallback_successes"])}
                />
              </div>
              {Array.isArray(r.discovery_errors) && r.discovery_errors.length > 0 && (
                <div className="mt-3 rounded-md border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">
                  <div className="mb-1 font-medium">Discovery errors</div>
                  {r.discovery_errors.map((err, idx) => (
                    <div key={`${idx}-${err}`} className="leading-relaxed">
                      - {err}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div>
              <div className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Agentic research
              </div>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <MetricCard
                  label="Contacts researched"
                  value={pickMetric(r, ["research_contacts_processed"])}
                />
                <MetricCard
                  label="Serper queries"
                  value={pickMetric(r, ["research_queries_serper"])}
                />
                <MetricCard
                  label="Websites scraped"
                  value={pickMetric(r, ["research_websites_scraped"])}
                />
                <MetricCard
                  label="DMs identified"
                  value={pickMetric(r, ["research_decision_makers_found"])}
                />
                <MetricCard
                  label="Avg audience confidence"
                  value={pickMetric(r, ["avg_audience_confidence"])}
                />
                <MetricCard
                  label="Avg maturity score"
                  value={pickMetric(r, ["avg_company_maturity_score"])}
                />
                <MetricCard
                  label="Company summaries"
                  value={pickMetric(r, [
                    "research_company_summaries_extracted",
                  ])}
                />
                <MetricCard
                  label="Emails found"
                  value={pickMetric(r, ["research_emails_found"])}
                />
              </div>
            </div>

            <div>
              <div className="mb-2 flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setReportOpen((v) => !v)}
                  className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground"
                >
                  Raw run report
                  {reportOpen ? (
                    <ChevronUp className="h-3 w-3" />
                  ) : (
                    <ChevronDown className="h-3 w-3" />
                  )}
                </button>
                <a
                  href={instantlyDownloadUrl(done.run_id)}
                  download
                  className="ml-auto text-xs text-muted-foreground underline-offset-2 hover:underline"
                >
                  Download instantly_campaign.csv
                </a>
              </div>
              {reportOpen && (
                <pre className="max-h-96 overflow-auto rounded-md border bg-muted/30 p-4 text-xs leading-relaxed">
                  {JSON.stringify(done.report, null, 2)}
                </pre>
              )}
            </div>
          </CardContent>
        )}
      </Card>

      <InstantlyDialog
        open={instantlyOpen}
        onOpenChange={setInstantlyOpen}
        runId={done.run_id}
        qualifiedCount={qualified || outreachDrafted}
      />
      <ApolloDialog open={apolloOpen} onOpenChange={setApolloOpen} runId={done.run_id} />
      <OutlookDialog
        open={outlookOpen}
        onOpenChange={setOutlookOpen}
        rows={rows}
      />
    </div>
  );
}

function CopyableCommand({ command }: { command: string }) {
  const [copied, setCopied] = React.useState(false);
  return (
    <div className="flex items-center gap-2 rounded-md border bg-muted/40 p-2">
      <code className="flex-1 overflow-x-auto whitespace-nowrap font-mono text-xs text-foreground">
        {command}
      </code>
      <Button
        size="sm"
        variant="ghost"
        className="gap-1.5"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(command);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          } catch {
            // noop
          }
        }}
      >
        {copied ? (
          <>
            <Check className="h-3.5 w-3.5" /> Copied
          </>
        ) : (
          <>
            <Copy className="h-3.5 w-3.5" /> Copy
          </>
        )}
      </Button>
    </div>
  );
}

function InstantlyDialog({
  open,
  onOpenChange,
  runId,
  qualifiedCount,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  runId: string;
  qualifiedCount: number;
}) {
  const [campaignId, setCampaignId] = React.useState("");
  const command = campaignId
    ? `python -m src.main --input /tmp/${runId}.csv --output out/${runId}_campaign.csv --push-instantly ${campaignId}`
    : "";
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Send className="h-5 w-5 text-sky-600" />
            Push to Instantly.ai
          </DialogTitle>
          <DialogDescription>
            Upload {qualifiedCount} qualified leads + personalized sequences
            directly into an Instantly campaign. Requires{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">INSTANTLY_API_KEY</code>{" "}
            in your environment.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="instantly-campaign">Instantly campaign ID</Label>
            <Input
              id="instantly-campaign"
              placeholder="e.g. 01931a...-b3f2"
              value={campaignId}
              onChange={(e) => setCampaignId(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Find this in your Instantly dashboard under Campaigns → Settings.
            </p>
          </div>
          {campaignId ? (
            <div className="space-y-1.5">
              <Label>Run this from the repo root</Label>
              <CopyableCommand command={command} />
            </div>
          ) : null}
        </div>
        <DialogFooter className="flex-row items-center justify-between sm:justify-between">
          <a
            href="https://app.instantly.ai/app/campaigns"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Open Instantly
          </a>
          <Button onClick={() => onOpenChange(false)}>Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ApolloDialog({
  open,
  onOpenChange,
  runId,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  runId: string;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Rocket className="h-5 w-5 text-orange-600" />
            Sync to Apollo.io sequences
          </DialogTitle>
          <DialogDescription>
            Apollo sequences require an Apollo Pro plan. Export the campaign CSV
            and import it from Apollo → Sequences → Add contacts → Upload CSV.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <a href={csvDownloadUrl(runId)} download>
            <Button variant="default" className="w-full gap-2">
              <Download className="h-4 w-4" />
              Download Apollo-ready CSV
            </Button>
          </a>
          <p className="text-xs text-muted-foreground">
            Apollo's native CSV import auto-maps first_name, last_name, email,
            company, and title. Subject lines and step bodies land as custom
            variables.
          </p>
        </div>
        <DialogFooter>
          <a
            href="https://app.apollo.io/#/sequences"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Open Apollo
          </a>
          <Button onClick={() => onOpenChange(false)}>Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function OutlookDialog({
  open,
  onOpenChange,
  rows,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  rows: ContactRow[];
}) {
  const readyRows = rows.filter(
    (r) =>
      r.email &&
      String(r.email).includes("@") &&
      (!r.review_flag ||
        ["", "false", "no", "0"].includes(String(r.review_flag).toLowerCase()))
  );
  const first = readyRows[0];
  const mailto = first
    ? `mailto:${encodeURIComponent(String(first.email))}?subject=${encodeURIComponent(
        String(first.subject_1 || "")
      )}&body=${encodeURIComponent(String(first.email_step_1 || ""))}`
    : "";
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-indigo-600" />
            Send to Outlook Drafts
          </DialogTitle>
          <DialogDescription>
            Open the first {readyRows.length === 0 ? "" : "of "}
            <span className="font-medium text-foreground">{readyRows.length}</span>{" "}
            ready sequences as an Outlook / default-mail draft. For batch
            drafting, install the Microsoft Graph connector (coming soon).
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          {first ? (
            <a href={mailto}>
              <Button variant="default" className="w-full gap-2">
                <Mail className="h-4 w-4" />
                Draft email to {first.full_name || first.email}
              </Button>
            </a>
          ) : (
            <div className="rounded-md border bg-muted/40 p-3 text-xs text-muted-foreground">
              No ready-to-send contacts yet. Clear review flags or add verified
              emails first.
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            The link uses your system's default mail handler. If Outlook is
            configured, it opens a new draft pre-filled with step 1 subject +
            body.
          </p>
        </div>
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
