import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { SiteFooter } from "../components/site_footer";
import { get_recent_analyses, type RecentAnalysis } from "../lib/api";

function format_relative_time(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "recently";
  }

  const diff_ms = Date.now() - date.getTime();
  const diff_minutes = Math.max(1, Math.round(diff_ms / 60000));

  if (diff_minutes < 60) {
    return `${diff_minutes}m ago`;
  }

  const diff_hours = Math.round(diff_minutes / 60);
  if (diff_hours < 24) {
    return `${diff_hours}h ago`;
  }

  const diff_days = Math.round(diff_hours / 24);
  return `${diff_days}d ago`;
}

function confidence_badge(analysis: RecentAnalysis) {
  if (analysis.score >= 85) {
    return "mergeable";
  }

  if (analysis.score >= 70) {
    return "focused review";
  }

  return "review needed";
}

function source_badge(analysis: RecentAnalysis) {
  if (analysis.cache_status === "fallback") {
    return "saved fallback";
  }

  if (analysis.cache_status === "cached") {
    return "cache";
  }

  return analysis.cache_status;
}

function result_path(pr_url: string) {
  return `/result?pr_url=${encodeURIComponent(pr_url)}`;
}

export function HistoryPage() {
  const [recent_analyses, set_recent_analyses] = useState<RecentAnalysis[]>([]);
  const [is_loading, set_is_loading] = useState(true);
  const [error_message, set_error_message] = useState<string | null>(null);

  useEffect(() => {
    let is_active = true;

    async function load_history() {
      try {
        const next_recent_analyses = await get_recent_analyses();
        if (is_active) {
          set_recent_analyses(next_recent_analyses);
          set_error_message(null);
        }
      } catch (error) {
        if (is_active) {
          set_error_message(error instanceof Error ? error.message : "Reviewer could not load history right now.");
          set_recent_analyses([]);
        }
      } finally {
        if (is_active) {
          set_is_loading(false);
        }
      }
    }

    void load_history();

    return () => {
      is_active = false;
    };
  }, []);

  return (
    <div className="history-page">
      <section className="history-hero">
        <div className="history-eyebrow">Saved review flow</div>
        <h1 className="history-title">Reopen the reviews people actually ran.</h1>
        <p className="history-copy">
          Every saved analysis is a fast way back into Reviewer. Open the review workspace again, compare sources,
          or jump straight to the original PR on GitHub.
        </p>
        <div className="history-actions">
          <Link to="/" className="history-action history-action-primary">Analyze another PR</Link>
          <a href="https://github.com/shalvirajpura2/reviewer" target="_blank" rel="noreferrer" className="history-action">
            Open project GitHub
          </a>
        </div>
      </section>

      <section className="history-grid-shell">
        {is_loading ? (
          <div className="history-empty">Loading saved reviews...</div>
        ) : error_message ? (
          <div className="history-empty">{error_message}</div>
        ) : recent_analyses.length > 0 ? (
          <div className="history-grid">
            {recent_analyses.map((analysis) => (
              <div key={`${analysis.pr_url}-${analysis.analyzed_at}`} className="history-card">
                <div className="history-card-head">
                  <div>
                    <div className="history-repo">{analysis.repo_name} #{analysis.pr_number}</div>
                    <div className="history-card-title">{analysis.title}</div>
                  </div>
                  <div className="history-score">{analysis.score}</div>
                </div>

                <div className="history-meta-row">
                  <span className="recent-analysis-chip">{confidence_badge(analysis)}</span>
                  <span className="recent-analysis-chip recent-analysis-chip-muted">{source_badge(analysis)}</span>
                  <span className="recent-analysis-time">{format_relative_time(analysis.analyzed_at)}</span>
                </div>

                <div className="history-card-actions">
                  <Link to={result_path(analysis.pr_url)} className="history-card-link history-card-link-primary">
                    Open in Reviewer
                  </Link>
                  <a href={analysis.pr_url} target="_blank" rel="noreferrer" className="history-card-link">
                    Open PR on GitHub
                  </a>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="history-empty">
            Saved reviews will show up here after people start analyzing public pull requests with Reviewer.
          </div>
        )}
      </section>

      <SiteFooter />
    </div>
  );
}
