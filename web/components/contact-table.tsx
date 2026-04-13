"use client";
import * as React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Pencil, Search, UserRound, Handshake } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ContactRow } from "@/lib/types";

function audienceKey(r: ContactRow): "owner" | "referral" {
  return (r.audience || "").toLowerCase().includes("referral") ? "referral" : "owner";
}

function AudiencePill({ audience }: { audience: string }) {
  const isReferral = audienceKey({ audience } as ContactRow) === "referral";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        isReferral
          ? "bg-violet-100 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300"
          : "bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300"
      )}
    >
      {isReferral ? (
        <Handshake className="h-3.5 w-3.5" />
      ) : (
        <UserRound className="h-3.5 w-3.5" />
      )}
      {isReferral ? "Referral Advocate" : "Owner"}
    </span>
  );
}

function fitBand(score: number): "high" | "medium" | "low" {
  if (score >= 75) return "high";
  if (score >= 55) return "medium";
  return "low";
}

function FitIndicator({ score }: { score: number | string }) {
  const n = typeof score === "number" ? score : Number(score);
  if (!Number.isFinite(n)) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }
  const band = fitBand(n);
  const styles = {
    high: "bg-emerald-100 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-300 dark:ring-emerald-500/30",
    medium:
      "bg-amber-100 text-amber-800 ring-amber-200 dark:bg-amber-500/15 dark:text-amber-300 dark:ring-amber-500/30",
    low: "bg-muted text-muted-foreground ring-border",
  } as const;
  const labels = { high: "High fit", medium: "Medium fit", low: "Low fit" } as const;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1",
        styles[band]
      )}
      title={`Fit score: ${n}`}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          band === "high"
            ? "bg-emerald-500"
            : band === "medium"
            ? "bg-amber-500"
            : "bg-muted-foreground/50"
        )}
      />
      {labels[band]}
    </span>
  );
}

function StatusPill({ row }: { row: ContactRow }) {
  const flagged = !!row.review_flag && !["false", "", "no", "0"].includes(
    String(row.review_flag).toLowerCase()
  );
  if (flagged) {
    return (
      <Badge variant="destructive" className="font-medium">
        Needs review
      </Badge>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
      Ready to send
    </span>
  );
}

function firstTwoSentences(text: string | undefined, maxChars = 220): string {
  if (!text) return "";
  const clean = text.replace(/\s+/g, " ").trim();
  const parts = clean.split(/(?<=[.!?])\s+/).slice(0, 2).join(" ");
  return parts.length > maxChars ? parts.slice(0, maxChars - 1) + "…" : parts;
}

function parseEvidenceCount(raw: string | undefined): number {
  if (!raw) return 0;
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const pages = parsed.source_evidence_pages;
    return Array.isArray(pages) ? pages.length : 0;
  } catch {
    return 0;
  }
}

export function ContactTable({
  rows,
  onSelect,
}: {
  rows: ContactRow[];
  onSelect: (row: ContactRow) => void;
}) {
  const [audienceFilter, setAudienceFilter] = React.useState<Set<"owner" | "referral">>(
    new Set(["owner", "referral"])
  );
  const [onlyQualified, setOnlyQualified] = React.useState(false);
  const [query, setQuery] = React.useState("");

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((r) => {
      if (!audienceFilter.has(audienceKey(r))) return false;
      if (onlyQualified) {
        const tier = (r.qualification_tier || "").toLowerCase();
        if (tier !== "high" && tier !== "qualified") return false;
      }
      if (q) {
        const hay = `${r.full_name || ""} ${r.company || ""} ${r.title || ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [rows, audienceFilter, onlyQualified, query]);

  const toggle = (k: "owner" | "referral") => {
    const next = new Set(audienceFilter);
    if (next.has(k)) next.delete(k);
    else next.add(k);
    setAudienceFilter(next);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative w-full max-w-xs">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search name, company, title…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-8"
          />
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">Audience:</span>
          {(["owner", "referral"] as const).map((k) => (
            <label key={k} className="flex cursor-pointer items-center gap-1.5 text-sm">
              <Checkbox
                checked={audienceFilter.has(k)}
                onCheckedChange={() => toggle(k)}
              />
              <span>{k === "referral" ? "Referral Advocate" : "Owner"}</span>
            </label>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="only-qualified"
            checked={onlyQualified}
            onCheckedChange={setOnlyQualified}
          />
          <Label htmlFor="only-qualified" className="cursor-pointer">
            Only qualified
          </Label>
        </div>
        <div className="ml-auto text-xs text-muted-foreground">
          Showing <span className="font-medium text-foreground">{filtered.length}</span>{" "}
          of {rows.length}
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40 hover:bg-muted/40">
              <TableHead className="w-[22%]">Target</TableHead>
              <TableHead className="w-[14%]">Audience</TableHead>
              <TableHead className="w-[12%]">Fit</TableHead>
              <TableHead className="w-[40%]">AI outreach preview</TableHead>
              <TableHead className="w-[8%]">Evidence</TableHead>
              <TableHead className="w-[10%]">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                  No contacts match current filters
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((r, i) => {
                const preview = firstTwoSentences(
                  r.email_step_1 || r.subject_1 ? String(r.email_step_1 || "") : ""
                );
                const evidence = parseEvidenceCount(r.personalization_facts_json as string);
                return (
                  <TableRow
                    key={`${r.full_name}-${i}`}
                    className="group cursor-pointer align-top transition-colors hover:bg-muted/30"
                    onClick={() => onSelect(r)}
                  >
                    <TableCell className="py-4">
                      <div className="flex flex-col">
                        <span className="font-medium leading-tight">
                          {r.full_name || "—"}
                        </span>
                        <span className="mt-0.5 text-xs text-muted-foreground">
                          {r.company || "—"}
                        </span>
                        {r.title ? (
                          <span className="mt-0.5 text-[11px] text-muted-foreground/80">
                            {r.title}
                          </span>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell className="py-4">
                      <AudiencePill audience={r.audience} />
                    </TableCell>
                    <TableCell className="py-4">
                      <FitIndicator score={r.fit_score} />
                    </TableCell>
                    <TableCell className="py-4">
                      <div className="flex items-start gap-2">
                        <div className="min-w-0 flex-1">
                          {r.subject_1 ? (
                            <div className="truncate text-xs font-medium text-foreground/90">
                              {r.subject_1}
                            </div>
                          ) : null}
                          <p className="mt-0.5 line-clamp-2 text-sm leading-relaxed text-muted-foreground">
                            {preview || (
                              <span className="italic">No preview available</span>
                            )}
                          </p>
                        </div>
                        <button
                          type="button"
                          aria-label="View or edit full sequence"
                          className="mt-0.5 rounded-md border p-1.5 text-muted-foreground opacity-0 transition-all hover:bg-accent hover:text-foreground group-hover:opacity-100"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelect(r);
                          }}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </TableCell>
                    <TableCell className="py-4">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium",
                          evidence > 0
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300"
                            : "bg-muted text-muted-foreground"
                        )}
                        title="Number of grounded source pages used for personalization"
                      >
                        {evidence > 0 ? `${evidence} src` : "none"}
                      </span>
                    </TableCell>
                    <TableCell className="py-4">
                      <StatusPill row={r} />
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
