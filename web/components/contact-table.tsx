"use client";
import * as React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { ModeBadge } from "@/components/mode-badge";
import type { ContactRow } from "@/lib/types";

function audienceKey(r: ContactRow): "owner" | "referral" {
  return (r.audience || "").toLowerCase().includes("referral") ? "referral" : "owner";
}

export function ContactTable({
  rows,
  onSelect,
}: {
  rows: ContactRow[];
  onSelect: (row: ContactRow) => void;
}) {
  const [audienceFilter, setAudienceFilter] = React.useState<Set<"owner" | "referral">>(
    new Set(["owner", "referral"])
  );
  const [onlyQualified, setOnlyQualified] = React.useState(false);

  const filtered = React.useMemo(
    () =>
      rows.filter((r) => {
        if (!audienceFilter.has(audienceKey(r))) return false;
        if (onlyQualified) {
          const tier = (r.qualification_tier || "").toLowerCase();
          if (tier !== "high" && tier !== "qualified") return false;
        }
        return true;
      }),
    [rows, audienceFilter, onlyQualified]
  );

  const toggle = (k: "owner" | "referral") => {
    const next = new Set(audienceFilter);
    if (next.has(k)) next.delete(k);
    else next.add(k);
    setAudienceFilter(next);
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">Audience:</span>
          {(["owner", "referral"] as const).map((k) => (
            <label key={k} className="flex items-center gap-1.5 text-sm cursor-pointer">
              <Checkbox
                checked={audienceFilter.has(k)}
                onCheckedChange={() => toggle(k)}
              />
              <span className="capitalize">{k === "referral" ? "Referral Advocate" : "Owner"}</span>
            </label>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="only-qualified"
            checked={onlyQualified}
            onCheckedChange={setOnlyQualified}
          />
          <Label htmlFor="only-qualified" className="cursor-pointer">
            Only qualified
          </Label>
        </div>
        <div className="ml-auto text-xs text-muted-foreground">
          {filtered.length} of {rows.length}
        </div>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Audience</TableHead>
              <TableHead>Fit score</TableHead>
              <TableHead>Tier</TableHead>
              <TableHead>Review</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  No contacts match current filters
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((r, i) => (
                <TableRow
                  key={`${r.full_name}-${i}`}
                  className="cursor-pointer"
                  onClick={() => onSelect(r)}
                >
                  <TableCell className="font-medium">{r.full_name}</TableCell>
                  <TableCell>{r.company}</TableCell>
                  <TableCell>
                    <ModeBadge audience={r.audience} />
                  </TableCell>
                  <TableCell className="tabular-nums">{String(r.fit_score ?? "—")}</TableCell>
                  <TableCell className="capitalize">{r.qualification_tier || "—"}</TableCell>
                  <TableCell>
                    {r.review_flag && r.review_flag !== "false" && r.review_flag !== "" ? (
                      <Badge variant="destructive">{r.review_flag}</Badge>
                    ) : (
                      <Badge variant="muted">clear</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
