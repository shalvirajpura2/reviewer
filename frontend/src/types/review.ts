export interface ReviewRiskItem {
  label: string;
  severity: "low" | "medium" | "high";
}

export interface ReviewRiskBreakdownItem {
  label: string;
  score: number;
  level: "low" | "medium" | "high";
  summary: string;
}

export interface ReviewScoreMovementItem {
  sha?: string;
  label: string;
}

export interface ReviewFileGroup {
  label: string;
  files: string[];
  level: "low" | "medium" | "high";
}

export interface ReviewSignalEvidence {
  label: string;
  severity: "low" | "medium" | "high";
  evidence: string[];
}

export interface ReviewRecommendation {
  id: string;
  title: string;
  detail: string;
  priority: "now" | "soon" | "nice_to_have";
}

export interface ReviewTopRiskFile {
  filename: string;
  risk_level: "low" | "medium" | "high";
  reasons: string[];
  reviewer_hints: string[];
  patch_excerpt: string[];
  changes: number;
  areas: string[];
  is_sensitive: boolean;
  blob_url?: string | null;
}

export interface ReviewCheckRun {
  name: string;
  status: string;
  conclusion?: string | null;
  details_url?: string | null;
}

export interface ReviewSafeguards {
  ci_state: "passing" | "failing" | "pending" | "missing" | "unknown";
  status_label: string;
  status_tone: "safe" | "warn" | "danger" | "idle";
  summary: string;
  checks_total: number;
  checks_passed: number;
  checks_failed: number;
  tests_changed: boolean;
  missing_safeguards: string[];
  check_runs: ReviewCheckRun[];
}

export interface ReviewCoverage {
  files_analyzed: number;
  total_files: number;
  patchless_files: number;
  is_partial: boolean;
  partial_reasons: string[];
}

export interface ReviewProvenance {
  cache_status: "live" | "cached" | "fallback";
  confidence_in_score: "high" | "medium" | "low";
  data_sources: string[];
  score_version: string;
  coverage: ReviewCoverage;
  source_updated_at?: string;
}

export interface ReviewResult {
  pr_title: string;
  repo_name: string;
  pr_url: string;
  author?: string;
  base_branch?: string;
  head_branch?: string;
  created_at?: string;
  updated_at?: string;
  report_status?: "demo" | "live" | "cached" | "fallback";
  merge_confidence: number;
  verdict: "mergeable" | "focused review" | "review needed";
  summary: string;
  verdict_text: string;
  confidence_label: BackendAnalysisResult["label"];
  top_risks: ReviewRiskItem[];
  next_actions: string[];
  changed_areas: string[];
  limitations: string[];
  stats: {
    files_changed: number;
    files_analyzed: number;
    additions: number;
    deletions: number;
    commits: number;
    patchless_files: number;
  };
  risk_breakdown: ReviewRiskBreakdownItem[];
  score_movement: ReviewScoreMovementItem[];
  file_groups: ReviewFileGroup[];
  review_focus: string[];
  signal_evidence: ReviewSignalEvidence[];
  review_plan: ReviewRecommendation[];
  top_risk_files: ReviewTopRiskFile[];
  safeguards: ReviewSafeguards;
  provenance?: ReviewProvenance;
}

export interface BackendMetadata {
  owner: string;
  repo: string;
  pull_number: number;
  repo_full_name: string;
  title: string;
  author: string;
  author_avatar_url: string;
  base_branch: string;
  head_branch: string;
  commits: number;
  additions: number;
  deletions: number;
  changed_files: number;
  html_url: string;
  created_at: string;
  updated_at: string;
}

export interface BackendRiskSignal {
  id: string;
  label: string;
  severity: "low" | "medium" | "high";
  evidence: string[];
  score_impact: number;
  breakdown_key: string;
}

export interface BackendRecommendationItem {
  id: string;
  title: string;
  detail: string;
  priority: "now" | "soon" | "nice_to_have";
}

export interface BackendChangedFile {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
  changes: number;
  patch?: string;
  blob_url?: string;
  previous_filename?: string;
  areas: string[];
  tags: string[];
  is_sensitive: boolean;
  blast_radius_weight: number;
  symbol_hints: string[];
}

export interface BackendChangedFileGroup {
  label: string;
  files: BackendChangedFile[];
}

export interface BackendTopRiskFile {
  filename: string;
  risk_level: "low" | "medium" | "high";
  reasons: string[];
  reviewer_hints: string[];
  patch_excerpt: string[];
  changes: number;
  areas: string[];
  is_sensitive: boolean;
  blob_url?: string | null;
}

export interface BackendCommitSummary {
  sha: string;
  message: string;
  author: string;
  authored_at?: string | null;
  html_url?: string | null;
}

export interface BackendCheckRunSummary {
  name: string;
  status: string;
  conclusion?: string | null;
  details_url?: string | null;
}

export interface BackendSafeguardSummary {
  ci_state: "passing" | "failing" | "pending" | "missing" | "unknown";
  summary: string;
  checks_total: number;
  checks_passed: number;
  checks_failed: number;
  tests_changed: boolean;
  missing_safeguards: string[];
  check_runs: BackendCheckRunSummary[];
}

export interface BackendAnalysisCoverage {
  files_analyzed: number;
  total_files: number;
  patchless_files: number;
  is_partial: boolean;
  partial_reasons: string[];
}

export interface BackendAnalysisContext {
  confidence_in_score: "high" | "medium" | "low";
  summary: string;
  limitations: string[];
  data_sources: string[];
  cache_status: "live" | "cached" | "fallback";
  coverage: BackendAnalysisCoverage;
}

export interface BackendAnalysisResult {
  metadata: BackendMetadata;
  score: number;
  label: "high confidence" | "moderate confidence" | "low confidence" | "risky to merge";
  verdict: string;
  review_focus: string[];
  affected_areas: string[];
  risk_breakdown: Array<{ key: string; label: string; score: number; summary: string }>;
  triggered_signals: BackendRiskSignal[];
  recommendations: BackendRecommendationItem[];
  safeguards: BackendSafeguardSummary;
  changed_file_groups: BackendChangedFileGroup[];
  top_risk_files: BackendTopRiskFile[];
  commits: BackendCommitSummary[];
  score_summary: {
    base_score: number;
    total_penalty: number;
    total_relief: number;
    score_version: string;
  };
  analysis_context: BackendAnalysisContext;
}

