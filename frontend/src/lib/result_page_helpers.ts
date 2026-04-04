import type { ReviewResult } from "../types/review";


export function report_badge(result: ReviewResult) {
  if (result.report_status === "fallback") return "saved fallback";
  if (result.report_status === "cached") return "live cache";
  if (result.report_status === "live") return "live analysis";
  return "analysis data";
}


export function source_badge_short(result: ReviewResult) {
  if (result.report_status === "fallback") return "saved";
  if (result.report_status === "cached") return "cache";
  if (result.report_status === "live") return "live";
  return "analysis";
}


export function coverage_pill_copy(result: ReviewResult) {
  const coverage = result.provenance?.coverage;

  if (!coverage) {
    return "analysis coverage";
  }

  if (coverage.is_partial) {
    return `${coverage.files_analyzed}/${coverage.total_files} files analyzed`;
  }

  return `${coverage.total_files} files analyzed`;
}


export function patch_line_class(patch_line: string) {
  if (patch_line.startsWith("@@")) return "rp-patch-line rp-patch-hunk";
  if (patch_line.startsWith("+")) return "rp-patch-line rp-patch-add";
  if (patch_line.startsWith("-")) return "rp-patch-line rp-patch-remove";
  return "rp-patch-line";
}