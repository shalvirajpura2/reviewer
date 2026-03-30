import type { CSSProperties } from "react";
import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";

import { SiteFooter } from "../components/site_footer";
import { analyze_pr } from "../lib/api";
import { normalize_pr_url, pr_url_validation_message } from "../lib/pr_url";
import { map_analysis_to_review } from "../lib/review_mapper";
import type {
  ReviewFileGroup,
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

function verdict_copy(verdict: ReviewResult["verdict"]) {
  if (verdict === "mergeable") return "Safe to merge";
  if (verdict === "focused review") return "Merge with focused review";
  return "Needs deeper review";
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

function report_badge(result: ReviewResult) {
  if (result.report_status === "cached") return "live cache";
  if (result.report_status === "live") return "live analysis";
  return "analysis data";
}

function source_badge_short(result: ReviewResult) {
  if (result.report_status === "cached") return "cache";
  if (result.report_status === "live") return "live";
  return "analysis";
}

function risk_level(score: number) {
  if (score >= 70) return { label: "High", className: "rp-risk-level rp-risk-level-high" };
  if (score >= 40) return { label: "Watch", className: "rp-risk-level rp-risk-level-medium" };
  return { label: "Low", className: "rp-risk-level rp-risk-level-low" };
}

function file_summary(file: ReviewTopRiskFile) {
  const area = file.areas[0] ?? "review-relevant";

  if (file.is_sensitive) {
    return `This file sits in a sensitive area and carries ${file.changes} changed lines across ${area} code.`;
  }

  if (file.risk_level === "high") {
    return `This file has the highest risk signature in the pull request and carries ${file.changes} changed lines.`;
  }

  return "This file stands out because its diff shape and affected areas make it worth reviewing early.";
}

function reviewer_checks(file: ReviewTopRiskFile, next_actions: string[]) {
  const checks = new Set<string>();

  if (file.is_sensitive) {
    checks.add("Verify downstream behavior and shared call sites still behave as expected.");
  }

  if (file.areas.some((area) => area.toLowerCase().includes("test"))) {
    checks.add("Confirm the updated tests still cover the logic that changed.");
  }

  if (file.reasons.some((reason) => reason.toLowerCase().includes("shared"))) {
    checks.add("Check whether shared paths now affect more surfaces than intended.");
  }

  if (file.reasons.some((reason) => reason.toLowerCase().includes("logic"))) {
    checks.add("Read the changed branches carefully and validate happy path and edge cases.");
  }

  next_actions.slice(0, 2).forEach((action) => {
    checks.add(action.endsWith(".") ? action : `${action}.`);
  });

  if (checks.size === 0) {
    checks.add("Review the changed logic and confirm surrounding behavior still holds.");
  }

  return Array.from(checks).slice(0, 4);
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

function FocusPanel({ file, next_actions }: { file: ReviewTopRiskFile; next_actions: string[] }) {
  const checks = reviewer_checks(file, next_actions);

  return (
    <>
      <div className="rp-focus-filename">{file.filename}</div>
      <div className="rp-focus-lines">{file.changes} lines changed</div>

      <div className="rp-focus-chips">
        <span className={severity_class(file.risk_level)}>{severity_label(file.risk_level)}</span>
        {file.is_sensitive ? <span className="rp-chip rp-chip-sensitive">Sensitive path</span> : null}
        {file.areas.slice(0, 4).map((area) => (
          <span key={area} className="rp-chip">{area}</span>
        ))}
      </div>

      <div className="rp-focus-section">
        <div className="rp-focus-section-title">Why prioritized</div>
        <div className="rp-focus-text">{file_summary(file)}</div>
      </div>

      <div className="rp-focus-section">
        <div className="rp-focus-section-title">Signals</div>
        {file.reasons.map((reason, index) => (
          <div key={reason} className="rp-bullet" style={{ "--rp-delay": `${index * 45}ms` } as CSSProperties}>
            {reason}
          </div>
        ))}
      </div>

      <div className="rp-focus-section">
        <div className="rp-focus-section-title">Reviewer should verify</div>
        {checks.map((item, index) => (
          <div
            key={item}
            className="rp-bullet"
            style={{ "--rp-delay": `${(index + file.reasons.length) * 45}ms` } as CSSProperties}
          >
            {item}
          </div>
        ))}
      </div>
    </>
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
            Read this as the shape of review risk: higher values need more reviewer attention, not necessarily merge blocking.
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
                      <span className={level.className}>{level.label}</span>
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
            `confidence: ${result.provenance?.confidence_in_score ?? "unknown"}`,
            `score version: ${result.provenance?.score_version ?? "unknown"}`,
            ...(result.provenance?.data_sources ?? []).map((source) => `data: ${source}`),
          ].map((item) => (
            <div key={item} className="rp-prov-item">{item}</div>
          ))}
        </div>

        <div className="rp-sec-panel">
          <div className="rp-card-label">limitations</div>
          {result.limitations.map((item) => (
            <div key={item} className="rp-prov-item">{item}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function ResultPage() {
  const [search_params] = useSearchParams();
  const raw_pr_url = search_params.get("pr_url");
  const pr_url = normalize_pr_url(raw_pr_url ?? "");

  const [result, set_result] = useState<ReviewResult | null>(null);
  const [is_loading, set_is_loading] = useState(true);
  const [error_message, set_error_message] = useState<string | null>(null);
  const [selected_file, set_selected_file] = useState<string | null>(null);
  const [deep_open, set_deep_open] = useState(false);

  const dial_ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let active = true;
    let timeout = 0;

    async function load() {
      set_is_loading(true);
      set_error_message(null);
      set_result(null);

      const validation_error = pr_url_validation_message(pr_url);
      if (validation_error) {
        if (!active) return;
        set_error_message(validation_error);
        set_is_loading(false);
        return;
      }

      try {
        const analysis = await analyze_pr(pr_url);
        if (!active) return;

        const next_result = map_analysis_to_review(analysis);
        set_result(next_result);
        set_selected_file(next_result.top_risk_files[0]?.filename ?? null);

        timeout = window.setTimeout(() => {
          if (dial_ref.current) {
            animate_dial(dial_ref.current, next_result.merge_confidence);
          }
        }, 320);
      } catch (error) {
        if (!active) return;
        set_error_message(error instanceof Error ? error.message : "Reviewer could not analyze that pull request.");
      } finally {
        if (active) {
          set_is_loading(false);
        }
      }
    }

    void load();

    return () => {
      active = false;
      window.clearTimeout(timeout);
    };
  }, [pr_url]);

  if (!raw_pr_url) {
    return <Navigate to="/" replace />;
  }

  const created_at = format_date(result?.created_at);
  const top_files = result?.top_risk_files ?? [];
  const next_actions = result?.next_actions ?? [];
  const focused = top_files.find((file) => file.filename === selected_file) ?? top_files[0] ?? null;

  return (
    <div className="rp-page">
      {is_loading ? (
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
              <div className="rp-pill">{created_at}</div>
              <a className="rp-pill rp-pill-link" href={result.pr_url} target="_blank" rel="noreferrer">
                Open on GitHub
              </a>
            </div>
          </div>

          <div className="rp-hero rp-anim" style={{ "--rp-delay": "60ms" } as CSSProperties}>
            <div className="rp-hero-copy">
              <div className="rp-verdict-eyebrow">decision</div>
              <div className={`rp-verdict-text ${verdict_tone(result.verdict)}`}>{verdict_copy(result.verdict)}</div>
              <div className="rp-verdict-summary">{result.summary}</div>
            </div>

            <div className="rp-hero-dial">
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

              <div className="rp-mini-stats">
                <div className="rp-mini-stat">
                  <span className="rp-mini-stat-val">{result.stats.files_changed}</span>
                  <span className="rp-mini-stat-key">files</span>
                </div>
                <div className="rp-mini-stat">
                  <span className="rp-mini-stat-val">{result.stats.commits}</span>
                  <span className="rp-mini-stat-key">commits</span>
                </div>
                <div className="rp-mini-stat rp-mini-stat-source">
                  <span className="rp-mini-stat-val">{source_badge_short(result)}</span>
                  <span className="rp-mini-stat-key">source</span>
                </div>
              </div>
            </div>
          </div>

          <div className="rp-action-strip rp-anim" style={{ "--rp-delay": "120ms" } as CSSProperties}>
            <div className="rp-action-card">
              <div className="rp-card-label">why attention</div>
              {result.top_risks.slice(0, 3).map((risk) => (
                <div key={risk.label} className="rp-risk-row">
                  <span className={severity_class(risk.severity)}>{severity_label(risk.severity)}</span>
                  <span>{risk.label}</span>
                </div>
              ))}
            </div>

            <div className="rp-action-card">
              <div className="rp-card-label">check these first</div>
              {top_files.slice(0, 3).map((file) => (
                <button key={file.filename} type="button" className="rp-file-btn" onClick={() => set_selected_file(file.filename)}>
                  <span>{file.filename}</span>
                  <span className="rp-file-btn-arrow">&gt;</span>
                </button>
              ))}
            </div>

            <div className="rp-action-card rp-action-card-highlight">
              <div className="rp-card-label">recommended next step</div>
              {(next_actions.length > 0 ? next_actions.slice(0, 2) : ["Run one focused reviewer pass before merge"]).map((item) => (
                <div key={item} className="rp-next-item">{item}</div>
              ))}
            </div>
          </div>

          <div className="rp-main-grid rp-anim" style={{ "--rp-delay": "180ms" } as CSSProperties}>
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

          <button
            type="button"
            className={`rp-deep-toggle rp-anim ${deep_open ? "rp-open" : ""}`}
            style={{ "--rp-delay": "240ms" } as CSSProperties}
            onClick={() => set_deep_open((current) => !current)}
          >
            <span className="rp-deep-toggle-copy">View full analysis</span>
            <span className="rp-toggle-icon">+</span>
          </button>

          {deep_open ? <DeepPanels result={result} /> : null}
        </>
      )}

      <SiteFooter />
    </div>
  );
}
