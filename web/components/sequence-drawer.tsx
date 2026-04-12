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
