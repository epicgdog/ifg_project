"use client";
import * as React from "react";
import { Check } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { RunStreamState } from "@/lib/sse";

const STEP_LABELS = [
  "Ingesting & Cleaning Contacts",
  "Enriching Data via API",
  "Filtering for Ideal Client Profile",
  "Drafting Personalized Emails",
  "Finalizing Campaign Sequence",
];

const SOURCE_COLORS: Record<string, string> = {
  classifier: "text-sky-300",
  hunter: "text-emerald-300",
  person_agent: "text-violet-300",
  website: "text-cyan-300",
  web: "text-amber-300",
  serper: "text-orange-300",
  enrich: "text-teal-300",
  generate: "text-fuchsia-300",
  validate: "text-lime-300",
};

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

function renderMessage(message: string) {
  const tokenRegex = /(https?:\/\/[^\s)]+|\([^)]*\))/g;
  const nodes: React.ReactNode[] = [];
  let last = 0;
  let key = 0;

  for (const match of message.matchAll(tokenRegex)) {
    const idx = match.index ?? 0;
    if (idx > last) {
      nodes.push(
        <span key={`txt-${key++}`} className="text-slate-300">
          {message.slice(last, idx)}
        </span>
      );
    }

    const token = match[0] || "";
    if (token.startsWith("http")) {
      nodes.push(
        <span
          key={`url-${key++}`}
          className="text-white underline decoration-white/30 underline-offset-2"
        >
          {token}
        </span>
      );
    } else {
      nodes.push(
        <span key={`ent-${key++}`} className="text-slate-100">
          {token}
        </span>
      );
    }
    last = idx + token.length;
  }

  if (last < message.length) {
    nodes.push(
      <span key={`tail-${key++}`} className="text-slate-300">
        {message.slice(last)}
      </span>
    );
  }

  return nodes;
}

export function ProgressPanel({
  stream,
  startedAt,
}: {
  stream: RunStreamState;
  startedAt: number | null;
}) {
  const mountStartedAtRef = React.useRef<number>(Date.now());
  const effectiveStartedAt = startedAt ?? mountStartedAtRef.current;
  const elapsed = useElapsed(effectiveStartedAt);
  const liveBoxRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    const el = liveBoxRef.current;
    if (!el) return;
    el.scrollTop = 0;
  }, [stream.activities.length]);

  return (
    <Card className="border-white/10 bg-[#0B0D12] text-slate-100 shadow-2xl shadow-black/35">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="text-base font-semibold text-slate-100">Pipeline progress</span>
          <span className="text-sm font-normal text-slate-400 tabular-nums">
            {`${new Date(effectiveStartedAt).toLocaleTimeString()} - ${elapsed}s elapsed`}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-start w-full overflow-x-auto pb-1">
          {STEP_LABELS.map((label, idx) => (
            <React.Fragment key={label}>
              {idx > 0 && (
                <div
                  className={cn(
                    "mt-4 h-px flex-1 min-w-[14px]",
                    idx === 1 ? "bg-emerald-500/90" : "bg-white/10"
                  )}
                />
              )}
              <div className="w-[140px] shrink-0 text-center">
                <div
                  className={cn(
                    "mx-auto flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold",
                    idx === 0
                      ? "border-emerald-500 bg-emerald-500 text-emerald-950"
                      : "border-slate-600 text-slate-400"
                  )}
                >
                  {idx === 0 ? <Check className="h-4 w-4" /> : idx + 1}
                </div>
                <p className="mt-2 px-1 text-[10px] leading-snug text-slate-400">{label}</p>
              </div>
            </React.Fragment>
          ))}
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="italic">research</span>
            <span className="tabular-nums">1/3</span>
          </div>
          <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-emerald-500 shadow-[0_0_14px_rgba(16,185,129,0.85)]"
              style={{ width: "33.333%" }}
            />
          </div>
        </div>

        <div className="space-y-2">
          <div className="text-sm font-semibold text-white">Live activity</div>
          <div
            ref={liveBoxRef}
            className="h-64 overflow-y-scroll rounded-md border border-white/10 bg-black/20 p-2"
            style={{
              fontFamily:
                "'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, monospace",
            }}
          >
            <div className="space-y-1.5">
              {stream.activities.length === 0 ? (
                <div className="rounded-md border border-dashed border-white/10 bg-white/[0.01] px-3 py-2 text-xs text-slate-500">
                  Waiting for live pipeline activity...
                </div>
              ) : (
                stream.activities.map((a, idx) => {
                  const sourceColor = SOURCE_COLORS[a.source] || "text-slate-300";
                  return (
                    <div
                      key={`${idx}-${a.source}-${a.message}`}
                      className="rounded-md border border-white/10 bg-white/[0.02] px-3 py-2 text-xs leading-relaxed"
                    >
                      <span className={cn("font-semibold", sourceColor)}>[{a.source}]</span>{" "}
                      {renderMessage(a.message)}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {stream.status === "error" && (
          <div className="rounded-md border border-red-500/30 bg-red-950/40 px-3 py-2 text-sm text-red-300">
            {stream.error || "Stream failed. Check backend logs."}
          </div>
        )}

        {stream.status === "done" && (
          <div className="rounded-md border border-emerald-500/30 bg-emerald-950/30 px-3 py-2 text-sm text-emerald-300">
            Pipeline completed successfully.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
