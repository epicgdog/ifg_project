"use client";
import { AlertCircle, CheckCircle2, Cpu, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useConfigHealth } from "@/hooks/use-config-health";
import { cn } from "@/lib/utils";

const PROVIDERS: Array<{ key: "openrouter" | "apollo" | "hunter" | "apify"; label: string; required?: boolean }> = [
  { key: "openrouter", label: "OpenRouter (LLM)", required: true },
  { key: "apollo", label: "Apollo (contact search)" },
  { key: "hunter", label: "Hunter (email lookup)" },
  { key: "apify", label: "Apify (LinkedIn enrichment)" },
];

function StatusIcon({ ok, error }: { ok: boolean; error?: boolean }) {
  if (error) return <AlertCircle className="h-4 w-4 text-muted-foreground" />;
  if (ok) return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
  return <XCircle className="h-4 w-4 text-red-400" />;
}

/** Compact list for use inside a Dialog */
export function ConfigHealthDialog() {
  const { data, isLoading, isError } = useConfigHealth();

  return (
    <div className="space-y-3">
      {PROVIDERS.map((p) => {
        const ok = !!data?.[p.key];
        return (
          <div key={p.key} className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <StatusIcon ok={ok} error={isError} />
              <div>
                <p className="text-sm font-medium leading-none">{p.label}</p>
                {p.required && (
                  <p className="text-xs text-muted-foreground mt-0.5">Required</p>
                )}
              </div>
            </div>
            <Badge variant={ok ? "success" : "muted"} className="ml-4 shrink-0">
              {isLoading ? "…" : isError ? "Offline" : ok ? "Configured" : "Missing"}
            </Badge>
          </div>
        );
      })}

      <div className="flex items-center justify-between border-t pt-3 mt-3">
        <div className="flex items-center gap-2.5">
          <Cpu className={cn("h-4 w-4", isError ? "text-muted-foreground" : "text-sky-500")} />
          <p className="text-sm font-medium">Active model</p>
        </div>
        <span className="text-sm text-muted-foreground truncate max-w-[14rem] text-right">
          {data?.model || (isError ? "offline" : "—")}
        </span>
      </div>
    </div>
  );
}
