"use client";
import Link from "next/link";
import { Settings, UserPlus } from "lucide-react";
import { ThemeToggle } from "./theme-toggle";
import { ConfigHealthDialog } from "./config-health";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

export function SiteHeader() {
  return (
    <header className="border-b bg-background/80 backdrop-blur sticky top-0 z-40">
      <div className="mx-auto max-w-7xl flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-baseline gap-2">
            <span className="text-xl font-semibold tracking-tight">ForgeReach</span>
            <span className="text-xs text-muted-foreground hidden sm:inline">
              AI outbound for blue-collar operators
            </span>
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/demo" className="text-muted-foreground hover:text-foreground">
              Demo
            </Link>
            <Link href="/tutorial" className="text-muted-foreground hover:text-foreground">
              Tutorial
            </Link>
            <Link href="/samples" className="text-muted-foreground hover:text-foreground">
              Samples
            </Link>
          </nav>
        </div>
        <div className="flex items-center gap-2">
          <Dialog>
            <DialogTrigger asChild>
              <button
                className="rounded-md p-2 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                aria-label="Connect infrastructure"
              >
                <Settings className="h-4 w-4" />
              </button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Connect infrastructure</DialogTitle>
              </DialogHeader>
              <div className="rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground">
                Keep this simple: connect lead sources and AI infrastructure once, then your
                team can launch campaigns without touching technical settings.
              </div>
              <ConfigHealthDialog />
              <button
                type="button"
                className="mt-1 inline-flex items-center gap-2 rounded-md border px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground"
              >
                <UserPlus className="h-3.5 w-3.5" /> Invite IT/admin to configure
              </button>
            </DialogContent>
          </Dialog>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
