"use client";
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { SiteHeader } from "@/components/site-header";
import { SampleCard } from "@/components/sample-card";
import { Badge } from "@/components/ui/badge";
import { getSamples } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { SampleContact } from "@/lib/types";

type Filter = "all" | "owner" | "referral";

export default function SamplesPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["samples"],
    queryFn: getSamples,
  });
  const [filter, setFilter] = React.useState<Filter>("all");

  const samples: SampleContact[] = data || [];
  const filtered = samples.filter((s) => {
    if (filter === "all") return true;
    const isRef = (s.audience || "").toLowerCase().includes("referral");
    return filter === "referral" ? isRef : !isRef;
  });

  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-7xl space-y-6 px-6 py-10">
        <header>
          <h1 className="text-2xl font-semibold tracking-tight">Sample sequences</h1>
          <p className="text-sm text-muted-foreground">
            Illustrative output across audiences — no live data.
          </p>
        </header>

        <div className="flex flex-wrap gap-2">
          {(
            [
              ["all", "All"],
              ["owner", "Owner"],
              ["referral", "Referral Advocate"],
            ] as [Filter, string][]
          ).map(([val, label]) => (
            <button
              key={val}
              onClick={() => setFilter(val)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                filter === val
                  ? "border-primary bg-primary/10 text-foreground"
                  : "border-border text-muted-foreground hover:text-foreground"
              )}
            >
              {label}
            </button>
          ))}
          <Badge variant="muted" className="ml-auto">
            {filtered.length} samples
          </Badge>
        </div>

        {isLoading ? (
          <div className="text-sm text-muted-foreground">Loading samples…</div>
        ) : isError ? (
          <div className="text-sm text-red-500">
            Failed to load samples: {(error as Error).message}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-sm text-muted-foreground">No samples match this filter.</div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {filtered.map((s, i) => (
              <SampleCard key={`${s.full_name}-${i}`} sample={s} />
            ))}
          </div>
        )}
      </main>
    </>
  );
}
