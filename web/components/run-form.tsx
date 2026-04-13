"use client";
import * as React from "react";
import { useDropzone } from "react-dropzone";
import { Upload, X, FileText, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import type { ProspectSource, RunMode, RunRequest } from "@/lib/types";
import { cn } from "@/lib/utils";

export type TargetAudience = "owner" | "referral_advocate" | "mixed";

export interface RunFormValues {
  mode: RunMode;
  files: File[];
  useSample: boolean;
  enrich: boolean;
  research: boolean;
  research_depth: "minimal" | "standard" | "deep";
  require_verified_email: boolean;
  require_identity_confirmation: boolean;
  use_master_persona: boolean;
  few_shot_k: number;
  min_qualification_score: number;
  min_fit_score_for_enrich: number;
  target_audience: TargetAudience;
  state: string;
  prospect_sources: ProspectSource[];
  prospect_limit: number;
  hunter_domains: string;
  sales_nav_titles: string;
  sales_nav_companies: string;
  min_ebitda: number;
}

const DEFAULTS: RunFormValues = {
  mode: "csv_only",
  files: [],
  useSample: false,
  enrich: true,
  research: true,
  research_depth: "standard",
  require_verified_email: true,
  require_identity_confirmation: true,
  use_master_persona: true,
  few_shot_k: 3,
  min_qualification_score: 60,
  min_fit_score_for_enrich: 65,
  target_audience: "mixed",
  state: "CO",
  prospect_sources: ["hunter"],
  prospect_limit: 25,
  hunter_domains: "",
  sales_nav_titles: "owner, founder, ceo",
  sales_nav_companies: "",
  min_ebitda: 3_000_000,
};

export function toRunRequest(v: RunFormValues, fileIds: string[]): RunRequest {
  return {
    mode: v.mode,
    csv_file_ids: v.useSample ? ["sample"] : fileIds,
    dry_run: false,
    enrich: v.enrich,
    research: v.research,
    research_depth: v.research_depth,
    require_verified_email: v.require_verified_email,
    require_identity_confirmation: v.require_identity_confirmation,
    use_master_persona: v.use_master_persona,
    master_persona_path: "MASTER.md",
    voice_profile_path: "data/voice_profile.json",
    few_shot_k: v.few_shot_k,
    min_qualification_score: v.min_qualification_score,
    min_fit_score_for_enrich: v.min_fit_score_for_enrich,
    referral_advocates_only: v.target_audience === "referral_advocate",
    state: v.state,
    prospect_sources: v.prospect_sources,
    prospect_limit: v.prospect_limit,
    hunter_domains: v.hunter_domains
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    sales_nav_titles: v.sales_nav_titles
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    sales_nav_companies: v.sales_nav_companies
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    min_ebitda: v.min_ebitda,
  };
}

function AdvancedAccordion({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = React.useState(false);
  return (
    <div className="border-t pt-3 mt-1">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
      >
        Advanced settings
        <ChevronDown
          className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")}
        />
      </button>
      {open && <div className="mt-3 space-y-4">{children}</div>}
    </div>
  );
}

const AUDIENCE_OPTIONS: { value: TargetAudience; label: string; description: string }[] = [
  {
    value: "mixed",
    label: "Mixed List (Auto-detect)",
    description: "Classify each contact automatically",
  },
  {
    value: "owner",
    label: "Blue-Collar Owners",
    description: ">$3M EBITDA target profile",
  },
  {
    value: "referral_advocate",
    label: "Referral Advocates (RAs)",
    description: "Advisors, bankers, and brokers",
  },
];

function helperForSource(source: ProspectSource): string {
  if (source === "hunter") {
    return "Works on free plans. Needs domains and usually returns email/name/title first.";
  }
  if (source === "linkedin_sales_nav") {
    return "Sales Navigator-style discovery. Use title/company seed terms for tighter targeting.";
  }
  return "Richer company + LinkedIn data when your Apollo plan allows people search.";
}

export function RunForm({
  value,
  onChange,
  disabled,
}: {
  value: RunFormValues;
  onChange: (v: RunFormValues) => void;
  disabled?: boolean;
}) {
  const v = value;
  const set = <K extends keyof RunFormValues>(k: K, val: RunFormValues[K]) =>
    onChange({ ...v, [k]: val });

  const onDrop = React.useCallback(
    (accepted: File[]) => {
      onChange({ ...v, files: [...v.files, ...accepted], useSample: false });
    },
    [v, onChange]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"] },
    disabled,
  });

  const removeFile = (idx: number) =>
    set(
      "files",
      v.files.filter((_, i) => i !== idx)
    );

  const toggleSource = (src: ProspectSource, checked: boolean) => {
    const next = checked
      ? Array.from(new Set([...v.prospect_sources, src]))
      : v.prospect_sources.filter((s) => s !== src);
    set("prospect_sources", next);
  };

  const ownerFieldsDisabled = disabled || v.target_audience === "referral_advocate";
  const hunterSelected = v.prospect_sources.includes("hunter");
  const hunterDomainsProvided =
    v.hunter_domains
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean).length > 0;
  const hunterDomainsRequired = v.mode === "api_discovery" && hunterSelected;

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      {/* Column 1: Data Source */}
      <Card>
        <CardHeader>
          <CardTitle>Data Source</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <RadioGroup
            value={v.mode}
            onValueChange={(val) => set("mode", val as RunMode)}
            disabled={disabled}
            className="gap-3"
          >
            {(
              [
                ["csv_only", "Use uploaded list"],
                ["api_discovery", "Find new contacts"],
                ["csv_plus_api", "Merge uploaded + discovered"],
              ] as [RunMode, string][]
            ).map(([val, label]) => (
              <div key={val} className="flex items-center gap-2">
                <RadioGroupItem value={val} id={`mode-${val}`} />
                <Label htmlFor={`mode-${val}`} className="cursor-pointer">
                  {label}
                </Label>
              </div>
            ))}
          </RadioGroup>

          <div className="space-y-2">
            <div
              {...getRootProps()}
              className={cn(
                "rounded-md border border-dashed p-5 text-center text-sm cursor-pointer transition-colors",
                isDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/30",
                disabled && "opacity-50 pointer-events-none"
              )}
            >
              <input {...getInputProps()} />
              <Upload className="mx-auto mb-2 h-5 w-5 text-muted-foreground" />
              <div className="font-medium">Drop CSVs here or click to browse</div>
              <div className="text-xs text-muted-foreground">Accepts .csv files</div>
            </div>

            <div className="flex items-center gap-2 pl-1">
              <Checkbox
                id="use-sample"
                checked={v.useSample}
                onCheckedChange={(val) => {
                  const checked = val === true;
                  onChange({ ...v, useSample: checked, files: checked ? [] : v.files });
                }}
                disabled={disabled}
              />
              <Label htmlFor="use-sample" className="cursor-pointer text-sm text-muted-foreground">
                Use built-in sample file (Apollo random 5)
              </Label>
            </div>
          </div>

          {v.files.length > 0 && (
            <div className="space-y-1">
              {v.files.map((f, i) => (
                <div
                  key={`${f.name}-${i}`}
                  className="flex items-center justify-between rounded-md border bg-muted/30 px-3 py-1.5 text-sm"
                >
                  <div className="flex items-center gap-2 truncate">
                    <FileText className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                    <span className="truncate">{f.name}</span>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {(f.size / 1024).toFixed(1)} KB
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeFile(i)}
                    className="text-muted-foreground hover:text-foreground"
                    aria-label={`Remove ${f.name}`}
                    disabled={disabled}
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Column 2: Target Audience */}
      <Card>
        <CardHeader>
          <CardTitle>Target Audience</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <RadioGroup
            value={v.target_audience}
            onValueChange={(val) => set("target_audience", val as TargetAudience)}
            disabled={disabled}
            className="gap-3"
          >
            {AUDIENCE_OPTIONS.map(({ value: val, label, description }) => (
              <div key={val} className="flex items-start gap-2.5">
                <RadioGroupItem value={val} id={`audience-${val}`} className="mt-0.5" />
                <div>
                  <Label htmlFor={`audience-${val}`} className="cursor-pointer leading-tight">
                    {label}
                  </Label>
                  <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
                </div>
              </div>
            ))}
          </RadioGroup>

          <div
            className={cn(
              "space-y-4 transition-opacity",
              ownerFieldsDisabled && !disabled && "opacity-40 pointer-events-none"
            )}
          >
            <div className="space-y-1.5">
              <Label htmlFor="state">State</Label>
              <Input
                id="state"
                value={v.state}
                onChange={(e) => set("state", e.target.value.toUpperCase().slice(0, 2))}
                disabled={ownerFieldsDisabled}
                maxLength={2}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="min-ebitda">Min. EBITDA</Label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">
                  $
                </span>
                <Input
                  id="min-ebitda"
                  type="number"
                  min={0}
                  step={100000}
                  value={v.min_ebitda}
                  onChange={(e) => set("min_ebitda", Number(e.target.value) || 0)}
                  disabled={ownerFieldsDisabled}
                  className="pl-7"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Estimated from annual revenue × 0.15
              </p>
            </div>
          </div>

          <AdvancedAccordion>
            <div className="space-y-2">
              <Label>Contact sources</Label>
              <div className="flex flex-col gap-2">
                {(["hunter", "apollo", "linkedin_sales_nav"] as ProspectSource[]).map((src) => (
                  <div key={src} className="flex items-center gap-2">
                    <Checkbox
                      id={`src-${src}`}
                      checked={v.prospect_sources.includes(src)}
                      onCheckedChange={(c) => toggleSource(src, c === true)}
                      disabled={disabled}
                    />
                    <Label htmlFor={`src-${src}`} className="cursor-pointer capitalize">
                      {src}
                    </Label>
                    <span className="text-[11px] text-muted-foreground">
                      {helperForSource(src)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="prospect-limit">Max contacts to find</Label>
              <Input
                id="prospect-limit"
                type="number"
                min={1}
                value={v.prospect_limit}
                onChange={(e) => set("prospect_limit", Number(e.target.value) || 0)}
                disabled={disabled}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="hunter-domains">Hunter domains</Label>
              <Input
                id="hunter-domains"
                placeholder="roofco.com, hvacpros.com"
                value={v.hunter_domains}
                onChange={(e) => set("hunter_domains", e.target.value)}
                disabled={disabled}
              />
              {hunterDomainsRequired && !hunterDomainsProvided && (
                <p className="text-xs text-amber-600">
                  Add at least one domain for Hunter discovery mode.
                </p>
              )}
            </div>

            {v.prospect_sources.includes("linkedin_sales_nav") && (
              <>
                <div className="space-y-1.5">
                  <Label htmlFor="sales-nav-titles">Sales Navigator seed titles</Label>
                  <Input
                    id="sales-nav-titles"
                    placeholder="owner, founder, president, ceo"
                    value={v.sales_nav_titles}
                    onChange={(e) => set("sales_nav_titles", e.target.value)}
                    disabled={disabled}
                  />
                  <p className="text-xs text-muted-foreground">
                    Comma-separated titles to prioritize in people search.
                  </p>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="sales-nav-companies">Sales Navigator seed companies</Label>
                  <Input
                    id="sales-nav-companies"
                    placeholder="Diamond Companies, Iron Woman Construction"
                    value={v.sales_nav_companies}
                    onChange={(e) => set("sales_nav_companies", e.target.value)}
                    disabled={disabled}
                  />
                  <p className="text-xs text-muted-foreground">
                    Optional comma-separated target companies to narrow discovery.
                  </p>
                </div>
              </>
            )}

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <Label>Example density</Label>
                  <p className="text-xs text-muted-foreground mt-0.5">Voice examples per email step</p>
                </div>
                <Badge variant="outline">{v.few_shot_k}</Badge>
              </div>
              <Slider
                min={1}
                max={5}
                step={1}
                value={[v.few_shot_k]}
                onValueChange={(vals) => set("few_shot_k", vals[0] ?? v.few_shot_k)}
                disabled={disabled}
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <Label>Qualification threshold</Label>
                  <p className="text-xs text-muted-foreground mt-0.5">Drop contacts scoring below</p>
                </div>
                <Badge variant="outline">{v.min_qualification_score}</Badge>
              </div>
              <Slider
                min={40}
                max={90}
                step={1}
                value={[v.min_qualification_score]}
                onValueChange={(vals) =>
                  set("min_qualification_score", vals[0] ?? v.min_qualification_score)
                }
                disabled={disabled}
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <Label>Min fit score for enrichment</Label>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Skip contacts below this score before enrichment
                  </p>
                </div>
                <Badge variant="outline">{v.min_fit_score_for_enrich}</Badge>
              </div>
              <Slider
                min={0}
                max={90}
                step={1}
                value={[v.min_fit_score_for_enrich]}
                onValueChange={(vals) =>
                  set("min_fit_score_for_enrich", vals[0] ?? v.min_fit_score_for_enrich)
                }
                disabled={disabled}
              />
            </div>

            <div className="space-y-2 rounded-md border p-3">
              <Label className="text-sm">Quality gate</Label>
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <Label htmlFor="require-verified-email">Require verified email</Label>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Only pass contacts with verified deliverable email
                    </p>
                  </div>
                  <Switch
                    id="require-verified-email"
                    checked={v.require_verified_email}
                    onCheckedChange={(c) => set("require_verified_email", c)}
                    disabled={disabled}
                  />
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <Label htmlFor="require-identity">Require identity confirmation</Label>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Needs LinkedIn or identified decision-maker name
                    </p>
                  </div>
                  <Switch
                    id="require-identity"
                    checked={v.require_identity_confirmation}
                    onCheckedChange={(c) => set("require_identity_confirmation", c)}
                    disabled={disabled}
                  />
                </div>
              </div>
            </div>
          </AdvancedAccordion>
        </CardContent>
      </Card>

      {/* Column 3: AI Generation */}
      <Card>
        <CardHeader>
          <CardTitle>AI Generation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <Label htmlFor="enrich">Enrichment</Label>
              <p className="text-xs text-muted-foreground mt-0.5">
                Fill missing contact and company fields
              </p>
            </div>
            <Switch
              id="enrich"
              checked={v.enrich}
              onCheckedChange={(c) => set("enrich", c)}
              disabled={disabled}
            />
          </div>

          <div className="flex items-center justify-between gap-4">
            <div>
              <Label htmlFor="master-persona">Apply Kory Mitchell&#39;s Voice</Label>
              <p className="text-xs text-muted-foreground mt-0.5">
                Write authentic, blue-collar founder outreach
              </p>
            </div>
            <Switch
              id="master-persona"
              checked={v.use_master_persona}
              onCheckedChange={(c) => set("use_master_persona", c)}
              disabled={disabled}
            />
          </div>

          <div className="flex items-center justify-between gap-4">
            <div>
              <Label htmlFor="research">Agentic research</Label>
              <p className="text-xs text-muted-foreground mt-0.5">
                Serper + website + Hunter orchestration before qualification
              </p>
            </div>
            <Switch
              id="research"
              checked={v.research}
              onCheckedChange={(c) => set("research", c)}
              disabled={disabled}
            />
          </div>

          {v.research && (
            <div className="space-y-2">
              <Label>Research depth</Label>
              <RadioGroup
                value={v.research_depth}
                onValueChange={(val) =>
                  set("research_depth", val as RunFormValues["research_depth"])
                }
                disabled={disabled}
                className="grid grid-cols-3 gap-2"
              >
                {([
                  ["minimal", "Minimal"],
                  ["standard", "Standard"],
                  ["deep", "Deep"],
                ] as const).map(([val, label]) => (
                  <Label
                    key={val}
                    htmlFor={`research-depth-${val}`}
                    className={cn(
                      "flex cursor-pointer items-center justify-center rounded-md border px-2 py-1.5 text-xs",
                      v.research_depth === val
                        ? "border-primary bg-primary/5 text-foreground"
                        : "border-muted-foreground/30 text-muted-foreground"
                    )}
                  >
                    <RadioGroupItem
                      value={val}
                      id={`research-depth-${val}`}
                      className="sr-only"
                    />
                    {label}
                  </Label>
                ))}
              </RadioGroup>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export { DEFAULTS as DEFAULT_RUN_FORM };
