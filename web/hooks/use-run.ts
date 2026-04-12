"use client";
import * as React from "react";
import { startRun, uploadFiles } from "@/lib/api";
import type { RunRequest, RunStatus } from "@/lib/types";

export interface UseRunState {
  status: RunStatus;
  runId: string | null;
  error: string | null;
}

export function useRun() {
  const [state, setState] = React.useState<UseRunState>({
    status: "idle",
    runId: null,
    error: null,
  });

  const upload = React.useCallback(async (files: File[]) => {
    setState((s) => ({ ...s, status: "uploading", error: null }));
    try {
      const res = await uploadFiles(files);
      setState((s) => ({ ...s, status: "idle" }));
      return res.file_ids;
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setState({ status: "error", runId: null, error: msg });
      throw e;
    }
  }, []);

  const run = React.useCallback(async (body: RunRequest) => {
    setState((s) => ({ ...s, status: "running", error: null }));
    try {
      const res = await startRun(body);
      setState({ status: "running", runId: res.run_id, error: null });
      return res;
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setState({ status: "error", runId: null, error: msg });
      throw e;
    }
  }, []);

  const setDone = React.useCallback(() => {
    setState((s) => ({ ...s, status: "done" }));
  }, []);

  const setError = React.useCallback((msg: string) => {
    setState((s) => ({ ...s, status: "error", error: msg }));
  }, []);

  const reset = React.useCallback(() => {
    setState({ status: "idle", runId: null, error: null });
  }, []);

  return { ...state, upload, run, setDone, setError, reset };
}
