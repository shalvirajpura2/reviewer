import type { CSSProperties } from "react";
import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useLocation, useSearchParams } from "react-router-dom";

import { SiteFooter } from "../components/site_footer";
import { analyze_pr } from "../lib/api";
import { normalize_pr_url, pr_url_validation_message } from "../lib/pr_url";
import { map_analysis_to_review } from "../lib/review_mapper";
import type {
  ReviewFileGroup,
  ReviewRecommendation,
  ReviewResult,
  ReviewRiskItem,
  ReviewTopRiskFile,
} from "../types/review";

const loading_steps = [
  "Reading pull request metadata",
  "Scanning changed files and commits",
  "Ranking risky files for review",
  "Building your review workspace",
];

function verdict_tone(verdict: ReviewResult["verdict"]) {
  if (verdict === "mergeable") return "safe";
  if (verdict === "focused review") return "caution";
  return "danger";
}

function verdict_copy(result: ReviewResult) {
  return result.verdict_text;
}

function severity_class(severity: ReviewRiskItem["severity"] | ReviewTopRiskFile["risk_level"]) {
  if (severity === "high") return "rp-sev rp-sev-h";
  if (severity === "medium") return "rp-sev rp-sev-m";
  return "rp-sev rp-sev-l";
}

function severity_label(severity: ReviewRiskItem["severity"] | ReviewTopRiskFile["risk_level"]) {
  if (severity === "medium") return "MED";
  return severity.toUpperCase();
}

function confidence_color(score: number) {
  if (score >= 70) return "rgb(var(--green))";
  if (score >= 40) return "rgb(var(--amber))";
  return "rgb(var(--red))";
}

function risk_color(score: number) {
  if (score >= 70) return "rgb(var(--red))";
  if (score >= 40) return "rgb(var(--amber))";
  return "rgb(var(--green))";
}

function group_color(level: ReviewFileGroup["level"]) {
  if (level === "high") return "rgb(var(--red))";
  if (level === "medium") return "rgb(var(--amber))";
  return "rgb(var(--green))";
}

function area_class(area: string, index: number) {
  if (index < 2 || area.toLowerCase().includes("test")) return "rp-area-tag rp-area-tag-hot";
  if (index < 5) return "rp-area-tag rp-area-tag-warn";
  return "rp-area-tag rp-area-tag-ok";
}

