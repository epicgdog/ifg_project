"use client";
import * as React from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ModeBadge } from "@/components/mode-badge";
import type { ContactRow } from "@/lib/types";

function parseFacts(raw: string | undefined): Record<string, unknown> {
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw);
    return typeof parsed === "object" && parsed !== null
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
}

function firstNStrings(value: unknown, n: number): string[] {
  if (!Array.isArray(value)) return [];
  const out: string[] = [];
  for (const item of value) {
    if (typeof item === "string" && item.trim()) out.push(item.trim());
    if (out.length >= n) break;
  }
  return out;
}

function extractTopHooks(facts: Record<string, unknown>): string[] {
  const pageLevel =
    typeof facts.page_level_personalization === "object" &&
    facts.page_level_personalization !== null
      ? (facts.page_level_personalization as Record<string, unknown>)
      : {};
  const reasoned =
    typeof facts.reasoned_personalization === "object" &&
    facts.reasoned_personalization !== null
      ? (facts.reasoned_personalization as Record<string, unknown>)
      : {};

  const angles = firstNStrings(pageLevel.personalization_angles, 3);
  if (angles.length > 0) return angles;

  const fallback = firstNStrings(reasoned.talking_points, 3);
  if (fallback.length > 0) return fallback;

  const heuristic = firstNStrings(facts.heuristic_personalization_hooks, 3);
  return heuristic;
}

function evidenceCount(facts: Record<string, unknown>): number {
  const pages = facts.source_evidence_pages;
  return Array.isArray(pages) ? pages.length : 0;
}

function Step({ subject, body }: { subject?: string; body?: string }) {
  return (
    <div className="space-y-3">
      <div>
        <div className="text-xs uppercase text-muted-foreground">Subject</div>
        <div className="mt-1 rounded-md border bg-muted/30 px-3 py-2 text-sm">
          {subject || <span className="text-muted-foreground">—</span>}
        </div>
      </div>
      <div>
        <div className="text-xs uppercase text-muted-foreground">Body</div>
        <div className="mt-1 whitespace-pre-wrap rounded-md border bg-muted/30 px-3 py-2 text-sm leading-relaxed">
          {body || <span className="text-muted-foreground">—</span>}
        </div>
      </div>
    </div>
  );
}

export function SequenceDrawer({
  contact,
  open,
  onOpenChange,
}: {
  contact: ContactRow | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const facts = React.useMemo(
    () => parseFacts((contact?.personalization_facts_json as string) || ""),
    [contact?.personalization_facts_json]
  );
  const hooks = React.useMemo(() => extractTopHooks(facts), [facts]);
  const evidCount = React.useMemo(() => evidenceCount(facts), [facts]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-2xl">
        {contact && (
          <>
            <SheetHeader>
              <SheetTitle className="flex items-center gap-2">
                {contact.full_name}
                <ModeBadge audience={contact.audience} />
              </SheetTitle>
              <SheetDescription>
                {[contact.title, contact.company].filter(Boolean).join(" · ")}
              </SheetDescription>
            </SheetHeader>

            <div className="mt-4 rounded-md border bg-muted/30 p-3">
              <div className="text-xs font-medium text-foreground">Research evidence</div>
              <div className="mt-1 text-xs text-muted-foreground">
                {evidCount} grounded source page{evidCount === 1 ? "" : "s"}
                {contact.decision_maker_name
                  ? ` | decision maker: ${contact.decision_maker_name}`
                  : ""}
                {contact.decision_maker_title
                  ? ` (${contact.decision_maker_title})`
                  : ""}
              </div>
              {hooks.length > 0 ? (
                <ul className="mt-2 space-y-1 text-xs text-foreground">
                  {hooks.map((h, i) => (
                    <li key={`${i}-${h}`}>- {h}</li>
                  ))}
                </ul>
              ) : (
                <div className="mt-2 text-xs text-muted-foreground">
                  No high-signal hooks extracted for this contact.
                </div>
              )}
            </div>

            <div className="mt-6">
              <Tabs defaultValue="1">
                <TabsList>
                  <TabsTrigger value="1">Step 1</TabsTrigger>
                  <TabsTrigger value="2">Step 2</TabsTrigger>
                  <TabsTrigger value="3">Step 3</TabsTrigger>
                </TabsList>
                <TabsContent value="1" className="mt-4">
                  <Step
                    subject={contact.subject_1 as string}
                    body={contact.email_step_1 as string}
                  />
                </TabsContent>
                <TabsContent value="2" className="mt-4">
                  <Step
                    subject={contact.subject_2 as string}
                    body={contact.email_step_2 as string}
                  />
                </TabsContent>
                <TabsContent value="3" className="mt-4">
                  <Step
                    subject={contact.subject_3 as string}
                    body={contact.email_step_3 as string}
                  />
                </TabsContent>
              </Tabs>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
