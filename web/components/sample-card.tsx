"use client";
import * as React from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ModeBadge } from "@/components/mode-badge";
import type { SampleContact } from "@/lib/types";

function StepSection({
  label,
  subject,
  body,
}: {
  label: string;
  subject: string;
  body: string;
}) {
  const [open, setOpen] = React.useState(false);
  return (
    <div className="border-t">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium hover:bg-muted/40"
      >
        <span>{label}</span>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open && (
        <div className="space-y-2 px-4 pb-4 text-sm">
          <div>
            <div className="text-xs uppercase text-muted-foreground">Subject</div>
            <div className="mt-1 rounded-md border bg-muted/30 px-3 py-2">
              {subject || "—"}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase text-muted-foreground">Body</div>
            <div className="mt-1 whitespace-pre-wrap rounded-md border bg-muted/30 px-3 py-2 leading-relaxed">
              {body || "—"}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function SampleCard({ sample }: { sample: SampleContact }) {
  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {sample.full_name}
          <ModeBadge audience={sample.audience} />
        </CardTitle>
        <div className="text-sm text-muted-foreground">
          {[sample.title, sample.company].filter(Boolean).join(" · ")}
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <StepSection label="Step 1" subject={sample.subject_1} body={sample.email_step_1} />
        <StepSection label="Step 2" subject={sample.subject_2} body={sample.email_step_2} />
        <StepSection label="Step 3" subject={sample.subject_3} body={sample.email_step_3} />
      </CardContent>
    </Card>
  );
}
