import { useEffect, useState, type ElementType } from "react";
import { Activity, Eye, ShieldCheck, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { BackgroundBoxes } from "../components/background_boxes";
import { PrInputBar } from "../components/pr_input_bar";
import { SiteFooter } from "../components/site_footer";
import { get_recent_analyses, get_site_stats, type RecentAnalysis, type SiteStats } from "../lib/api";

const LottiePlayer = "lottie-player" as ElementType;

const feature_items = [
  {
    icon: ShieldCheck,
    title: "Clear merge verdict",
    detail:
      "Get a deterministic score, a plain-language verdict, and an honest signal of how much review confidence the diff deserves.",
    tag: "Scored",
  },
  {
    icon: Eye,
    title: "Start with the right files",
    detail:
      "Reviewer ranks the files most worth opening first so you can begin with the highest-impact parts of the pull request.",
    tag: "Prioritized",
  },
  {
    icon: Activity,
    title: "Understand the risk shape",
    detail:
      "See which review dimensions are driving risk: sensitive code, dependencies, config, migrations, tests, and blast radius.",
    tag: "Explained",
  },
  {
    icon: Sparkles,
    title: "See what the analysis used",
    detail:
      "Every report shows where the result came from and when the review is partial, cached, or missing fresh GitHub context.",
    tag: "Honest",
  },
];

function format_avg_time(value: number | null) {
  if (value === null) {
    return "--";
  }

  if (value >= 10) {
    return Math.round(value).toString();
  }

  return value.toFixed(1);
}

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

export function HomePage() {
  const [site_stats, set_site_stats] = useState<SiteStats | null>(null);
  const [recent_analyses, set_recent_analyses] = useState<RecentAnalysis[]>([]);

  useEffect(() => {
    let is_active = true;

    async function load_home_data() {
      try {
        const [next_site_stats, next_recent_analyses] = await Promise.all([
          get_site_stats(),
          get_recent_analyses(),
        ]);

        if (is_active) {
          set_site_stats(next_site_stats);
          set_recent_analyses(next_recent_analyses.slice(0, 4));
        }
      } catch {
        if (is_active) {
          set_site_stats(null);
          set_recent_analyses([]);
        }
      }
    }

    void load_home_data();

    return () => {
      is_active = false;
    };
  }, []);

  return (
    <div className="page active">
      <div className="home-hero-wrapper">
        <BackgroundBoxes />
        <div className="home-hero">
          <div className="hero-eyebrow">
            <span className="hero-dot" />
            <span>Deterministic pull request review</span>
          </div>

          <div className="hero-lottie-shell" aria-hidden="true">
            <LottiePlayer
              src="/animations/eyes.json"
              background="transparent"
              speed="1"
              loop
              autoplay
              className="hero-lottie-frame"
            />
          </div>

          <h1 className="hero-h1">
            Paste a PR. <br />
            Start the review faster.
          </h1>
          <p className="hero-sub">
            Reviewer reads a <b>public GitHub pull request</b> and shows you what to inspect first, what raised risk,
            and how much confidence to place in the score.
          </p>

          <div className="hero-input-shell">
            <PrInputBar />
          </div>

          <div className="hero-stats-shell">
            <div className="hero-stats">
              <div className="stat-item">
                <div className="stat-num">{site_stats ? site_stats.prs_analyzed.toLocaleString() : "--"}</div>
                <div className="stat-label">PRs analyzed</div>
              </div>
              <div className="stat-item stat-item-padded">
                <div className="stat-num">
                  {site_stats ? site_stats.deterministic_scoring_rate : "--"}
                  <small>%</small>
                </div>
                <div className="stat-label">deterministic scoring</div>
              </div>
              <div className="stat-item stat-item-padded">
                <div className="stat-num">
                  {format_avg_time(site_stats?.avg_report_time_seconds ?? null)}
                  <small>s</small>
                </div>
                <div className="stat-label">avg report time</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="features-section">
        <div className="section-label">What you get</div>
        <div className="features-grid">
          {feature_items.map((feature_item) => {
            const Icon = feature_item.icon;

            return (
              <div key={feature_item.title} className="feature-card">
                <div className="feat-icon">
                  <Icon className="h-4 w-4" strokeWidth={1.9} />
                </div>
                <div className="feat-title">{feature_item.title}</div>
                <div className="feat-desc">{feature_item.detail}</div>
                <div className="feat-tag">{feature_item.tag}</div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="features-section recent-analyses-section">
        <div className="recent-analyses-topbar">
          <div>
            <div className="section-label">Recent analyses</div>
            <div className="recent-analyses-copy">
              Reopen saved reviews inside Reviewer or jump to GitHub when you need the raw pull request.
            </div>
          </div>
          <Link to="/history" className="recent-analyses-link">Open full history</Link>
        </div>
        <div className="recent-analyses-grid">
          {recent_analyses.length > 0 ? recent_analyses.map((analysis) => (
            <div key={analysis.pr_url} className="recent-analysis-card">
              <Link to={result_path(analysis.pr_url)} className="recent-analysis-main-link">
                <div className="recent-analysis-head">
                  <div>
                    <div className="recent-analysis-repo">{analysis.repo_name} #{analysis.pr_number}</div>
                    <div className="recent-analysis-title">{analysis.title}</div>
                  </div>
                  <div className="recent-analysis-score">{analysis.score}</div>
                </div>
                <div className="recent-analysis-meta-row">
                  <span className="recent-analysis-chip">{confidence_badge(analysis)}</span>
                  <span className="recent-analysis-chip recent-analysis-chip-muted">{source_badge(analysis)}</span>
                  <span className="recent-analysis-time">{format_relative_time(analysis.analyzed_at)}</span>
                </div>
              </Link>
              <div className="recent-analysis-card-actions">
                <Link to={result_path(analysis.pr_url)} className="recent-analysis-action recent-analysis-action-primary">Open in Reviewer</Link>
                <a href={analysis.pr_url} target="_blank" rel="noreferrer" className="recent-analysis-action">Open PR</a>
              </div>
            </div>
          )) : (
            <div className="recent-analysis-empty">
              Recent PR analyses will appear here after people start using Reviewer with real pull requests.
            </div>
          )}
        </div>
      </div>

      <SiteFooter />
    </div>
  );
}
