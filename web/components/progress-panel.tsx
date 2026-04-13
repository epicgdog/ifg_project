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

const FEED_LINES = [
  "[classifier] Audience confidence 0.90, maturity 75 (Diamond Companies)",
  "[hunter] Verified email identified (Diamond Companies)",
  "[person_agent] Identity cross-reference validated (Diamond Companies)",
  "[website] Scraped company site: https://diamond-co.com (Diamond Companies)",
  "[web] Fetched evidence page: https://issuu.com/naturaldiamondcouncil/docs/only_natural_diamonds_-_fall_winter_2025 (Diamond Companies)",
  "[web] Fetched evidence page: https://thenewjeweller.com/Events_And_News.html (Diamond Companies)",
  "[serper] Query: \"Diamond Companies\" recent award OR recognition 2023 2024 (Diamond Companies)",
  "[serper] Query: \"Diamond Companies\" industry trends OR priorities 2024 CEO (Diamond Companies)",
];

const SOURCE_COLORS: Record<string, string> = {
  classifier: "text-sky-300",
  hunter: "text-emerald-300",
  person_agent: "text-violet-300",
  website: "text-cyan-300",
  web: "text-amber-300",
  serper: "text-orange-300",
};

type FeedItem = {
  id: string;
  source: string;
  message: string;
  entering: boolean;
  fading: boolean;
};

function parseFeedLine(line: string): { source: string; message: string } {
  const match = line.match(/^\[(.+?)\]\s*(.*)$/);
  if (!match) return { source: "system", message: line };
  return { source: match[1] || "system", message: match[2] || "" };
}

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
  const [feedItems, setFeedItems] = React.useState<FeedItem[]>([]);
  const cursorRef = React.useRef<number>(0);
  const timersRef = React.useRef<number[]>([]);

  const schedule = React.useCallback((fn: () => void, ms: number) => {
    const id = window.setTimeout(fn, ms);
    timersRef.current.push(id);
  }, []);

  const pushFeedLine = React.useCallback(
    (line: string) => {
      const { source, message } = parseFeedLine(line);
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

      setFeedItems((prev) => [{ id, source, message, entering: true, fading: false }, ...prev].slice(0, 9));

      schedule(() => {
        setFeedItems((prev) =>
          prev.map((item) =>
            item.id === id ? { ...item, entering: false } : item
          )
        );
      }, 30);

      schedule(() => {
        setFeedItems((prev) =>
          prev.map((item) => (item.id === id ? { ...item, fading: true } : item))
        );
      }, 4200);

      schedule(() => {
        setFeedItems((prev) => prev.filter((item) => item.id !== id));
      }, 5200);
    },
    [schedule]
  );

  React.useEffect(() => {
    const tick = () => {
      const line = FEED_LINES[cursorRef.current % FEED_LINES.length];
      cursorRef.current += 1;
      pushFeedLine(line);
    };

    tick();
    const interval = window.setInterval(tick, 1500);
    return () => {
      window.clearInterval(interval);
      for (const id of timersRef.current) window.clearTimeout(id);
      timersRef.current = [];
    };
  }, [pushFeedLine]);

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
            className="h-64 overflow-hidden rounded-md border border-white/10 bg-black/20 p-2"
            style={{
              fontFamily:
                "'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, monospace",
            }}
          >
            <div className="space-y-1.5">
              {feedItems.map((item) => {
                const sourceColor = SOURCE_COLORS[item.source] || "text-slate-300";
                return (
                  <div
                    key={item.id}
                    className={cn(
                      "rounded-md border border-white/10 bg-white/[0.02] px-3 py-2 text-xs leading-relaxed transition-all duration-700 ease-out",
                      item.entering && "translate-y-2 opacity-0",
                      !item.entering && !item.fading && "translate-y-0 opacity-100",
                      item.fading && "-translate-y-1 opacity-0"
                    )}
                  >
                    <span className={cn("font-semibold", sourceColor)}>[{item.source}]</span>{" "}
                    {renderMessage(item.message)}
                  </div>
                );
              })}
            </div>
            <div className="pointer-events-none absolute" />
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
