export type RunMode = "csv_only" | "api_discovery" | "csv_plus_api";

export type ProspectSource = "apollo" | "hunter";

export interface ConfigHealth {
  openrouter: boolean;
  apollo: boolean;
  hunter: boolean;
  apify: boolean;
  model: string;
}

export interface UploadResponse {
  file_ids: string[];
}

export interface RunRequest {
  mode: RunMode;
  csv_file_ids: string[];
  dry_run: boolean;
  enrich: boolean;
  use_master_persona: boolean;
  master_persona_path: string;
  voice_profile_path: string;
  few_shot_k: number;
  min_qualification_score: number;
  min_fit_score_for_enrich: number;
  referral_advocates_only: boolean;
  state: string;
  prospect_sources: ProspectSource[];
  prospect_limit: number;
  hunter_domains: string[];
  min_ebitda: number;
}

export interface RunResponse {
  run_id: string;
  stream_url: string;
}

export type RunStage =
  | "ingest"
  | "research"  // NEW
  | "enrich"
  | "classify"
  | "generate"
  | "validate"
  | "export";

export const RUN_STAGES: RunStage[] = [
  "ingest",
  "research",  // NEW
  "enrich",
  "classify",
  "generate",
  "validate",
  "export",
];

export interface StageEvent {
  stage: RunStage;
}

export interface ProgressEvent {
  current: number;
  total: number;
  stage: string;
}

export interface RunReport {
  total?: number;
  enriched?: number;
  qualified?: number;
  high_priority?: number;
  review_flagged?: number;
  avg_fit_score?: number;
  skipped_low_fit_count?: number;
  skipped_missing_linkedin_count?: number;
  discovered_count?: number;
  apollo_search_attempts?: number;
  apollo_search_failures?: number;
  apollo_empty_batches?: number;
  apollo_fallback_attempts?: number;
  apollo_fallback_successes?: number;
  discovery_error_count?: number;
  research_contacts_processed?: number;
  research_queries_serper?: number;
  research_websites_scraped?: number;
  research_emails_found?: number;
  research_emails_verified?: number;
  research_decision_makers_found?: number;
  research_company_summaries_extracted?: number;
  research_failure_count?: number;

  // New quality gate metrics
  skipped_unverified_email_count?: number;
  skipped_no_identity_count?: number;

  // Audience & maturity metrics
  avg_audience_confidence?: number;
  avg_company_maturity_score?: number;
  discovery_errors?: string[];
  [key: string]: unknown;
}

export interface DoneEvent {
  run_id: string;
  report: RunReport;
  output_csv: string;
  instantly_csv: string;
}

export interface SampleContact {
  full_name: string;
  title: string;
  company: string;
  audience: string;
  subject_1: string;
  email_step_1: string;
  subject_2: string;
  email_step_2: string;
  subject_3: string;
  email_step_3: string;
}

export interface ContactRow {
  full_name: string;
  company: string;
  audience: string;
  fit_score: string | number;
  qualification_tier: string;
  review_flag: string;
  title?: string;
  email?: string;
  subject_1?: string;
  email_step_1?: string;
  subject_2?: string;
  email_step_2?: string;
  subject_3?: string;
  email_step_3?: string;
  [key: string]: string | number | undefined;
}

export type RunStatus = "idle" | "uploading" | "running" | "done" | "error";
