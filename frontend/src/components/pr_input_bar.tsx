import { AlertCircle, ArrowRight, ExternalLink, GitBranch, Link2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { preview_pr, type PrPreview } from "../lib/api";
import { normalize_pr_url, pr_url_validation_message, sample_pr_url } from "../lib/pr_url";

type PrInputBarProps = {
  mode?: "hero" | "compact";
};

const own_pr_prompts = [
  "Paste a PR your team is actively reviewing.",
  "Try the pull request you opened most recently.",
  "Use a real PR to see the files reviewers should inspect first.",
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

export function PrInputBar({ mode = "hero" }: PrInputBarProps) {
  const navigate = useNavigate();
  const [pr_url, set_pr_url] = useState("");
  const [is_loading, set_is_loading] = useState(false);
  const [validation_message, set_validation_message] = useState<string | null>(null);
  const [preview, set_preview] = useState<PrPreview | null>(null);
  const [preview_error, set_preview_error] = useState<string | null>(null);
  const is_compact = mode === "compact";

  async function submit_pr() {
    const normalized_pr_url = normalize_pr_url(pr_url);
    const next_validation_message = pr_url_validation_message(normalized_pr_url);

    setValidation(next_validation_message);

    if (next_validation_message || is_loading) {
      return;
    }

    set_is_loading(true);
    set_preview_error(null);

    try {
      const next_preview = await preview_pr(normalized_pr_url);
      set_preview(next_preview);
    } catch (error) {
      set_preview(null);
      set_preview_error(error instanceof Error ? error.message : "Reviewer could not load that pull request preview.");
    } finally {
      set_is_loading(false);
    }
  }

  function setValidation(message: string | null) {
    set_validation_message(message);
    if (message) {
      set_preview(null);
      set_preview_error(null);
    }
  }

  function continue_to_review() {
    const normalized_pr_url = normalize_pr_url(pr_url);
    navigate(`/result?pr_url=${encodeURIComponent(normalized_pr_url)}`);
  }

  const preview_metadata = preview?.metadata;

  return (
    <div className={`input-zone ${is_compact ? "input-zone-compact" : ""}`}>
      <div className="input-label">{is_compact ? "// Analyze a real pull request" : "// Paste your own GitHub pull request URL"}</div>
      {!is_compact ? (
        <div className="input-message-shell">
          <div className="input-message-title">Bring your own PR</div>
          <div className="input-message-copy">
            Reviewer is most useful when you paste a live PR you actually care about right now.
          </div>
          <div className="input-message-points">
            {own_pr_prompts.map((prompt) => (
              <div key={prompt} className="input-message-point">
                <span className="input-message-dot" />
                <span>{prompt}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      <div className="input-frame">
        <div className="input-prefix">
          <Link2 className="h-4 w-4 shrink-0" />
        </div>
        <input
          value={pr_url}
          onChange={(event) => {
            const next_value = event.target.value;
            set_pr_url(next_value);
            set_preview(null);
            set_preview_error(null);
            if (validation_message) {
              setValidation(pr_url_validation_message(next_value));
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
        <button onClick={() => void submit_pr()} disabled={is_loading} className="analyze-btn">
          {is_loading ? "Previewing" : "Preview"}
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
      {preview_metadata ? (
        <div className="pr-preview-card">
          <div className="pr-preview-eyebrow">Ready to analyze</div>
          <div className="pr-preview-title">{preview_metadata.title}</div>
          <div className="pr-preview-repo">{preview_metadata.repo_full_name} #{preview_metadata.pull_number}</div>
          <div className="pr-preview-copy">
            This looks like the right pull request. Reviewer will use GitHub metadata, changed files, and commit history to build the review workspace.
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
            <button type="button" className="pr-preview-btn pr-preview-btn-primary" onClick={continue_to_review}>
              Analyze this PR
            </button>
            <button type="button" className="pr-preview-btn" onClick={() => set_preview(null)}>
              Change URL
            </button>
            <a href={preview_metadata.html_url} target="_blank" rel="noreferrer" className="pr-preview-btn pr-preview-link">
              Open on GitHub <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
        </div>
      ) : null}
      <div className="input-hint">
        <span className="input-hint-item input-hint-item-primary">Public GitHub PRs only</span>
        <span className="input-hint-item">No signup</span>
        <span className="input-hint-item">Best with your own PR</span>
      </div>
      <div className="input-sample-row">
        <span className="input-sample-label">Want a quick demo first?</span>
        <button
          type="button"
          className="input-sample-link"
          onClick={() => {
            set_pr_url(sample_pr_url);
            set_validation_message(null);
            set_preview(null);
            set_preview_error(null);
          }}
        >
          Load the sample PR
        </button>
      </div>
      {!is_compact ? (
        <div className="input-proof-strip">
          <span className="input-proof-chip">See the PR before review</span>
          <span className="input-proof-chip">Find risky files first</span>
          <span className="input-proof-chip">Open the review with a plan</span>
        </div>
      ) : null}
    </div>
  );
}
