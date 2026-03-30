import { AlertCircle, ArrowRight, Link2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { normalize_pr_url, pr_url_validation_message, sample_pr_url } from "../lib/pr_url";

type PrInputBarProps = {
  mode?: "hero" | "compact";
};

const own_pr_prompts = [
  "Paste a PR your team is actively reviewing.",
  "Try the pull request you opened most recently.",
  "Use a real PR to see the files reviewers should inspect first.",
];

export function PrInputBar({ mode = "hero" }: PrInputBarProps) {
  const navigate = useNavigate();
  const [pr_url, set_pr_url] = useState("");
  const [is_loading, set_is_loading] = useState(false);
  const [validation_message, set_validation_message] = useState<string | null>(null);
  const is_compact = mode === "compact";

  function submit_pr() {
    const normalized_pr_url = normalize_pr_url(pr_url);
    const next_validation_message = pr_url_validation_message(normalized_pr_url);

    set_validation_message(next_validation_message);

    if (next_validation_message || is_loading) {
      return;
    }

    set_is_loading(true);
    window.setTimeout(() => {
      navigate(`/result?pr_url=${encodeURIComponent(normalized_pr_url)}`);
    }, 260);
  }

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
            set_pr_url(event.target.value);
            if (validation_message) {
              set_validation_message(pr_url_validation_message(event.target.value));
            }
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              submit_pr();
            }
          }}
          placeholder="https://github.com/owner/repo/pull/123"
          className="pr-url"
        />
        <button onClick={submit_pr} disabled={is_loading} className="analyze-btn">
          {is_loading ? "Loading" : "Analyze"}
          <ArrowRight className="ml-2 inline h-4 w-4" />
        </button>
      </div>
      {validation_message ? (
        <div className="input-validation">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          <span>{validation_message}</span>
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
          }}
        >
          Load the sample PR
        </button>
      </div>
      {!is_compact ? (
        <div className="input-proof-strip">
          <span className="input-proof-chip">Find risky files first</span>
          <span className="input-proof-chip">See what drives the score</span>
          <span className="input-proof-chip">Open the review with a plan</span>
        </div>
      ) : null}
    </div>
  );
}
