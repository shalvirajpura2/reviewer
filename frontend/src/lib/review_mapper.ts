import type {
  BackendAnalysisResult,
  ReviewResult,
  ReviewRecommendation,
  ReviewRiskBreakdownItem,
  ReviewRiskItem,
  ReviewScoreMovementItem,
  ReviewSignalEvidence
} from "../types/review";

function build_summary(result: BackendAnalysisResult) {
  return result.analysis_context.summary || result.verdict;
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
      label: item.label,
      severity: item.severity
    }));
  }

  return [
    {
      label: "No material risk signals were detected",
      severity: "low"
    }
  ];
}

function build_next_actions(result: BackendAnalysisResult) {
  return result.recommendations.slice(0, 5).map((item) => item.title);
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
  return result.recommendations.slice(0, 5).map((item) => ({
    id: item.id,
    title: item.title,
    detail: item.detail,
    priority: item.priority
  }));
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
  const seen = new Set<string>();
  const items = [...partial_reasons, ...result.analysis_context.limitations];

  return items.filter((item) => {
    const normalized_item = item.trim().toLowerCase();

    if (!normalized_item || seen.has(normalized_item)) {
      return false;
    }

    seen.add(normalized_item);
    return true;
  });

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
    verdict: result.label === "high confidence" ? "mergeable" : result.label === "risky to merge" ? "review needed" : "focused review",
    verdict_text: result.verdict,
    confidence_label: result.label,
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
      patch_excerpt: item.patch_excerpt ?? [],
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

