"use client";
import * as React from "react";
import { streamUrl } from "./api";
import type { DoneEvent, ProgressEvent, RunStage, RunStatus } from "./types";

export interface RunStreamState {
  stage: RunStage | null;
  progress: ProgressEvent | null;
  status: RunStatus;
  report: DoneEvent | null;
  error: string | null;
  completedStages: RunStage[];
}

const initial: RunStreamState = {
  stage: null,
  progress: null,
  status: "idle",
  report: null,
  error: null,
  completedStages: [],
};

export function useRunStream(runId: string | null): RunStreamState {
  const [state, setState] = React.useState<RunStreamState>(initial);

  React.useEffect(() => {
    if (!runId) {
      setState(initial);
      return;
    }
    setState({ ...initial, status: "running" });

    let es: EventSource | null = null;
    try {
      es = new EventSource(streamUrl(runId));
    } catch (err) {
      setState((s) => ({ ...s, status: "error", error: String(err) }));
      return;
    }

    const onStage = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as { stage: RunStage };
        setState((s) => ({
          ...s,
          stage: data.stage,
          completedStages: s.stage && s.stage !== data.stage && !s.completedStages.includes(s.stage)
            ? [...s.completedStages, s.stage]
            : s.completedStages,
        }));
      } catch {
        /* noop */
      }
    };

    const onProgress = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as ProgressEvent;
        setState((s) => ({ ...s, progress: data }));
      } catch {
        /* noop */
      }
    };

    const onDone = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as DoneEvent;
        setState((s) => ({
          ...s,
          status: "done",
          report: data,
          completedStages: s.stage && !s.completedStages.includes(s.stage)
            ? [...s.completedStages, s.stage]
            : s.completedStages,
        }));
      } catch {
        /* noop */
      }
      es?.close();
    };

    const onError = (e: Event) => {
      const data = (e as MessageEvent).data;
      const msg = typeof data === "string" ? data : "Stream error";
      setState((s) => ({ ...s, status: "error", error: msg }));
      es?.close();
    };

    es.addEventListener("stage", onStage as EventListener);
    es.addEventListener("progress", onProgress as EventListener);
    es.addEventListener("done", onDone as EventListener);
    es.addEventListener("error", onError as EventListener);

    return () => {
      es?.close();
    };
  }, [runId]);

  return state;
}
