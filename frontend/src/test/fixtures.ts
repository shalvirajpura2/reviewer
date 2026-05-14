import type { BackendAnalysisResult, BackendMetadata } from "../types/review";
import type { GithubBotPullRequestSummary, GithubBotRepositorySummary } from "../types/github_bot";

export function build_backend_metadata(overrides: Partial<BackendMetadata> = {}): BackendMetadata {
  return {
    owner: "acme",
    repo: "reviewer",
    pull_number: 42,
    repo_full_name: "acme/reviewer",
    title: "Tighten review flow",
    author: "shalv",
    author_avatar_url: "https://example.com/avatar.png",
    base_branch: "main",
    head_branch: "feature/review",
    commits: 2,
    additions: 80,
    deletions: 12,
    changed_files: 3,
    html_url: "https://github.com/acme/reviewer/pull/42",
    created_at: "2026-05-10T10:00:00Z",
    updated_at: "2026-05-11T12:30:00Z",
    ...overrides,
  };
}

export function build_backend_analysis(overrides: Partial<BackendAnalysisResult> = {}): BackendAnalysisResult {
  const metadata = overrides.metadata ?? build_backend_metadata();

  return {
    metadata,
    score: 72,
    label: "high confidence",
    verdict: "Mergeable with routine review",
    review_focus: ["Review backend service boundaries"],
    affected_areas: ["backend", "tests"],
    risk_breakdown: [{ key: "tests", label: "Test coverage", score: 8, summary: "Tests changed with implementation." }],
    triggered_signals: [
      {
        id: "signal:backend",
        label: "Backend service touched",
        severity: "medium",
        evidence: ["backend/app/services/review.py changed"],
        score_impact: -8,
        breakdown_key: "backend",
      },
    ],
    recommendations: [
      { id: "rec:tests", title: "Run backend tests", detail: "Verify the service path still works.", priority: "now" },
    ],
    safeguards: {
      ci_state: "passing",
      summary: "CI checks are passing and tests changed.",
      checks_total: 2,
      checks_passed: 2,
      checks_failed: 0,
      tests_changed: true,
      missing_safeguards: [],
      check_runs: [{ name: "frontend tests", status: "completed", conclusion: "success" }],
    },
    changed_file_groups: [
      {
        label: "Highest risk",
        files: [
          {
            filename: "backend/app/services/review.py",
            status: "modified",
            additions: 30,
            deletions: 4,
            changes: 34,
            patch: "@@ -1 +1 @@",
            blob_url: "https://github.com/acme/reviewer/blob/main/backend/app/services/review.py",
            areas: ["backend"],
            tags: ["backend"],
            is_sensitive: false,
            blast_radius_weight: 3,
            symbol_hints: ["review"],
          },
        ],
      },
    ],
    top_risk_files: [
      {
        filename: "backend/app/services/review.py",
        risk_level: "medium",
        reasons: ["backend service changed"],
        reviewer_hints: ["backend reviewer"],
        patch_excerpt: ["@@ -1 +1 @@", "+new behavior"],
        changes: 34,
        areas: ["backend"],
        is_sensitive: false,
        blob_url: "https://github.com/acme/reviewer/blob/main/backend/app/services/review.py",
      },
    ],
    commits: [{ sha: "abc1234", message: "tighten review flow", author: "shalv" }],
    score_summary: {
      base_score: 80,
      total_penalty: 8,
      total_relief: 0,
      score_version: "test-v1",
    },
    analysis_context: {
      confidence_in_score: "high",
      summary: "Built from GitHub metadata and changed files.",
      limitations: ["Patch structure hints are limited."],
      data_sources: ["GitHub PR metadata"],
      cache_status: "live",
      coverage: {
        files_analyzed: 3,
        total_files: 3,
        patchless_files: 0,
        is_partial: false,
        partial_reasons: [],
      },
    },
    ...overrides,
  };
}

export function build_bot_repository(overrides: Partial<GithubBotRepositorySummary> = {}): GithubBotRepositorySummary {
  return {
    owner: "acme",
    repo: "reviewer",
    full_name: "acme/reviewer",
    installation_id: 123,
    default_branch: "main",
    app_installed: true,
    open_pull_requests: 1,
    settings: {
      manual_review: true,
      automatic_review: false,
      review_new_pushes: false,
    },
    activity: {
      last_review_at: "",
      last_pull_number: 0,
      last_trigger: "",
      last_action: "",
      last_comment_url: null,
    },
    ...overrides,
  };
}

export function build_bot_pull_request(overrides: Partial<GithubBotPullRequestSummary> = {}): GithubBotPullRequestSummary {
  return {
    number: 42,
    title: "Tighten review flow",
    author: "shalv",
    updated_at: "2026-05-11T12:30:00Z",
    html_url: "https://github.com/acme/reviewer/pull/42",
    base_branch: "main",
    head_branch: "feature/review",
    draft: false,
    mode: "manual_review",
    ...overrides,
  };
}
