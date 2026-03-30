import type {
  BackendAnalysisResult,
  ReviewResult,
  ReviewRecommendation,
  ReviewRiskBreakdownItem,
  ReviewRiskItem,
  ReviewScoreMovementItem,
  ReviewSignalEvidence
} from "../types/review";

function map_verdict(label: BackendAnalysisResult["label"]): ReviewResult["verdict"] {
  if (label === "high confidence") {
    return "mergeable";
  }

  if (label === "moderate confidence" || label === "low confidence") {
    return "focused review";
  }

  return "review needed";
}

function build_summary(result: BackendAnalysisResult) {
  const coverage = result.analysis_context.coverage;

  if (result.analysis_context.cache_status === "fallback") {
    return result.analysis_context.summary;
  }

  if (coverage.is_partial && coverage.partial_reasons.length > 0) {
    return `Partial analysis: ${coverage.partial_reasons[0]}`;
  }

  if (result.analysis_context.summary) {
    return result.analysis_context.summary;
  }

  if (result.triggered_signals.length === 0) {
    return "The pull request looks contained enough to merge with routine review.";
  }

  const primary_signal = result.triggered_signals[0].label.toLowerCase();
  return `${result.verdict}. ${primary_signal} is the main review driver.`;
}

function build_changed_areas(result: BackendAnalysisResult) {
  if (result.affected_areas.length > 0) {
    return result.affected_areas;
  }

  return result.changed_file_groups
    .flatMap((group_item) => group_item.files.map((file_item) => file_item.filename))
    .slice(0, 6);
}

function build_top_risks(result: BackendAnalysisResult): ReviewRiskItem[] {
  if (result.triggered_signals.length > 0) {
    return result.triggered_signals.slice(0, 4).map((item) => ({
      label: item.label.toLowerCase(),
      severity: item.severity
    }));
  }

  return [
    {
      label: "no material risk signals were detected",
      severity: "low"
    }
  ];
}

function build_next_actions(result: BackendAnalysisResult) {
  const next_actions = result.recommendations.length > 0
    ? result.recommendations.slice(0, 5).map((item) => item.title)
    : ["Run a final reviewer pass before merge"];

  if (result.analysis_context.cache_status === "fallback") {
    return ["Retry for a fresh live analysis in a few minutes", ...next_actions].slice(0, 5);
  }

  if (result.analysis_context.coverage.is_partial) {
    return ["Review the remaining files directly on GitHub", ...next_actions].slice(0, 5);
  }

  return next_actions;
}

function map_breakdown_level(score: number): ReviewRiskBreakdownItem["level"] {
  if (score >= 20) {
    return "high";
  }

  if (score >= 10) {
    return "medium";
  }

  return "low";
}

function build_risk_breakdown(result: BackendAnalysisResult): ReviewRiskBreakdownItem[] {
  return result.risk_breakdown.slice(0, 6).map((item) => ({
    label: item.label,
    score: item.score,
    level: map_breakdown_level(item.score),
    summary: item.summary
  }));
}

function build_recent_commits(result: BackendAnalysisResult): ReviewScoreMovementItem[] {
  if (result.commits.length > 0) {
    return result.commits.slice(0, 7).map((item) => ({
      sha: item.sha,
      label: item.message,
      delta: 0
    }));
  }

  return [
    {
      sha: "-",
      label: "No commit data available",
      delta: 0
    }
  ];
}

function build_review_plan(result: BackendAnalysisResult): ReviewRecommendation[] {
  if (result.recommendations.length > 0) {
    return result.recommendations.slice(0, 5).map((item) => ({
      id: item.id,
      title: item.title,
      detail: item.detail,
      priority: item.priority
    }));
  }

  return [
    {
      id: "standard_review",
      title: "Run a standard merge review",
      detail: "The current analysis looks contained, so a normal reviewer pass should be enough before merge.",
      priority: "nice_to_have"
    }
  ];
}

function build_signal_evidence(result: BackendAnalysisResult): ReviewSignalEvidence[] {
  if (result.triggered_signals.length === 0) {
    return [
      {
        label: "No material risk signals were detected",
        severity: "low",
        evidence: ["The current rules engine did not detect any notable merge-risk patterns."]
      }
    ];
  }

  return result.triggered_signals.slice(0, 5).map((item) => ({
    label: item.label,
    severity: item.severity,
    evidence: item.evidence.length > 0 ? item.evidence.slice(0, 4) : ["No explicit evidence captured."]
  }));
}

function build_file_groups(result: BackendAnalysisResult): ReviewResult["file_groups"] {
  return result.changed_file_groups.slice(0, 6).map((group_item) => ({
    label: group_item.label,
    files: group_item.files.slice(0, 5).map((file_item) => file_item.filename),
    level:
      group_item.files.some((file_item) => file_item.is_sensitive || file_item.blast_radius_weight >= 4)
        ? "high"
        : group_item.files.some((file_item) => file_item.blast_radius_weight >= 3)
          ? "medium"
          : "low"
  }));
}

function build_review_focus(result: BackendAnalysisResult) {
  if (result.review_focus.length > 0) {
    return result.review_focus;
  }

  return build_changed_areas(result).slice(0, 4).map((item) => `Review ${item}`);
}

function build_limitations(result: BackendAnalysisResult) {
  const partial_reasons = result.analysis_context.coverage.partial_reasons;
  return [...partial_reasons, ...result.analysis_context.limitations];
}

export function map_analysis_to_review(result: BackendAnalysisResult): ReviewResult {
  return {
    pr_title: result.metadata.title,
    repo_name: `${result.metadata.repo_full_name} #${result.metadata.pull_number}`,
    pr_url: result.metadata.html_url,
    author: `@${result.metadata.author}`,
    base_branch: result.metadata.base_branch,
    head_branch: result.metadata.head_branch,
    created_at: result.metadata.created_at,
    updated_at: result.metadata.updated_at,
    report_status: result.analysis_context.cache_status,
    merge_confidence: result.score,
    verdict: map_verdict(result.label),
    summary: build_summary(result),
    top_risks: build_top_risks(result),
    next_actions: build_next_actions(result),
    changed_areas: build_changed_areas(result),
    limitations: build_limitations(result),
    stats: {
      files_changed: result.metadata.changed_files,
      files_analyzed: result.analysis_context.coverage.files_analyzed,
      additions: result.metadata.additions,
      deletions: result.metadata.deletions,
      commits: result.metadata.commits,
      patchless_files: result.analysis_context.coverage.patchless_files
    },
    risk_breakdown: build_risk_breakdown(result),
    score_movement: build_recent_commits(result),
    file_groups: build_file_groups(result),
    review_focus: build_review_focus(result),
    signal_evidence: build_signal_evidence(result),
    review_plan: build_review_plan(result),
    top_risk_files: result.top_risk_files.slice(0, 5).map((item) => ({
      filename: item.filename,
      risk_level: item.risk_level,
      reasons: item.reasons,
      changes: item.changes,
      areas: item.areas,
      is_sensitive: item.is_sensitive,
      blob_url: item.blob_url
    })),
    provenance: {
      cache_status: result.analysis_context.cache_status,
      confidence_in_score: result.analysis_context.confidence_in_score,
      data_sources: result.analysis_context.data_sources,
      score_version: result.score_summary.score_version,
      coverage: result.analysis_context.coverage,
      source_updated_at: result.metadata.updated_at
    }
  };
}
