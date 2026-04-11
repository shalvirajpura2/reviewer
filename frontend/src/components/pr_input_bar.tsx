import type { CSSProperties } from "react";
import { AlertCircle, ArrowRight, ExternalLink, GitBranch, Link2, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";

import { preview_pr, type PrPreview } from "../lib/api";
import { normalize_pr_url, pr_url_validation_message, sample_pr_url } from "../lib/pr_url";

type PrInputBarProps = {
  mode?: "hero" | "compact";
};

const review_loading_steps = [
  "Checking pull request context",
  "Reading changed files and commits",
  "Opening your review workspace",
];

function format_date(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Recently updated";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

function get_focusable_elements(container: HTMLElement | null): HTMLElement[] {
  if (!container) {
    return [];
  }

  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    ),
  ).filter((element) => !element.hasAttribute("hidden") && !element.getAttribute("aria-hidden"));
}

export function PrInputBar({ mode = "hero" }: PrInputBarProps) {
  const navigate = useNavigate();
  const preview_title_id = useId();
  const preview_description_id = useId();
  const [pr_url, set_pr_url] = useState("");
  const [is_loading, set_is_loading] = useState(false);
  const [is_starting_review, set_is_starting_review] = useState(false);
  const [validation_message, set_validation_message] = useState<string | null>(null);
  const [preview, set_preview] = useState<PrPreview | null>(null);
  const [preview_error, set_preview_error] = useState<string | null>(null);
  const [is_preview_open, set_is_preview_open] = useState(false);
  const is_compact = mode === "compact";
  const input_ref = useRef<HTMLInputElement | null>(null);
  const dialog_ref = useRef<HTMLDivElement | null>(null);
  const close_button_ref = useRef<HTMLButtonElement | null>(null);
  const previous_active_element_ref = useRef<HTMLElement | null>(null);
  const is_starting_review_ref = useRef(false);

  useEffect(() => {
    is_starting_review_ref.current = is_starting_review;
  }, [is_starting_review]);

  useEffect(() => {
    if (!is_preview_open) {
      document.body.style.removeProperty("overflow");
      return;
    }

    const previous_overflow = document.body.style.overflow;
    previous_active_element_ref.current = document.activeElement instanceof HTMLElement ? document.activeElement : input_ref.current;
    document.body.style.overflow = "hidden";

    function handle_key_down(event: KeyboardEvent) {
      if (event.key === "Escape" && !is_starting_review_ref.current) {
        set_is_preview_open(false);
        return;
      }

      if (event.key !== "Tab") {
        return;
      }

      const focusable_elements = get_focusable_elements(dialog_ref.current);
      if (focusable_elements.length === 0) {
        event.preventDefault();
        dialog_ref.current?.focus();
        return;
      }

      const first_element = focusable_elements[0];
      const last_element = focusable_elements[focusable_elements.length - 1];
      const active_element = document.activeElement;

      if (event.shiftKey && active_element === first_element) {
        event.preventDefault();
        last_element.focus();
      } else if (!event.shiftKey && active_element === last_element) {
        event.preventDefault();
        first_element.focus();
      }
    }

    window.addEventListener("keydown", handle_key_down);
    return () => {
      document.body.style.overflow = previous_overflow;
      window.removeEventListener("keydown", handle_key_down);
      previous_active_element_ref.current?.focus();
    };
  }, [is_preview_open]);

  useEffect(() => {
    if (!is_preview_open) {
      return;
    }

    const focus_target = is_starting_review ? dialog_ref.current : close_button_ref.current ?? dialog_ref.current;
    const focus_timeout = window.setTimeout(() => {
      focus_target?.focus();
    }, 0);

    return () => {
      window.clearTimeout(focus_timeout);
    };
  }, [is_preview_open, is_starting_review]);

  function set_validation(message: string | null) {
    set_validation_message(message);
    if (message) {
      set_preview(null);
      set_preview_error(null);
      set_is_preview_open(false);
    }
  }

  async function submit_pr() {
    const normalized_pr_url = normalize_pr_url(pr_url);
    const next_validation_message = pr_url_validation_message(normalized_pr_url);

    set_validation(next_validation_message);

    if (next_validation_message || is_loading || is_starting_review) {
      return;
    }

    set_is_loading(true);
    set_preview_error(null);

    try {
      const next_preview = await preview_pr(normalized_pr_url);
      set_preview(next_preview);
      set_is_preview_open(true);
    } catch (error) {
      set_preview(null);
      set_is_preview_open(false);
      set_preview_error(error instanceof Error ? error.message : "Reviewer could not load that pull request preview.");
    } finally {
      set_is_loading(false);
    }
  }

  function close_preview() {
    if (is_starting_review) {
      return;
    }

    set_is_preview_open(false);
  }

  function continue_to_review() {
    const normalized_pr_url = normalize_pr_url(pr_url);
    set_is_starting_review(true);

    window.setTimeout(() => {
      navigate(`/result?pr_url=${encodeURIComponent(normalized_pr_url)}`, {
        state: { skip_loading_screen: true },
      });
    }, 1050);
  }

  const preview_metadata = preview?.metadata;

  return (
    <>
      <div className={`input-zone ${is_compact ? "input-zone-compact" : ""}`}>
        {is_compact ? <div className="input-label">// Analyze a public pull request</div> : null}
        <div className="input-frame">
          <div className="input-prefix">
            <Link2 className="h-4 w-4 shrink-0" />
          </div>
          <input
            ref={input_ref}
            value={pr_url}
            onChange={(event) => {
              const next_value = event.target.value;
              set_pr_url(next_value);
              set_preview(null);
              set_preview_error(null);
              set_is_preview_open(false);
              if (validation_message) {
                set_validation(pr_url_validation_message(next_value));
              }
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                void submit_pr();
              }
            }}
            placeholder="https://github.com/owner/repo/pull/123"
            className="pr-url"
          />
          <button onClick={() => void submit_pr()} disabled={is_loading || is_starting_review} className="analyze-btn">
            {is_loading ? "Checking" : "Preview"}
            <ArrowRight className="ml-2 inline h-4 w-4" />
          </button>
        </div>
        {validation_message ? (
          <div className="input-validation">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <span>{validation_message}</span>
          </div>
        ) : null}
        {preview_error ? (
          <div className="input-validation">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <span>{preview_error}</span>
          </div>
        ) : null}
        <div className="input-hint">
          <span className="input-hint-item input-hint-item-primary">Works with live PRs</span>
          <span className="input-hint-item">No signup</span>
          <span className="input-hint-item">Preview first</span>
        </div>
        <div className="input-sample-row">
          <span className="input-sample-label">Need a quick demo?</span>
          <button
            type="button"
            className="input-sample-link"
            onClick={() => {
              set_pr_url(sample_pr_url);
              set_validation_message(null);
              set_preview(null);
              set_preview_error(null);
              set_is_preview_open(false);
            }}
          >
            Load the sample PR
          </button>
        </div>
      </div>

      {is_preview_open && preview_metadata ? createPortal(
        <div
          className="pr-preview-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby={preview_title_id}
          aria-describedby={preview_description_id}
        >
          <button type="button" className="pr-preview-backdrop" aria-label="Close preview" onClick={close_preview} />
          <div ref={dialog_ref} className="pr-preview-dialog" tabIndex={-1}>
            {!is_starting_review ? (
              <>
                <div className="pr-preview-dialog-top">
                  <div className="pr-preview-heading">
                    <div className="pr-preview-eyebrow">Pull request preview</div>
                    <div id={preview_title_id} className="pr-preview-title">{preview_metadata.title}</div>
                    <div className="pr-preview-repo">{preview_metadata.repo_full_name} #{preview_metadata.pull_number}</div>
                  </div>
                  <button ref={close_button_ref} type="button" className="pr-preview-close" onClick={close_preview} aria-label="Close preview">
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <div id={preview_description_id} className="pr-preview-copy">
                  This looks like the right pull request. Start the review when you are ready.
                </div>
                <div className="pr-preview-stats">
                  <div className="pr-preview-stat">
                    <span className="pr-preview-stat-value">@{preview_metadata.author}</span>
                    <span className="pr-preview-stat-label">author</span>
                  </div>
                  <div className="pr-preview-stat">
                    <span className="pr-preview-stat-value">{preview_metadata.changed_files}</span>
                    <span className="pr-preview-stat-label">files changed</span>
                  </div>
                  <div className="pr-preview-stat">
                    <span className="pr-preview-stat-value">{preview_metadata.commits}</span>
                    <span className="pr-preview-stat-label">commits</span>
                  </div>
                  <div className="pr-preview-stat">
                    <span className="pr-preview-stat-value">{format_date(preview_metadata.updated_at)}</span>
                    <span className="pr-preview-stat-label">updated</span>
                  </div>
                </div>
                <div className="pr-preview-branches">
                  <span className="pr-preview-branch"><GitBranch className="h-3.5 w-3.5" /> {preview_metadata.base_branch}</span>
                  <span className="pr-preview-branch"><ArrowRight className="h-3.5 w-3.5" /> {preview_metadata.head_branch}</span>
                </div>
                <div className="pr-preview-actions">
                  <button type="button" className="pr-preview-btn" onClick={close_preview}>
                    Change URL
                  </button>
                  <button type="button" className="pr-preview-btn pr-preview-btn-primary pr-preview-btn-main" onClick={continue_to_review}>
                    Analyze this PR
                  </button>
                  <a href={preview_metadata.html_url} target="_blank" rel="noreferrer" className="pr-preview-btn pr-preview-link">
                    Open on GitHub <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                </div>
              </>
            ) : (
              <div className="pr-preview-loading-shell">
                <div className="pr-preview-eyebrow">Starting review</div>
                <div id={preview_title_id} className="pr-preview-title">{preview_metadata.title}</div>
                <div id={preview_description_id} className="pr-preview-copy">
                  Reviewer is preparing the review now.
                </div>
                <div className="rp-shimmer-bar" />
                <div className="rp-loading-steps pr-preview-loading-steps">
                  {review_loading_steps.map((step, index) => (
                    <div key={step} className="rp-loading-step" style={{ "--rp-delay": `${index * 110}ms` } as CSSProperties}>
                      <span className="rp-loading-step-index">0{index + 1}</span>
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>,
        document.body
      ) : null}
    </>
  );
}

