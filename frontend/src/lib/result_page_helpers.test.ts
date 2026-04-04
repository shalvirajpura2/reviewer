import { describe, expect, it } from "vitest";

import { coverage_pill_copy, patch_line_class, report_badge, source_badge_short } from "./result_page_helpers";
import type { ReviewResult } from "../types/review";


function build_result(overrides: Partial<ReviewResult> = {}): ReviewResult {
  return {
    pr_title: "Review API contract",
    repo_name: "acme/reviewer #7",
    pr_url: "https://github.com/acme/reviewer/pull/7",
    report_status: "live",
    merge_confidence: 82,
    verdict: "focused review",
    summary: "Check the risky files first.",
    verdict_text: "mergeable with focused review",
    confidence_label: "moderate confidence",
    top_risks: [],
    next_actions: [],
    changed_areas: [],
    limitations: [],
    stats: {
      files_changed: 4,
      files_analyzed: 4,
      additions: 24,
      deletions: 8,
      commits: 2,
      patchless_files: 0,
    },
    risk_breakdown: [],
    score_movement: [],
    file_groups: [],
    review_focus: [],
    signal_evidence: [],
    review_plan: [],
    top_risk_files: [],
    provenance: {
      cache_status: "live",
      confidence_in_score: "medium",
      data_sources: [],
      score_version: "v1.2-deterministic",
      coverage: {
        files_analyzed: 4,
        total_files: 4,
        patchless_files: 0,
        is_partial: false,
        partial_reasons: [],
      },
    },
    ...overrides,
  };
}


describe("result_page_helpers", () => {
  it("builds cache and coverage labels", () => {
    expect(report_badge(build_result({ report_status: "fallback" }))).toBe("saved fallback");
    expect(source_badge_short(build_result({ report_status: "cached" }))).toBe("cache");
    expect(coverage_pill_copy(build_result())).toBe("4 files analyzed");
    expect(
      coverage_pill_copy(
        build_result({
          provenance: {
            cache_status: "cached",
            confidence_in_score: "low",
            data_sources: [],
            score_version: "v1.2-deterministic",
            coverage: {
              files_analyzed: 2,
              total_files: 5,
              patchless_files: 1,
              is_partial: true,
              partial_reasons: [],
            },
          },
        })
      )
    ).toBe("2/5 files analyzed");
  });

  it("maps patch lines to styles", () => {
    expect(patch_line_class("@@ -1,2 +1,3 @@")).toBe("rp-patch-line rp-patch-hunk");
    expect(patch_line_class("+const value = 1")).toBe("rp-patch-line rp-patch-add");
    expect(patch_line_class("-const value = 0")).toBe("rp-patch-line rp-patch-remove");
    expect(patch_line_class("const value = 1")).toBe("rp-patch-line");
  });
});