import Link from "next/link";
import { ThemeToggle } from "./theme-toggle";

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
            <Link href="/" className="text-muted-foreground hover:text-foreground">
              Dashboard
            </Link>
            <Link href="/samples" className="text-muted-foreground hover:text-foreground">
              Samples
            </Link>
          </nav>
        </div>
        <ThemeToggle />
      </div>
    </header>
  );
}
