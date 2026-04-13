import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  FileText,
  Layers,
  ShieldCheck,
  Sparkles,
  Users,
  Zap,
} from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import { FaqItem } from "@/components/faq-item";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

/* ─── Data ──────────────────────────────────────────────────────────────── */

const PAIN_POINTS = [
  {
    label: "200 contacts. 200 different emails. One of you.",
    body: "Personalizing at scale is impossible to do manually. So you copy-paste the same template, swap the name, and call it personalization. Buyers see through it — open rates tank, replies go quiet.",
  },
  {
    label: "Your best outreach lives in one person's head.",
    body: "The sequences that actually convert are buried in a single rep's drafts. There's no playbook. No way to clone what works. Every new hire starts from scratch.",
  },
  {
    label: "Cold lists go cold fast.",
    body: "By the time you've manually enriched, scored, and written to each contact, half of them have moved on. The speed of your pipeline determines the quality of your pipeline.",
  },
];

const HOW_IT_WORKS = [
  {
    step: "01",
    title: "Upload your list",
    body: "Drop a CSV from Apollo, LinkedIn, or Hunter. ForgeReach reads whatever header format your export has — no cleaning required.",
  },
  {
    step: "02",
    title: "Set your ICP",
    body: "Choose your target state, EBITDA floor, and audience type. Or skip straight to the built-in sample file and run in seconds.",
  },
  {
    step: "03",
    title: "Download your campaign",
    body: "An Instantly-ready CSV lands in your results panel with subjects, 3 email steps, and quality-checked copy — ready to review and send.",
  },
];

const FEATURES = [
  {
    icon: Sparkles,
    title: "Voice-matched sequences",
    body: "Not templates. Not \u201CAI-powered\u201D filler. Every sequence is grounded in your actual tone, phrase preferences, and the things you never say — built from your best-performing emails.",
  },
  {
    icon: Users,
    title: "Contact intelligence",
    body: "Every lead is classified as a business owner or referral advocate and scored 0–100 for fit. The wrong contacts get flagged before a single word is written.",
  },
  {
    icon: Layers,
    title: "3-step sequences, not blasts",
    body: "Step 1 opens with something specific. Step 2 follows up with a different angle. Step 3 closes. Subject lines included. Sequence logic built in.",
  },
  {
    icon: Zap,
    title: "Parallel enrichment",
    body: "Apollo and LinkedIn data pulled simultaneously across all contacts. 25 contacts enrich and generate in under 90 seconds.",
  },
  {
    icon: ShieldCheck,
    title: "Built-in quality gates",
    body: "12 checks per email — length, CTA present, no filler phrases, no taboo words, valid signature. Bad drafts get flagged, not exported.",
  },
  {
    icon: FileText,
    title: "One-click export",
    body: "Two CSVs ready when you're done: a full pipeline output and an Instantly import file. No reformatting, no column mapping.",
  },
];

const STATS = [
  { value: "3", label: "email steps per sequence" },
  { value: "<90s", label: "per 25 contacts" },
  { value: "12", label: "quality checks per email" },
  { value: "0–100", label: "fit score per lead" },
];

const FAQ = [
  {
    q: "What does \u201Cin your voice\u201D actually mean?",
    a: "Not a style dropdown. Your best-performing emails were parsed into a voice profile — tone traits, preferred phrases, and a list of things you never write. Every generated sequence inherits it automatically.",
  },
  {
    q: "Do I need API keys to try it?",
    a: "No. Open the Demo tab, tick \u201CUse built-in sample file,\u201D and hit Run. No sign-up, no credit card, no configuration. The sample runs in dry-run mode so there\u2019s no LLM cost either.",
  },
  {
    q: "Can I bring my own contact list?",
    a: 'Yes. Drop any CSV from Apollo, LinkedIn, or Hunter. ForgeReach normalizes headers automatically, so your export works as-is — "First Name," "first_name," "firstName" — all fine.',
  },
  {
    q: "What's the difference between an owner and a referral advocate?",
    a: "Business owners are direct buyers — they buy from you. Referral advocates (insurance agents, wealth managers, CPAs) send you warm introductions. ForgeReach scores and sequences each type with a different approach.",
  },
  {
    q: "Is this safe to send immediately?",
    a: "Enable dry run to generate and preview sequences without calling the LLM. When you're ready, review the output in Instantly before any email leaves your inbox. You stay in control.",
  },
];

/* ─── Page ───────────────────────────────────────────────────────────────── */

