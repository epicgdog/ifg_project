"use client";
import * as React from "react";
import { useDropzone } from "react-dropzone";
import { Upload, X, FileText } from "lucide-react";
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

export interface RunFormValues {
  mode: RunMode;
  files: File[];
  useSample: boolean;
  dry_run: boolean;
  enrich: boolean;
  use_master_persona: boolean;
  few_shot_k: number;
  min_qualification_score: number;
  referral_advocates_only: boolean;
  state: string;
  prospect_sources: ProspectSource[];
  prospect_limit: number;
  hunter_domains: string;
  min_ebitda: number;
}

const DEFAULTS: RunFormValues = {
  mode: "csv_only",
  files: [],
  useSample: false,
  dry_run: true,
  enrich: true,
  use_master_persona: true,
  few_shot_k: 3,
  min_qualification_score: 60,
  referral_advocates_only: false,
  state: "CO",
  prospect_sources: ["apollo"],
  prospect_limit: 25,
  hunter_domains: "",
  min_ebitda: 3_000_000,
};

export function toRunRequest(v: RunFormValues, fileIds: string[]): RunRequest {
  return {
    mode: v.mode,
    csv_file_ids: v.useSample ? ["sample"] : fileIds,
    dry_run: v.dry_run,
    enrich: v.enrich,
    use_master_persona: v.use_master_persona,
    master_persona_path: "MASTER.md",
    voice_profile_path: "data/voice_profile.json",
    few_shot_k: v.few_shot_k,
    min_qualification_score: v.min_qualification_score,
    referral_advocates_only: v.referral_advocates_only,
    state: v.state,
    prospect_sources: v.prospect_sources,
    prospect_limit: v.prospect_limit,
    hunter_domains: v.hunter_domains
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    min_ebitda: v.min_ebitda,
  };
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
      set("files", [...v.files, ...accepted]);
      set("useSample", false);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [v.files]
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

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      {/* Left: mode + upload */}
      <Card>
        <CardHeader>
          <CardTitle>Mode & Source</CardTitle>
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
                ["csv_only", "CSV only"],
                ["api_discovery", "API discovery"],
                ["csv_plus_api", "CSV + API merge"],
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
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-center gap-2">
            <Checkbox
              id="use-sample"
              checked={v.useSample}
              onCheckedChange={(val) => {
                const checked = val === true;
                set("useSample", checked);
                if (checked) set("files", []);
              }}
              disabled={disabled}
            />
            <Label htmlFor="use-sample" className="cursor-pointer text-sm">
              Use sample file
            </Label>
          </div>
        </CardContent>
      </Card>

      {/* Middle: generation settings */}
      <Card>
        <CardHeader>
          <CardTitle>Generation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="flex items-center justify-between">
            <Label htmlFor="dry-run">Dry run</Label>
            <Switch
              id="dry-run"
              checked={v.dry_run}
              onCheckedChange={(c) => set("dry_run", c)}
              disabled={disabled}
            />
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="master-persona">Use MASTER persona</Label>
            <Switch
              id="master-persona"
              checked={v.use_master_persona}
              onCheckedChange={(c) => set("use_master_persona", c)}
              disabled={disabled}
            />
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="enrich">Enrichment</Label>
            <Switch
              id="enrich"
              checked={v.enrich}
              onCheckedChange={(c) => set("enrich", c)}
              disabled={disabled}
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Few-shot k</Label>
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
              <Label>Min qualification score</Label>
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
        </CardContent>
      </Card>

      {/* Right: sourcing & ICP */}
      <Card>
        <CardHeader>
          <CardTitle>Sourcing & ICP</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="flex items-center justify-between">
            <Label htmlFor="referral-only">Referral advocates only</Label>
            <Switch
              id="referral-only"
              checked={v.referral_advocates_only}
              onCheckedChange={(c) => set("referral_advocates_only", c)}
              disabled={disabled}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="state">State</Label>
            <Input
              id="state"
              value={v.state}
              onChange={(e) => set("state", e.target.value.toUpperCase().slice(0, 2))}
              disabled={disabled}
              maxLength={2}
            />
          </div>

          <div className="space-y-2">
            <Label>Prospect sources</Label>
            <div className="flex flex-col gap-2">
              {(["apollo", "hunter"] as ProspectSource[]).map((src) => (
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
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="prospect-limit">Prospect limit</Label>
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
              placeholder="acme.com, example.com"
              value={v.hunter_domains}
              onChange={(e) => set("hunter_domains", e.target.value)}
              disabled={disabled}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="min-ebitda">EBITDA minimum</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                $
              </span>
              <Input
                id="min-ebitda"
                type="number"
                min={0}
                step={100000}
                value={v.min_ebitda}
                onChange={(e) => set("min_ebitda", Number(e.target.value) || 0)}
                disabled={disabled}
                className="pl-7"
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Approx. filter; uses annual_revenue × 0.15 as proxy
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export { DEFAULTS as DEFAULT_RUN_FORM };
