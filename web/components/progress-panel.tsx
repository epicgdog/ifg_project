"use client";
import * as React from "react";
import { Check, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RUN_STAGES, type RunStage } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { RunStreamState } from "@/lib/sse";

const FRIENDLY_STEPS: { label: string; stages: RunStage[] }[] = [
  { label: "Ingesting & Cleaning Contacts", stages: ["ingest"] },
  { label: "Enriching Data via API", stages: ["enrich"] },
  { label: "Filtering for Ideal Client Profile", stages: ["classify"] },
  { label: "Drafting Personalized Emails", stages: ["generate"] },
  { label: "Finalizing Campaign Sequence", stages: ["validate", "export"] },
];

function useElapsed(startedAt: number | null) {
  const [now, setNow] = React.useState(() => Date.now());
  React.useEffect(() => {
    if (!startedAt) return;
    const id = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(id);
  }, [startedAt]);
  if (!startedAt) return 0;
  return Math.max(0, Math.floor((now - startedAt) / 1000));
}

export function ProgressPanel({
  stream,
  startedAt,
}: {
  stream: RunStreamState;
  startedAt: number | null;
}) {
  const elapsed = useElapsed(startedAt);
  const percent =
    stream.progress && stream.progress.total > 0
      ? (stream.progress.current / stream.progress.total) * 100
      : 0;

  const currentRawIdx = stream.stage ? RUN_STAGES.indexOf(stream.stage) : -1;

  const getStepStatus = (step: { stages: RunStage[] }): "done" | "active" | "pending" => {
    if (stream.status === "done") return "done";

    const maxRawIdx = Math.max(...step.stages.map((s) => RUN_STAGES.indexOf(s)));

    const isCompleted = step.stages.every((s) => stream.completedStages.includes(s));
    if (isCompleted) return "done";
    if (currentRawIdx > maxRawIdx) return "done";

    const isActive = step.stages.some((s) => stream.stage === s);
    if (isActive) return "active";

    return "pending";
  };

  const activeStep = FRIENDLY_STEPS.find((s) => getStepStatus(s) === "active");
  const activeLabel = activeStep?.label;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Pipeline progress</span>
          <span className="text-sm font-normal text-muted-foreground tabular-nums">
            {startedAt
              ? `${new Date(startedAt).toLocaleTimeString()} · ${elapsed}s elapsed`
              : ""}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Horizontal stepper */}
        <div className="flex items-start w-full overflow-x-auto pb-1">
          {FRIENDLY_STEPS.map((step, i) => {
            const status = getStepStatus(step);
            const isLast = i === FRIENDLY_STEPS.length - 1;
            const prevStatus = i > 0 ? getStepStatus(FRIENDLY_STEPS[i - 1]) : "done";
            const connectorActive = prevStatus === "done";

            return (
              <React.Fragment key={step.label}>
                {i > 0 && (
                  <div
                    className={cn(
                      "h-px flex-1 shrink-0 min-w-[16px]",
                      "transition-colors duration-500",
                      connectorActive ? "bg-emerald-500" : "bg-border"
                    )}
                    style={{ marginTop: "18px" }}
                  />
                )}
                <div
                  className={cn(
                    "flex flex-col items-center gap-2 shrink-0",
                    isLast ? "min-w-[72px]" : "min-w-[72px]"
                  )}
                >
                  {/* Circle */}
                  <div
                    className={cn(
                      "flex h-9 w-9 items-center justify-center rounded-full border-2 text-sm font-semibold transition-all duration-300",
                      status === "done" &&
                        "border-emerald-500 bg-emerald-500 text-white",
                      status === "active" &&
                        "border-primary bg-primary text-primary-foreground shadow-md shadow-primary/25",
                      status === "pending" &&
                        "border-border bg-background text-muted-foreground"
                    )}
                  >
                    {status === "done" ? (
                      <Check className="h-4 w-4" />
                    ) : status === "active" ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      i + 1
                    )}
                  </div>
                  {/* Label */}
                  <span
                    className={cn(
                      "max-w-[72px] text-center text-[10px] leading-snug font-medium transition-colors duration-300",
                      status === "done" && "text-emerald-700 dark:text-emerald-400",
                      status === "active" && "text-foreground",
                      status === "pending" && "text-muted-foreground"
                    )}
                  >
                    {step.label}
                  </span>
                </div>
              </React.Fragment>
            );
          })}
        </div>

        {/* Progress bar (per-contact within current stage) */}
        {stream.progress && stream.progress.total > 0 && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="italic">{activeLabel ?? stream.progress.stage}</span>
              <span className="tabular-nums">
                {stream.progress.current} / {stream.progress.total}
              </span>
            </div>
            <div className="relative h-2 w-full overflow-hidden rounded-full bg-secondary">
              <div
                className="h-full bg-primary"
                style={{
                  width: `${Math.min(100, Math.max(0, percent))}%`,
                  transition: "width 0.5s ease-in-out",
                }}
              />
            </div>
          </div>
        )}

        {stream.activities.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-medium text-foreground">Live activity</div>
            <div className="max-h-44 space-y-1 overflow-auto rounded-md border bg-muted/20 p-2">
              {stream.activities.slice(0, 14).map((a, idx) => (
                <div
                  key={`${idx}-${a.source}-${a.message}`}
                  className="text-xs text-muted-foreground"
                >
                  <span className="font-medium text-foreground/80">[{a.source}]</span>{" "}
                  {a.message}
                  {a.company ? (
                    <span className="text-muted-foreground/80"> ({a.company})</span>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error state */}
        {stream.status === "error" && (
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600 dark:border-red-900 dark:bg-red-950/30 dark:text-red-400">
            {stream.error || "Stream failed. Check backend logs."}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
