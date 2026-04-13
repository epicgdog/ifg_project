"use client";
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, ChevronDown, ChevronUp } from "lucide-react";
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
import { MetricCard } from "@/components/metric-card";
import { ContactTable } from "@/components/contact-table";
import { SequenceDrawer } from "@/components/sequence-drawer";
import { csvDownloadUrl, getCampaignCsv, instantlyDownloadUrl } from "@/lib/api";
import { parseContactsCsv } from "@/lib/csv";
import type { ContactRow, DoneEvent } from "@/lib/types";

function pickMetric(report: DoneEvent["report"], keys: string[]): string | number {
  for (const k of keys) {
    const v = report?.[k];
    if (typeof v === "number" || typeof v === "string") return v;
  }
  return "—";
}

export function ResultsPanel({ done }: { done: DoneEvent }) {
  const [selected, setSelected] = React.useState<ContactRow | null>(null);
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [reportOpen, setReportOpen] = React.useState(false);

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
  const metrics = [
    { label: "Total", value: pickMetric(r, ["total", "total_contacts"]) },
    {
      label: "Skipped (Low fit)",
      value: pickMetric(r, ["skipped_low_fit_count"]),
    },
    {
      label: "Skipped (No Identity)",
      value: pickMetric(r, ["skipped_no_identity_count"]),
    },
    {
      label: "Skipped (Unverified Email)",
      value: pickMetric(r, ["skipped_unverified_email_count"]),
    },
    { label: "Enriched", value: pickMetric(r, ["enriched", "enriched_count"]) },
    { label: "Qualified", value: pickMetric(r, ["qualified", "qualified_count"]) },
    {
      label: "High priority",
      value: pickMetric(r, ["high_priority", "high_priority_count"]),
    },
    {
      label: "Review flagged",
      value: pickMetric(r, ["review_flagged", "review_flagged_count", "review_flag_count"]),
    },
    {
      label: "Avg fit score",
      value: pickMetric(r, ["avg_fit_score", "average_fit_score"]),
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="mb-3 text-lg font-semibold">Executive summary</h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-8">
          {metrics.map((m) => (
            <MetricCard key={m.label} label={m.label} value={m.value} />
          ))}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Audience split</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={audienceData}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="hsl(var(--primary))" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Discovery diagnostics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
            <MetricCard
              label="Discovered"
              value={pickMetric(r, ["discovered_count"])}
            />
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
              label="Fallback attempts"
              value={pickMetric(r, ["apollo_fallback_attempts"])}
            />
            <MetricCard
              label="Fallback successes"
              value={pickMetric(r, ["apollo_fallback_successes"])}
            />
          </div>
          {Array.isArray(r.discovery_errors) && r.discovery_errors.length > 0 && (
            <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">
              <div className="mb-1 font-medium">Discovery errors</div>
              {r.discovery_errors.map((err, idx) => (
                <div key={`${idx}-${err}`} className="leading-relaxed">
                  - {err}
                </div>
              ))}
            </div>
          )}
          {Number(r.apollo_search_failures || 0) > 0 &&
            Number(r.apollo_search_attempts || 0) > 0 && (
              <div className="mt-3 rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground">
                Apollo discovery is failing in this run. Switch source to Hunter and provide
                domains to keep discovery running.
              </div>
            )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Research diagnostics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
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
              label="Emails found"
              value={pickMetric(r, ["research_emails_found"])}
            />
            <MetricCard
              label="DMs identified"
              value={pickMetric(r, ["research_decision_makers_found"])}
            />
            <MetricCard
              label="Company summaries"
              value={pickMetric(r, ["research_company_summaries_extracted"])}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Audience &amp; Maturity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <MetricCard
              label="Avg Audience Confidence"
              value={pickMetric(r, ["avg_audience_confidence"])}
            />
            <MetricCard
              label="Avg Maturity Score"
              value={pickMetric(r, ["avg_company_maturity_score"])}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Contacts</CardTitle>
        </CardHeader>
        <CardContent>
          {csvQuery.isLoading ? (
            <div className="text-sm text-muted-foreground">Loading contacts…</div>
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

      <SequenceDrawer
        contact={selected}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
      />

      <div className="flex flex-wrap gap-3">
        <a href={csvDownloadUrl(done.run_id)} download>
          <Button variant="default">
            <Download className="h-4 w-4" /> campaign_ready.csv
          </Button>
        </a>
        <a href={instantlyDownloadUrl(done.run_id)} download>
          <Button variant="outline">
            <Download className="h-4 w-4" /> instantly_campaign.csv
          </Button>
        </a>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            <button
              type="button"
              onClick={() => setReportOpen((v) => !v)}
              className="flex items-center gap-2"
            >
              Run report
              {reportOpen ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
          </CardTitle>
        </CardHeader>
        {reportOpen && (
          <CardContent>
            <pre className="overflow-auto rounded-md border bg-muted/30 p-4 text-xs leading-relaxed">
              {JSON.stringify(done.report, null, 2)}
            </pre>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
