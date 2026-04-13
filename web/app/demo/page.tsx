"use client";
import * as React from "react";
import { Play, Loader2, ArrowDown } from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import {
  RunForm,
  DEFAULT_RUN_FORM,
  toRunRequest,
  type RunFormValues,
} from "@/components/run-form";
import { ProgressPanel } from "@/components/progress-panel";
import { ResultsPanel } from "@/components/results-panel";
import { Button } from "@/components/ui/button";
import { useRun } from "@/hooks/use-run";
import { useRunStream } from "@/lib/sse";
import { cn } from "@/lib/utils";

export default function DemoPage() {
  const [form, setForm] = React.useState<RunFormValues>(DEFAULT_RUN_FORM);
  const run = useRun();
  const [startedAt, setStartedAt] = React.useState<number | null>(null);
  const stream = useRunStream(run.runId);

  const resultsRef = React.useRef<HTMLDivElement>(null);

  const busy = run.status === "uploading" || run.status === "running";
  const isDone = stream.status === "done" && !!stream.report;
  const showProgress = busy || stream.status === "running" || stream.status === "error";
  const showResults = isDone;

  const canRun =
    (() => {
      const hunterSelected = form.prospect_sources.includes("hunter");
      const hunterDomainsProvided =
        form.hunter_domains
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean).length > 0;
      const hunterNeedsDomains =
        form.mode === "api_discovery" && hunterSelected && !hunterDomainsProvided;

      return (
        !busy &&
        (form.useSample || form.files.length > 0 || form.mode === "api_discovery") &&
        (form.mode !== "api_discovery" || form.prospect_sources.length > 0) &&
        !hunterNeedsDomains
      );
    })();

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
      <main className="mx-auto max-w-7xl px-6 py-10 space-y-8">
        <section
          className={cn(
            "transition-all duration-300",
            busy && "opacity-40 pointer-events-none select-none"
          )}
        >
          <div className="mb-4">
            <h1 className="text-2xl font-semibold tracking-tight">Campaign Builder</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Upload contacts, define your ICP, and generate reviewable outbound sequences.
            </p>
          </div>
          <RunForm value={form} onChange={setForm} disabled={busy} />
        </section>

        <section className="flex flex-col items-start gap-2">
          {isDone ? (
            <Button
              size="lg"
              className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-md shadow-emerald-600/20"
              onClick={() =>
                resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
              }
            >
              <ArrowDown className="h-4 w-4" />
              Review Generated Sequences
            </Button>
          ) : (
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
          )}
          {!busy && !isDone && (
            <p className="text-xs text-muted-foreground">
              Expect 30–90 s depending on contact count.
            </p>
          )}
          {run.error && (
            <p className="text-sm text-red-500">Run failed: {run.error}</p>
          )}
        </section>

        {showProgress && (
          <section
            className={cn(
              "rounded-lg border bg-card p-4 transition-all duration-300",
              busy && "ring-2 ring-primary/30"
            )}
          >
            <ProgressPanel stream={stream} startedAt={startedAt} />
          </section>
        )}

        {showResults && stream.report && (
          <section ref={resultsRef} className="scroll-mt-6">
            <h2 className="mb-4 text-lg font-semibold">Results</h2>
            <ResultsPanel done={stream.report} />
          </section>
        )}
      </main>
    </>
  );
}
