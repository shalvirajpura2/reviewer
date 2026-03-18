import { AlertCircle, ArrowRight, Link2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { normalize_pr_url, pr_url_validation_message, sample_pr_url } from "../lib/pr_url";

export function PrInputBar() {
  const navigate = useNavigate();
  const [pr_url, set_pr_url] = useState(sample_pr_url);
  const [is_loading, set_is_loading] = useState(false);
  const [validation_message, set_validation_message] = useState<string | null>(null);

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
    <div className="input-zone">
      <div className="input-label">// GitHub pull request URL</div>
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
        <span className="input-hint-item">
          <span className="input-hint-label">Try</span>
          <button
            type="button"
            onClick={() => {
              set_pr_url(sample_pr_url);
              set_validation_message(null);
            }}
          >
            tailwindcss/pull/14776
          </button>
        </span>
        <span className="input-hint-item">Free to use</span>
        <span className="input-hint-item">No signup</span>
        <span className="input-hint-item">Public repos</span>
      </div>
    </div>
  );
}
