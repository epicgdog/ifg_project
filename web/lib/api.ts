import type {
  ConfigHealth,
  ContactRow,
  RunReport,
  RunRequest,
  RunResponse,
  SampleContact,
  UploadResponse,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body || res.statusText}`);
  }
  return (await res.json()) as T;
}

export async function getConfigHealth(signal?: AbortSignal): Promise<ConfigHealth> {
  const res = await fetch(`${API_URL}/api/config/health`, { signal, cache: "no-store" });
  return handle<ConfigHealth>(res);
}

export async function uploadFiles(files: File[]): Promise<UploadResponse> {
  const fd = new FormData();
  files.forEach((f) => fd.append("files", f));
  const res = await fetch(`${API_URL}/api/uploads`, {
    method: "POST",
    body: fd,
  });
  return handle<UploadResponse>(res);
}

export async function startRun(body: RunRequest): Promise<RunResponse> {
  const res = await fetch(`${API_URL}/api/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handle<RunResponse>(res);
}

export function csvDownloadUrl(runId: string): string {
  return `${API_URL}/api/runs/${runId}/csv`;
}

export function instantlyDownloadUrl(runId: string): string {
  return `${API_URL}/api/runs/${runId}/instantly`;
}

export async function getReport(runId: string): Promise<RunReport> {
  const res = await fetch(`${API_URL}/api/runs/${runId}/report`, { cache: "no-store" });
  return handle<RunReport>(res);
}

export async function getCampaignCsv(runId: string): Promise<string> {
  const res = await fetch(csvDownloadUrl(runId), { cache: "no-store" });
  if (!res.ok) throw new Error(`CSV fetch failed: ${res.status}`);
  return res.text();
}

export async function getSamples(): Promise<SampleContact[]> {
  const res = await fetch(`${API_URL}/api/samples`, { cache: "no-store" });
  const body = await handle<{ samples: SampleContact[]; message?: string }>(res);
  return body.samples || [];
}

export function streamUrl(runId: string): string {
  return `${API_URL}/api/runs/${runId}/stream`;
}

export type { ContactRow };
