"use client";
import { AlertCircle, CheckCircle2, Cpu } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useConfigHealth } from "@/hooks/use-config-health";
import { cn } from "@/lib/utils";

const PROVIDERS: Array<{ key: "openrouter" | "apollo" | "hunter" | "apify"; label: string }> = [
  { key: "openrouter", label: "OpenRouter" },
  { key: "apollo", label: "Apollo" },
  { key: "hunter", label: "Hunter" },
  { key: "apify", label: "Apify" },
];

function Dot({ ok }: { ok: boolean }) {
  return (
    <span
      className={cn(
        "inline-block h-2.5 w-2.5 rounded-full",
        ok ? "bg-emerald-500" : "bg-red-500"
      )}
      aria-hidden
    />
  );
}

export function ConfigHealth() {
  const { data, isLoading, isError } = useConfigHealth();

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
      {PROVIDERS.map((p) => {
        const ok = !!data?.[p.key];
        return (
          <Card key={p.key}>
            <CardContent className="flex items-center justify-between p-4">
              <div className="flex items-center gap-2">
                {isError ? (
                  <AlertCircle className="h-4 w-4 text-muted-foreground" />
                ) : ok ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                ) : (
                  <Dot ok={false} />
                )}
                <span className="text-sm font-medium">{p.label}</span>
              </div>
              <Badge variant={ok ? "success" : "muted"}>
                {isLoading
                  ? "..."
                  : isError
                  ? "Offline"
                  : ok
                  ? "Configured"
                  : "Missing"}
              </Badge>
            </CardContent>
          </Card>
        );
      })}
      <Card>
        <CardContent className="flex items-center justify-between p-4">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Model</span>
          </div>
          <Badge variant="outline" className="max-w-[12rem] truncate">
            {data?.model || (isError ? "offline" : "—")}
          </Badge>
        </CardContent>
      </Card>
    </div>
  );
}
