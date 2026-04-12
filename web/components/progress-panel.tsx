"use client";
import * as React from "react";
import { Check, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { RUN_STAGES, type RunStage } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { RunStreamState } from "@/lib/sse";

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

  const stageIndex = stream.stage ? RUN_STAGES.indexOf(stream.stage) : -1;

  const stageStatus = (s: RunStage, idx: number) => {
    if (stream.completedStages.includes(s)) return "done";
    if (stageIndex >= 0 && idx < stageIndex) return "done";
    if (stream.stage === s) return "active";
    return "pending";
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Live progress</span>
          <span className="text-sm font-normal text-muted-foreground">
            {startedAt
              ? `${new Date(startedAt).toLocaleTimeString()} • ${elapsed}s elapsed`
              : ""}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex flex-wrap gap-2">
          {RUN_STAGES.map((s, i) => {
            const status = stageStatus(s, i);
            return (
              <div
                key={s}
                className={cn(
                  "flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium capitalize transition-colors",
                  status === "done" && "border-emerald-600/40 bg-emerald-600/10 text-emerald-700 dark:text-emerald-400",
                  status === "active" && "border-primary bg-primary/10 text-foreground",
                  status === "pending" && "border-muted text-muted-foreground"
                )}
              >
                {status === "done" ? (
                  <Check className="h-3 w-3" />
                ) : status === "active" ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-muted-foreground/40" />
                )}
                {s}
              </div>
            );
          })}
        </div>

        {stream.progress && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground capitalize">
                {stream.progress.stage}
              </span>
              <span className="tabular-nums">
                {stream.progress.current} / {stream.progress.total}
              </span>
            </div>
            <Progress value={percent} />
          </div>
        )}

        {stream.status === "error" && (
          <div className="text-sm text-red-500">
            Error: {stream.error || "Stream failed"}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