function format_date(value?: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

function format_date_time(value?: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function report_badge(result: ReviewResult) {
  if (result.report_status === "fallback") return "saved fallback";
  if (result.report_status === "cached") return "live cache";
  if (result.report_status === "live") return "live analysis";
  return "analysis data";
}

function source_badge_short(result: ReviewResult) {
  if (result.report_status === "fallback") return "saved";
  if (result.report_status === "cached") return "cache";
  if (result.report_status === "live") return "live";
  return "analysis";
}

function coverage_pill_copy(result: ReviewResult) {
  const coverage = result.provenance?.coverage;

  if (!coverage) {
    return "analysis coverage";
  }

  if (coverage.is_partial) {
    return `${coverage.files_analyzed}/${coverage.total_files} files analyzed`;
  }

  return `${coverage.total_files} files analyzed`;
}

function confidence_pill_copy(result: ReviewResult) {
  return result.confidence_label;
}

function risk_level(score: number) {
  if (score >= 70) return { label: "High", class_name: "rp-risk-level rp-risk-level-high" };
  if (score >= 40) return { label: "Watch", class_name: "rp-risk-level rp-risk-level-medium" };
  return { label: "Low", class_name: "rp-risk-level rp-risk-level-low" };
}

function priority_class(priority: ReviewRecommendation["priority"]) {
  if (priority === "now") return "rp-plan-priority rp-plan-priority-now";
  if (priority === "soon") return "rp-plan-priority rp-plan-priority-soon";
  return "rp-plan-priority rp-plan-priority-later";
}

function priority_copy(priority: ReviewRecommendation["priority"]) {
  if (priority === "now") return "Do now";
  if (priority === "soon") return "Do soon";
  return "Nice to have";
}

function animate_dial(element: HTMLElement, target: number, duration = 1100) {
  const start = performance.now();

  function tick(now: number) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = eased * target;

    element.style.setProperty("--rp-progress", `${current.toFixed(1)}%`);

    const number_element = element.querySelector<HTMLElement>(".rp-dial-num");
    if (number_element) {
      number_element.textContent = String(Math.round(current));
    }

    if (progress < 1) {
      requestAnimationFrame(tick);
    }
  }

  requestAnimationFrame(tick);
}

function build_share_url(pr_url: string) {
  if (typeof window === "undefined") {
    return `/result?pr_url=${encodeURIComponent(pr_url)}`;
  }

  return `${window.location.origin}/result?pr_url=${encodeURIComponent(pr_url)}`;
}

function build_share_summary(result: ReviewResult) {
  const first_focus = result.top_risk_files[0]?.filename ?? "No single file highlighted";
  return [
    `${result.repo_name}`,
    `Verdict: ${verdict_copy(result)}`,
    `Confidence: ${result.merge_confidence}/100`,
    `Start with: ${first_focus}`,
    `Source: ${report_badge(result)}`,
  ].join("\n");
}

function build_backend_snapshot(result: ReviewResult) {
  const items = [
    `${result.stats.files_analyzed}/${result.stats.files_changed} files analyzed`,
    `${result.stats.commits} commits reviewed`,
    `${result.stats.additions} additions, ${result.stats.deletions} deletions`,
  ];

  if (result.stats.patchless_files > 0) {
    items.push(`${result.stats.patchless_files} files without patch hunks`);
  }

  return items;
}

function primary_next_step(result: ReviewResult) {
  return result.next_actions.slice(0, 2);
}

async function copy_text(value: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  throw new Error("Clipboard is unavailable in this browser.");
}

function patch_line_class(patch_line: string) {
  if (patch_line.startsWith("@@")) return "rp-patch-line rp-patch-hunk";
  if (patch_line.startsWith("+")) return "rp-patch-line rp-patch-add";
  if (patch_line.startsWith("-")) return "rp-patch-line rp-patch-remove";
  return "rp-patch-line";
}

function FocusPanel({ file, next_actions }: { file: ReviewTopRiskFile; next_actions: string[] }) {
  return (
    <div className="rp-focus-stack">
      <div className="rp-focus-topline">
        <div>
          <div className="rp-focus-filename">{file.filename}</div>
          <div className="rp-focus-lines">{file.changes} lines changed</div>
        </div>
        {file.blob_url ? (
          <a className="rp-focus-link" href={file.blob_url} target="_blank" rel="noreferrer">
            Open on GitHub
          </a>
        ) : null}
      </div>

      <div className="rp-focus-chips">
        <span className={severity_class(file.risk_level)}>{severity_label(file.risk_level)}</span>
        {file.is_sensitive ? <span className="rp-chip rp-chip-sensitive">Sensitive path</span> : null}
        {file.areas.slice(0, 4).map((area) => (
          <span key={area} className="rp-chip">{area}</span>
        ))}
      </div>

      {file.patch_excerpt.length > 0 ? (
        <div className="rp-patch-box" aria-label={`Patch excerpt from ${file.filename}`}>
          <div className="rp-patch-title">Patch evidence</div>
          <pre className="rp-patch-pre">
            {file.patch_excerpt.map((patch_line, index) => (
              <code key={`${file.filename}-${index}-${patch_line}`} className={patch_line_class(patch_line)}>
                {patch_line}
              </code>
            ))}
          </pre>
        </div>
      ) : null}

      <div className="rp-focus-grid">
        <div className="rp-focus-section">
          <div className="rp-focus-section-title">Why this file</div>
          {file.reasons.map((reason, index) => (
            <div key={reason} className="rp-bullet" style={{ "--rp-delay": `${index * 45}ms` } as CSSProperties}>
              {reason}
            </div>
          ))}
        </div>

        <div className="rp-focus-section">
          <div className="rp-focus-section-title">Reviewer hints</div>
          {file.reviewer_hints.map((item, index) => (
            <div
              key={item}
              className="rp-bullet"
              style={{ "--rp-delay": `${(index + file.reasons.length) * 45}ms` } as CSSProperties}
            >
              {item}
            </div>
          ))}
        </div>

        <div className="rp-focus-section">
          <div className="rp-focus-section-title">Check next</div>
          {(next_actions.length > 0 ? next_actions.slice(0, 3) : ["No additional backend review actions were generated."]).map((item, index) => (
            <div
              key={item}
              className="rp-bullet"
              style={{ "--rp-delay": `${(index + file.reasons.length) * 45}ms` } as CSSProperties}
            >
              {item}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ReviewSignalsPanel({ result }: { result: ReviewResult }) {
  return (
    <div className="rp-guide-panel">
      <div className="rp-panel-header">
        <div className="rp-card-label">why attention</div>
        <div className="rp-panel-hint">The strongest signals behind this review</div>
      </div>

      <div className="rp-guide-copy">
        {result.signal_evidence.length > 0
          ? "These signals explain why the backend pushed this PR toward a closer look."
          : "No strong review signals were returned for this PR."}
      </div>

      <div className="rp-signal-stack">
        {result.signal_evidence.slice(0, 3).map((signal) => (
          <div key={signal.label} className="rp-signal-card">
            <div className="rp-signal-head">
              <span className={severity_class(signal.severity)}>{severity_label(signal.severity)}</span>
              <span className="rp-signal-title">{signal.label}</span>
            </div>
            <div className="rp-signal-evidence">
              {signal.evidence.slice(0, 2).map((item) => (
                <div key={item} className="rp-bullet">{item}</div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ReviewNotesPanel({ result }: { result: ReviewResult }) {
  return (
    <div className="rp-guide-panel">
      <div className="rp-panel-header">
        <div className="rp-card-label">review flow</div>
        <div className="rp-panel-hint">The broader pass after the first file</div>
      </div>

      <div className="rp-guide-copy">
        {result.review_plan.length > 0 ? "Follow these backend recommendations after opening the first file." : "The backend did not return extra review steps for this PR."}
      </div>

      <div className="rp-plan-list">
        {result.review_plan.length > 0 ? result.review_plan.slice(0, 3).map((item, index) => (
          <div key={item.id} className="rp-plan-item">
            <div className="rp-plan-head">
              <div className="rp-plan-index">0{index + 1}</div>
              <div className="rp-plan-title-wrap">
                <div className="rp-plan-title">{item.title}</div>
                <div className="rp-plan-detail">{item.detail}</div>
              </div>
              <span className={priority_class(item.priority)}>{priority_copy(item.priority)}</span>
            </div>
          </div>
        )) : <div className="rp-empty-state">No extra backend review notes were generated.</div>}
      </div>
    </div>
  );
}

function ReviewLimitsPanel({ result }: { result: ReviewResult }) {
  return (
    <div className="rp-guide-panel">
      <div className="rp-panel-header">
        <div className="rp-card-label">coverage and limits</div>
        <div className="rp-panel-hint">What this analysis could and could not verify</div>
      </div>

      <div className="rp-certainty-grid">
        <div className="rp-certainty-stat">
          <span className="rp-certainty-stat-value">{result.provenance?.confidence_in_score ?? "unknown"}</span>
          <span className="rp-certainty-stat-label">score confidence</span>
        </div>
        <div className="rp-certainty-stat">
          <span className="rp-certainty-stat-value">{result.stats.files_analyzed}/{result.stats.files_changed}</span>
          <span className="rp-certainty-stat-label">files analyzed</span>
        </div>
        <div className="rp-certainty-stat">
          <span className="rp-certainty-stat-value">{result.stats.patchless_files}</span>
          <span className="rp-certainty-stat-label">patchless files</span>
        </div>
        <div className="rp-certainty-stat">
          <span className="rp-certainty-stat-value">{result.stats.commits}</span>
          <span className="rp-certainty-stat-label">commits analyzed</span>
        </div>
      </div>

      <div className="rp-guide-notes">
        {[
          `Updated on GitHub: ${format_date_time(result.updated_at ?? result.provenance?.source_updated_at)}`,
          ...result.limitations.slice(0, 3),
        ].map((item) => (
          <div key={item} className="rp-prov-item">{item}</div>
        ))}
      </div>
    </div>
  );
}

function DeepPanels({ result }: { result: ReviewResult }) {
  const [open_groups, set_open_groups] = useState<number[]>([]);

  return (
    <div className="rp-deep-panels">
      <div className="rp-dp-grid">
        <div className="rp-dp-panel rp-dp-panel-wide">
          <div className="rp-card-label">risk breakdown</div>
          <div className="rp-section-intro">
            Read this as the shape of review risk: higher values deserve more attention, not necessarily an immediate block.
          </div>

          <div className="rp-risk-breakdown-grid">
            {result.risk_breakdown.map((item, index) => {
              const level = risk_level(item.score);
              return (
                <div key={item.label} className="rp-risk-card" style={{ "--rp-delay": `${index * 60}ms` } as CSSProperties}>
                  <div className="rp-risk-card-head">
                    <div>
                      <div className="rp-risk-name">{item.label}</div>
                      <div className="rp-risk-summary">{item.summary}</div>
                    </div>
                    <div className="rp-risk-score-stack">
                      <span className={level.class_name}>{level.label}</span>
                      <span className="rp-risk-score">{item.score}</span>
                    </div>
                  </div>

                  <div className="rp-risk-meter-shell">
                    <div
                      className="rp-risk-meter-fill"
                      style={{
                        "--target-w": `${item.score}%`,
                        "--rp-delay": `${index * 80}ms`,
                        background: risk_color(item.score),
                      } as CSSProperties}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="rp-dp-panel">
          <div className="rp-card-label">signal evidence</div>
          {result.signal_evidence.map((signal) => (
            <div key={signal.label} className="rp-ev-item">
              <div className="rp-ev-head">
                <span className={severity_class(signal.severity)}>{severity_label(signal.severity)}</span>
                <span className="rp-ev-title">{signal.label}</span>
              </div>
              <div className="rp-ev-lines">
                {signal.evidence.map((item) => (
                  <div key={item} className="rp-ev-line">{item}</div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rp-dp-grid">
        <div className="rp-dp-panel">
          <div className="rp-card-label">recent commits</div>
          {result.score_movement.map((item) => (
            <div key={`${item.sha}-${item.label}`} className="rp-commit-row">
              <span className="rp-commit-sha">{item.sha ?? "-"}</span>
              <span className="rp-commit-msg">{item.label}</span>
            </div>
          ))}
        </div>

        <div className="rp-dp-panel">
          <div className="rp-card-label">changed file groups</div>
          {result.file_groups.map((group, index) => (
            <div key={group.label} className="rp-fg-item">
              <button
                type="button"
                className="rp-fg-header"
                onClick={() =>
                  set_open_groups((current) =>
                    current.includes(index) ? current.filter((item) => item !== index) : [...current, index]
                  )
                }
              >
                <div className="rp-fg-bar" style={{ background: group_color(group.level) }} />
                <span className="rp-fg-name">{group.label}</span>
                <span className="rp-fg-count">{group.files.length} files</span>
                <span className={`rp-fg-chevron ${open_groups.includes(index) ? "rp-open" : ""}`} aria-hidden="true">&gt;</span>
              </button>
              {open_groups.includes(index) ? (
                <div className="rp-fg-files">
                  {group.files.map((file) => (
                    <div key={file} className="rp-fg-file">{file}</div>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </div>

      <div className="rp-sec-grid">
        <div className="rp-sec-panel">
          <div className="rp-card-label">affected areas</div>
          <div className="rp-area-tags">
            {result.changed_areas.map((area, index) => (
              <span key={area} className={area_class(area, index)}>{area}</span>
            ))}
          </div>
          <div className="rp-review-focus">{result.review_focus.join(" ")}</div>
        </div>

        <div className="rp-sec-panel">
          <div className="rp-card-label">analysis provenance</div>
          {[
            `source: ${result.provenance?.cache_status ?? "unknown"}`,
            result.provenance?.cache_status === "fallback" ? "fresh fetch: GitHub unavailable, using saved review" : null,
            `confidence: ${result.provenance?.confidence_in_score ?? "unknown"}`,
            `score version: ${result.provenance?.score_version ?? "unknown"}`,
            `patchless files: ${result.stats.patchless_files}`,
            ...(result.provenance?.data_sources ?? []).map((source) => `data: ${source}`),
          ].filter(Boolean).map((item) => (
            <div key={String(item)} className="rp-prov-item">{item}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function ResultPage() {
  const location = useLocation();
  const [search_params] = useSearchParams();
  const raw_pr_url = search_params.get("pr_url");
  const pr_url = normalize_pr_url(raw_pr_url ?? "");
  const skip_loading_screen = Boolean((location.state as { skip_loading_screen?: boolean } | null)?.skip_loading_screen);

  const [result, set_result] = useState<ReviewResult | null>(null);
  const [is_loading, set_is_loading] = useState(true);
  const [error_message, set_error_message] = useState<string | null>(null);
  const [selected_file, set_selected_file] = useState<string | null>(null);
  const [deep_open, set_deep_open] = useState(false);
  const [is_refreshing, set_is_refreshing] = useState(false);
  const [share_feedback, set_share_feedback] = useState<string | null>(null);

  const dial_ref = useRef<HTMLDivElement | null>(null);
  const dial_timeout_ref = useRef<number>(0);
  const feedback_timeout_ref = useRef<number>(0);
  const request_controller_ref = useRef<AbortController | null>(null);
  const analysis_run_ref = useRef(0);

  async function run_analysis(force_refresh = false) {
    const validation_error = pr_url_validation_message(pr_url);
    if (validation_error) {
      request_controller_ref.current?.abort();
      set_error_message(validation_error);
      set_is_loading(false);
      set_is_refreshing(false);
      return;
    }

    request_controller_ref.current?.abort();

    const request_controller = new AbortController();
    const analysis_run_id = analysis_run_ref.current + 1;
    request_controller_ref.current = request_controller;
    analysis_run_ref.current = analysis_run_id;

    if (force_refresh) {
      set_is_refreshing(true);
    } else {
      set_is_loading(true);
      set_result(null);
    }

    set_error_message(null);

    try {
      const analysis = await analyze_pr(pr_url, force_refresh, request_controller.signal);

      if (analysis_run_id !== analysis_run_ref.current || request_controller.signal.aborted) {
        return;
      }

      const next_result = map_analysis_to_review(analysis);
      set_result(next_result);
      set_selected_file(next_result.top_risk_files[0]?.filename ?? null);

      window.clearTimeout(dial_timeout_ref.current);
      dial_timeout_ref.current = window.setTimeout(() => {
        if (dial_ref.current && analysis_run_id === analysis_run_ref.current) {
          animate_dial(dial_ref.current, next_result.merge_confidence);
        }
      }, 320);
    } catch (error) {
      if (analysis_run_id !== analysis_run_ref.current || request_controller.signal.aborted) {
        return;
      }

      set_error_message(error instanceof Error ? error.message : "Reviewer could not analyze that pull request.");
    } finally {
      if (analysis_run_id !== analysis_run_ref.current) {
        return;
      }

      if (request_controller_ref.current === request_controller) {
        request_controller_ref.current = null;
      }

      set_is_loading(false);
      set_is_refreshing(false);
    }
  }
  useEffect(() => {
    let is_active = true;

    void (async () => {
      if (!is_active) {
        return;
      }
      await run_analysis();
    })();

    return () => {
      is_active = false;
      analysis_run_ref.current += 1;
      request_controller_ref.current?.abort();
      request_controller_ref.current = null;
      window.clearTimeout(dial_timeout_ref.current);
      window.clearTimeout(feedback_timeout_ref.current);
    };
  }, [pr_url]);

  async function handle_copy_summary() {
    if (!result) {
      return;
    }

    try {
      await copy_text(build_share_summary(result));
      set_share_feedback("Review summary copied.");
    } catch (error) {
      set_share_feedback(error instanceof Error ? error.message : "Reviewer could not copy the summary.");
    }
  }

  async function handle_copy_link() {
    try {
      await copy_text(build_share_url(pr_url));
      set_share_feedback("Review link copied.");
    } catch (error) {
      set_share_feedback(error instanceof Error ? error.message : "Reviewer could not copy the link.");
    }
  }

  async function handle_share_review() {
    if (!result) {
      return;
    }

    const share_url = build_share_url(pr_url);
    const share_title = `${result.repo_name} review`;
    const share_text = build_share_summary(result);

    if (navigator.share) {
      try {
        await navigator.share({ title: share_title, text: share_text, url: share_url });
        set_share_feedback("Review shared.");
        return;
      } catch {
      }
    }

    await handle_copy_link();
  }

  useEffect(() => {
    if (!share_feedback) {
      return;
    }

    window.clearTimeout(feedback_timeout_ref.current);
    feedback_timeout_ref.current = window.setTimeout(() => {
      set_share_feedback(null);
    }, 2200);

    return () => {
      window.clearTimeout(dial_timeout_ref.current);
      window.clearTimeout(feedback_timeout_ref.current);
    };
  }, [share_feedback]);

  if (!raw_pr_url) {
    return <Navigate to="/" replace />;
  }

  const created_at = format_date(result?.created_at);
  const updated_at = format_date(result?.updated_at ?? result?.provenance?.source_updated_at);
  const top_files = result?.top_risk_files ?? [];
  const next_actions = result?.next_actions ?? [];
  const focused = top_files.find((file) => file.filename === selected_file) ?? top_files[0] ?? null;
  const backend_snapshot = result ? build_backend_snapshot(result) : [];

  return (
    <div className="rp-page">
      {is_loading ? (
        skip_loading_screen ? (
          <div className="rp-loading rp-loading-quiet rp-anim" style={{ "--rp-delay": "0ms" } as CSSProperties}>
            <div className="rp-loading-title">opening your review</div>
            <div className="rp-loading-copy">Reviewer is finishing the handoff from the preview.</div>
          </div>
        ) : (
          <div className="rp-loading rp-anim" style={{ "--rp-delay": "0ms" } as CSSProperties}>
            <div className="rp-loading-title">building your review</div>
            <div className="rp-loading-copy">Reviewer is pulling the PR context, ranking risk, and preparing the files worth reading first.</div>
            <div className="rp-shimmer-bar" />
            <div className="rp-loading-steps">
              {loading_steps.map((step, index) => (
                <div key={step} className="rp-loading-step" style={{ "--rp-delay": `${index * 90}ms` } as CSSProperties}>
                  <span className="rp-loading-step-index">0{index + 1}</span>
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </div>
        )
      ) : error_message || !result ? (
        <div className="rp-error rp-anim" style={{ "--rp-delay": "0ms" } as CSSProperties}>
          <div className="rp-error-title">analysis unavailable</div>
          <div className="rp-error-msg">{error_message ?? "Reviewer could not analyze that pull request."}</div>
          <Link to="/" className="rp-back-link">Go back home</Link>
        </div>
      ) : (
        <>
          <div className="rp-topbar rp-anim" style={{ "--rp-delay": "0ms" } as CSSProperties}>
            <div className="rp-topbar-left">
              <div className="rp-repo-label">{result.repo_name}</div>
              <div className="rp-pr-title">{result.pr_title}</div>
            </div>
            <div className="rp-topbar-pills">
              <div className="rp-pill">
                <span className="rp-pill-dot" />
                {report_badge(result)}
              </div>
              <div className="rp-pill">Opened {created_at}</div>
              <div className="rp-pill">Updated {updated_at}</div>
              <div className="rp-pill">{coverage_pill_copy(result)}</div>
              <div className="rp-pill">{confidence_pill_copy(result)}</div>
              <a className="rp-pill rp-pill-link" href={result.pr_url} target="_blank" rel="noreferrer">
                Open on GitHub
              </a>
            </div>
          </div>

          <div className="rp-hero rp-anim" style={{ "--rp-delay": "60ms" } as CSSProperties}>
            <div className="rp-hero-copy">
              <div className="rp-verdict-eyebrow">decision</div>
              <div className={`rp-verdict-text ${verdict_tone(result.verdict)}`}>{verdict_copy(result)}</div>
              <div className="rp-verdict-summary">{result.summary}</div>
              <div className="rp-share-row">
                <button type="button" className="rp-secondary-btn" onClick={() => void handle_copy_summary()}>
                  Copy summary
                </button>
                <button type="button" className="rp-secondary-btn" onClick={() => void handle_copy_link()}>
                  Copy link
                </button>
                <button type="button" className="rp-secondary-btn" onClick={() => void handle_share_review()}>
                  Share review
                </button>
                <button type="button" className="rp-secondary-btn rp-secondary-btn-strong" onClick={() => void run_analysis(true)} disabled={is_refreshing}>
                  {is_refreshing ? "Refreshing..." : "Fetch fresh live analysis"}
                </button>
              </div>
              {share_feedback ? <div className="rp-share-feedback">{share_feedback}</div> : null}
            </div>

            <div className="rp-hero-rail">
              <div className="rp-score-card">
                <div
                  ref={dial_ref}
                  className="rp-dial-ring"
                  style={{
                    "--rp-progress": "0%",
                    "--rp-tone": confidence_color(result.merge_confidence),
                  } as CSSProperties}
                >
                  <div className="rp-dial-inner">
                    <div className="rp-dial-num">0</div>
                    <div className="rp-dial-label">confidence</div>
                  </div>
                </div>
              </div>

              <div className="rp-mini-stats rp-mini-stats-stack">
                {backend_snapshot.map((item) => (
                  <div key={item} className="rp-mini-stat rp-mini-stat-wide">
                    <span className="rp-mini-stat-val">{item}</span>
                  </div>
                ))}
                <div className="rp-mini-stat rp-mini-stat-source">
                  <span className="rp-mini-stat-val">{source_badge_short(result)}</span>
                  <span className="rp-mini-stat-key">source</span>
                </div>
              </div>
            </div>
          </div>

          <div className="rp-summary-grid rp-anim" style={{ "--rp-delay": "100ms" } as CSSProperties}>
            <ReviewSignalsPanel result={result} />
            <div className="rp-guide-panel">
              <div className="rp-panel-header">
                <div className="rp-card-label">check these first</div>
                <div className="rp-panel-hint">The fastest way into the PR</div>
              </div>
              <div className="rp-priority-list">
                {top_files.slice(0, 3).map((file) => (
                  <button
                    key={file.filename}
                    type="button"
                    className={`rp-priority-item ${focused?.filename === file.filename ? "rp-active" : ""}`}
                    onClick={() => set_selected_file(file.filename)}
                  >
                    <span className="rp-priority-name">{file.filename}</span>
                    <span className="rp-priority-chevron">&gt;</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="rp-guide-panel">
              <div className="rp-panel-header">
                <div className="rp-card-label">recommended next step</div>
                <div className="rp-panel-hint">The first backend actions to take</div>
              </div>
              <div className="rp-priority-list">
                {primary_next_step(result).length > 0 ? primary_next_step(result).map((item) => (
                  <div key={item} className="rp-bullet">{item}</div>
                )) : <div className="rp-empty-state">No immediate backend next steps were generated.</div>}
              </div>
            </div>
          </div>

          <div className="rp-sequence-shell rp-anim" style={{ "--rp-delay": "120ms" } as CSSProperties}>
            <div className="rp-sequence-intro">
              <div className="rp-card-label">start here</div>
              <div className="rp-sequence-title">Open one file first, then decide if the PR needs a wider pass</div>
              <div className="rp-sequence-copy">
                The queue is already ranked by the backend. You do not need to scan the whole PR before making progress.
              </div>
            </div>

            <div className="rp-main-grid">
              <div className="rp-queue-panel">
                <div className="rp-panel-header">
                  <div className="rp-card-label">review queue</div>
                  <div className="rp-panel-hint">Click a file to inspect it in detail</div>
                </div>
                {top_files.length > 0 ? (
                  top_files.map((file, index) => (
                    <button
                      key={file.filename}
                      type="button"
                      className={`rp-file-row ${focused?.filename === file.filename ? "rp-active" : ""}`}
                      onClick={() => set_selected_file(file.filename)}
                    >
                      <span className="rp-file-rank">{String(index + 1).padStart(2, "0")}</span>
                      <span>
                        <span className="rp-file-name">{file.filename}</span>
                        <span className="rp-file-reason">{file.reasons[0] ?? "Review this file first."}</span>
                      </span>
                      <span className={severity_class(file.risk_level)}>{severity_label(file.risk_level)}</span>
                    </button>
                  ))
                ) : (
                  <div className="rp-empty-state">No prioritized files identified.</div>
                )}
              </div>

              <div className="rp-focus-panel">
                <div className="rp-panel-header">
                  <div className="rp-card-label">selected file</div>
                  <div className="rp-panel-hint">Context updates when you switch files</div>
                </div>
                {focused ? <FocusPanel key={focused.filename} file={focused} next_actions={next_actions} /> : <div className="rp-empty-state">No prioritized file available.</div>}
              </div>
            </div>
          </div>

          <div className="rp-support-grid rp-anim" style={{ "--rp-delay": "150ms" } as CSSProperties}>
            <ReviewNotesPanel result={result} />
            <ReviewLimitsPanel result={result} />
          </div>

          <button
            type="button"
            className={`rp-deep-toggle rp-anim ${deep_open ? "rp-open" : ""}`}
            style={{ "--rp-delay": "240ms" } as CSSProperties}
            onClick={() => set_deep_open((current) => !current)}
          >
            <span className="rp-deep-toggle-copy">See deeper evidence</span>
            <span className="rp-toggle-icon">+</span>
          </button>

          {deep_open ? <DeepPanels result={result} /> : null}
        </>
      )}

      <SiteFooter />
    </div>
  );
}