export default function LandingPage() {
  return (
    <>
      <SiteHeader />

      {/* ── Hero ── */}
      <section className="relative overflow-hidden border-b bg-background">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,hsl(var(--primary)/0.12),transparent)]" />
        <div className="mx-auto max-w-4xl px-6 py-24 text-center md:py-32">
          <Badge variant="outline" className="mb-6 border-primary/30 text-primary">
            AI outbound for blue-collar operators
          </Badge>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            Outreach that sounds like you —{" "}
            <span className="text-primary">at 10× the scale.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            Drop a contact list. ForgeReach scores every lead, enriches their profile, and
            writes a 3-step email sequence in your voice. Campaign-ready in under 90 seconds.
          </p>
          <div className="mt-10 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <Button size="lg" asChild>
              <Link href="/demo">
                Try the demo <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="#how-it-works">See how it works</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* ── Stats bar ── */}
      <section className="border-b bg-muted/40">
        <div className="mx-auto max-w-5xl px-6 py-8">
          <dl className="grid grid-cols-2 gap-6 md:grid-cols-4">
            {STATS.map((s) => (
              <div key={s.label} className="text-center">
                <dt className="text-3xl font-bold tracking-tight text-primary">{s.value}</dt>
                <dd className="mt-1 text-xs text-muted-foreground">{s.label}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* ── Pain ── */}
      <section className="border-b">
        <div className="mx-auto max-w-5xl px-6 py-20">
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            The problem
          </p>
          <h2 className="mb-10 text-3xl font-bold tracking-tight">
            Manual outreach doesn't scale. <br className="hidden sm:block" />
            Generic outreach doesn't convert.
          </h2>
          <div className="grid gap-4 md:grid-cols-3">
            {PAIN_POINTS.map((p) => (
              <Card key={p.label} className="border-destructive/20 bg-destructive/5">
                <CardContent className="p-6">
                  <p className="mb-3 font-semibold leading-snug">{p.label}</p>
                  <p className="text-sm text-muted-foreground leading-relaxed">{p.body}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section id="how-it-works" className="border-b bg-muted/30">
        <div className="mx-auto max-w-5xl px-6 py-20">
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            How it works
          </p>
          <h2 className="mb-12 text-3xl font-bold tracking-tight">Three steps. Under 90 seconds.</h2>
          <div className="grid gap-8 md:grid-cols-3">
            {HOW_IT_WORKS.map((step, i) => (
              <div key={step.step} className="relative">
                {i < HOW_IT_WORKS.length - 1 && (
                  <div className="absolute top-5 left-full hidden w-full -translate-x-1/2 border-t border-dashed border-border md:block" />
                )}
                <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-bold">
                  {step.step}
                </div>
                <h3 className="mb-2 text-base font-semibold">{step.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{step.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="border-b">
        <div className="mx-auto max-w-5xl px-6 py-20">
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            What's inside
          </p>
          <h2 className="mb-12 text-3xl font-bold tracking-tight">
            Every part of the pipeline, handled.
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
            {FEATURES.map((f) => (
              <Card key={f.title}>
                <CardContent className="p-6">
                  <f.icon className="mb-3 h-5 w-5 text-primary" />
                  <h3 className="mb-2 font-semibold">{f.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{f.body}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ── Comparison ── */}
      <section className="border-b bg-muted/30">
        <div className="mx-auto max-w-3xl px-6 py-20">
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            The alternative
          </p>
          <h2 className="mb-10 text-3xl font-bold tracking-tight">
            What the old way costs you.
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Card className="border-destructive/20 bg-destructive/5">
              <CardContent className="p-6">
                <p className="mb-4 font-semibold text-destructive">Without ForgeReach</p>
                <ul className="space-y-3 text-sm">
                  {[
                    "3–4 days to write 200 personalized sequences",
                    "No consistency — every rep sounds different",
                    "Zero visibility into which contacts are worth pursuing",
                    "Manual enrichment, manual scoring, manual export",
                    "Campaigns get stale before they launch",
                  ].map((item) => (
                    <li key={item} className="flex items-start gap-2 text-muted-foreground">
                      <span className="mt-0.5 text-destructive font-bold shrink-0">✕</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
            <Card className="border-primary/20 bg-primary/5">
              <CardContent className="p-6">
                <p className="mb-4 font-semibold text-primary">With ForgeReach</p>
                <ul className="space-y-3 text-sm">
                  {[
                    "200 sequences in under 90 seconds",
                    "Every email in the same proven voice",
                    "0–100 fit score on every lead before you write a word",
                    "Enrichment, scoring, and export fully automated",
                    "Launch the same day you pull the list",
                  ].map((item) => (
                    <li key={item} className="flex items-start gap-2 text-muted-foreground">
                      <CheckCircle2 className="mt-0.5 h-4 w-4 text-primary shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section className="border-b">
        <div className="mx-auto max-w-2xl px-6 py-20">
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            FAQ
          </p>
          <h2 className="mb-8 text-3xl font-bold tracking-tight">Common questions.</h2>
          <div>
            {FAQ.map((item) => (
              <FaqItem key={item.q} q={item.q} a={item.a} />
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="bg-muted/30">
        <div className="mx-auto max-w-2xl px-6 py-24 text-center">
          <h2 className="text-3xl font-bold tracking-tight">
            Ready to build your first campaign?
          </h2>
          <p className="mx-auto mt-4 max-w-md text-muted-foreground">
            No sign-up. No credit card. Run the built-in sample file and see a full
            3-step sequence generated in your voice in under 30 seconds.
          </p>
          <div className="mt-8">
            <Button size="lg" asChild>
              <Link href="/demo">
                Try the demo <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t">
        <div className="mx-auto max-w-7xl px-6 py-6 flex flex-col items-center justify-between gap-4 sm:flex-row">
          <p className="text-sm font-semibold tracking-tight">ForgeReach</p>
          <p className="text-xs text-muted-foreground">
            AI outbound for blue-collar operators · Built by IFG
          </p>
          <nav className="flex gap-4 text-xs text-muted-foreground">
            <Link href="/demo" className="hover:text-foreground">Demo</Link>
            <Separator orientation="vertical" className="h-3 self-center" />
            <Link href="/samples" className="hover:text-foreground">Samples</Link>
          </nav>
        </div>
      </footer>
    </>
  );
}
