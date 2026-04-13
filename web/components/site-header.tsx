"use client";
import Link from "next/link";
import { Settings } from "lucide-react";
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
                aria-label="API settings"
              >
                <Settings className="h-4 w-4" />
              </button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>API Configuration</DialogTitle>
              </DialogHeader>
              <ConfigHealthDialog />
            </DialogContent>
          </Dialog>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
