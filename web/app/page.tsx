"use client";
import * as React from "react";
import { Play, Loader2 } from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import { ConfigHealth } from "@/components/config-health";
import {
  RunForm,
  DEFAULT_RUN_FORM,
  toRunRequest,
  type RunFormValues,
} from "@/components/run-form";
import { ProgressPanel } from "@/components/progress-panel";
import { ResultsPanel } from "@/components/results-panel";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useRun } from "@/hooks/use-run";
import { useRunStream } from "@/lib/sse";

export default function HomePage() {
  const [form, setForm] = React.useState<RunFormValues>(DEFAULT_RUN_FORM);
  const run = useRun();
  const [startedAt, setStartedAt] = React.useState<number | null>(null);
  const stream = useRunStream(run.runId);

  const busy = run.status === "uploading" || run.status === "running";
  const showProgress = busy || stream.status === "running" || stream.status === "error";
  const showResults = stream.status === "done" && stream.report;

  const canRun =
    !busy &&
    ((form.useSample || form.files.length > 0 || form.mode === "api_discovery") &&
      (form.mode !== "api_discovery" || form.prospect_sources.length > 0));

  const onRun = async () => {
    try {
      let fileIds: string[] = [];
      if (!form.useSample && form.files.length > 0 && form.mode !== "api_discovery") {
        fileIds = await run.upload(form.files);
      }
      setStartedAt(Date.now());
      await run.run(toRunRequest(form, fileIds));
    } catch {
      /* surfaced in run.error */
    }
  };

  // When SSE terminates in "done" state, flip our run state machine.
  React.useEffect(() => {
    if (stream.status === "done" && run.status === "running") {
      run.setDone();
    }
    if (stream.status === "error" && run.status === "running") {
      run.setError(stream.error || "Stream error");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stream.status]);

  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-7xl space-y-10 px-6 py-10">
        <section>
          <h1 className="mb-2 text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="mb-4 text-sm text-muted-foreground">
            Upload contacts, configure your ICP, and generate reviewable outbound sequences.
          </p>
          <ConfigHealth />
        </section>

        <Separator />

        <section>
          <h2 className="mb-4 text-lg font-semibold">Run configuration</h2>
          <RunForm value={form} onChange={setForm} disabled={busy} />
        </section>

        <section className="flex flex-col items-start gap-2">
          <Button size="lg" onClick={onRun} disabled={!canRun}>
            {busy ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Running…
              </>
            ) : (
              <>
                <Play className="h-4 w-4" /> Run pipeline
              </>
            )}
          </Button>
          <p className="text-xs text-muted-foreground">
            Run will take ~30–90s depending on contact count.
          </p>
          {run.error && (
            <p className="text-sm text-red-500">Run failed: {run.error}</p>
          )}
        </section>

        {showProgress && (
          <section>
            <ProgressPanel stream={stream} startedAt={startedAt} />
          </section>
        )}

        {showResults && stream.report && (
          <section>
            <h2 className="mb-4 text-lg font-semibold">Results</h2>
            <ResultsPanel done={stream.report} />
          </section>
        )}
      </main>
    </>
  );
}
