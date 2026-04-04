import { describe, expect, it } from "vitest";

import { map_analysis_to_review } from "./review_mapper";
import type { BackendAnalysisResult } from "../types/review";

function build_backend_result(overrides: Partial<BackendAnalysisResult> = {}): BackendAnalysisResult {
  return {
    metadata: {
      owner: "acme",
      repo: "reviewer",
      pull_number: 12,
      repo_full_name: "acme/reviewer",
      title: "Keep frontend aligned with backend",
      author: "shalv",
      author_avatar_url: "https://example.com/avatar.png",
      base_branch: "main",
      head_branch: "feat/alignment",
      commits: 2,
      additions: 44,
      deletions: 8,
      changed_files: 3,
      html_url: "https://github.com/acme/reviewer/pull/12",
      created_at: "2026-03-31T10:00:00Z",
      updated_at: "2026-03-31T11:00:00Z",
    },
    score: 74,
    label: "moderate confidence",
    verdict: "mergeable with focused review",
    review_focus: ["Sensitive paths changed"],
    affected_areas: ["shared-core", "backend"],
    risk_breakdown: [
      { key: "sensitive_code_risk", label: "Sensitive code risk", score: 10, summary: "Sensitive code risk is present but contained." },
      { key: "dependency_risk", label: "Dependency risk", score: 0, summary: "Dependency risk is limited in this pull request." },
    ],
    triggered_signals: [
      {
        id: "sensitive_paths_changed",
        label: "Sensitive paths changed",
        severity: "medium",
        evidence: ["backend/app/services/github_client.py"],
        score_impact: -10,
        breakdown_key: "sensitive_code_risk",
      },
    ],
    recommendations: [
      {
        id: "review_sensitive_logic",
        title: "Review sensitive logic carefully",
        detail: "Validate auth, permissions, payments, or data-layer behavior with edge cases in mind.",
        priority: "now",
      },
    ],
    changed_file_groups: [
      {
        label: "Shared / Core",
        files: [
          {
            filename: "backend/app/services/github_client.py",
            status: "modified",
            additions: 10,
            deletions: 2,
            changes: 12,
            patch: "import httpx",
            blob_url: "https://github.com/acme/reviewer/blob/main/backend/app/services/github_client.py",
            previous_filename: undefined,
            areas: ["backend", "shared_core", "sensitive"],
            tags: ["backend", "shared-core", "sensitive"],
            is_sensitive: true,
            blast_radius_weight: 4,
            symbol_hints: ["imports_changed"],
          },
        ],
      },
    ],
    top_risk_files: [
      {
        filename: "backend/app/services/github_client.py",
        risk_level: "high",
        reasons: ["sensitive execution path touched", "shared or reused code touched"],
        reviewer_hints: ["backend reviewer", "core maintainer"],
        patch_excerpt: ["@@ -1,2 +1,3 @@", "-import httpx", "+import httpx"],
        changes: 12,
        areas: ["backend", "shared_core", "sensitive"],
        is_sensitive: true,
        blob_url: "https://github.com/acme/reviewer/blob/main/backend/app/services/github_client.py",
      },
    ],
    commits: [
      {
        sha: "abc1234",
        message: "tighten review mapper",
        author: "shalv",
        authored_at: "2026-03-31T10:30:00Z",
        html_url: "https://github.com/acme/reviewer/commit/abc1234",
      },
    ],
    score_summary: {
      base_score: 100,
      total_penalty: 26,
      total_relief: 0,
      score_version: "v1.2-deterministic",
    },
    analysis_context: {
      confidence_in_score: "medium",
      summary: "Built from GitHub metadata, 3 of 3 changed files analyzed, 2 commits, rule-based risk scoring, and patch-level structure hints. Patch coverage note: full patch hints where available. Response source: live.",
      limitations: [
        "This analysis does not inspect CI status or deployment health.",
        "Patch structure hints are based on changed hunks, not full repository semantics.",
      ],
      data_sources: ["GitHub PR metadata", "GitHub changed files", "GitHub commits", "rule-based risk engine"],
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

describe("map_analysis_to_review", () => {
  it("keeps backend verdict and summary intact", () => {
    const mapped = map_analysis_to_review(build_backend_result());

    expect(mapped.verdict_text).toBe("mergeable with focused review");
    expect(mapped.summary).toContain("Built from GitHub metadata");
    expect(mapped.next_actions).toEqual(["Review sensitive logic carefully"]);
    expect(mapped.top_risk_files[0]?.filename).toBe("backend/app/services/github_client.py");
    expect(mapped.top_risk_files[0]?.reviewer_hints).toEqual(["backend reviewer", "core maintainer"]);
    expect(mapped.top_risk_files[0]?.patch_excerpt).toEqual(["@@ -1,2 +1,3 @@", "-import httpx", "+import httpx"]);
  });

  it("dedupes limitations while keeping partial analysis reasons", () => {
    const mapped = map_analysis_to_review(
      build_backend_result({
        analysis_context: {
          confidence_in_score: "low",
          summary: "Partial analysis is all that was available.",
          limitations: [
            "Patch structure hints are based on changed hunks, not full repository semantics.",
            "Patch structure hints are based on changed hunks, not full repository semantics.",
          ],
          data_sources: ["GitHub PR metadata"],
          cache_status: "fallback",
          coverage: {
            files_analyzed: 2,
            total_files: 3,
            patchless_files: 1,
            is_partial: true,
            partial_reasons: [
              "GitHub did not provide patch hunks for 1 changed files, so structure hints are limited there.",
              "GitHub did not provide patch hunks for 1 changed files, so structure hints are limited there.",
            ],
          },
        },
      })
    );

    expect(mapped.limitations).toEqual([
      "GitHub did not provide patch hunks for 1 changed files, so structure hints are limited there.",
      "Patch structure hints are based on changed hunks, not full repository semantics.",
    ]);
    expect(mapped.report_status).toBe("fallback");
  });
});
