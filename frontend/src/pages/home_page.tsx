import { useEffect, useState, type ElementType } from "react";
import { Activity, Eye, ShieldCheck, Sparkles } from "lucide-react";

import { BackgroundBoxes } from "../components/background_boxes";
import { PrInputBar } from "../components/pr_input_bar";
import { SiteFooter } from "../components/site_footer";
import { get_site_stats, type SiteStats } from "../lib/api";


const LottiePlayer = "lottie-player" as ElementType;

const feature_items = [
  {
    icon: ShieldCheck,
    title: "Merge Confidence Score",
    detail:
      "A 0-100 score with a clear verdict, derived from deterministic signals like sensitive paths, diff size, missing tests, migrations, and blast radius.",
    tag: "Scored",
  },
  {
    icon: Activity,
    title: "Risk Breakdown",
    detail:
      "See exactly which review dimensions are driving risk: sensitive code, dependencies, migrations, config changes, tests, and blast radius.",
    tag: "Explained",
  },
  {
    icon: Eye,
    title: "Top Files To Inspect",
    detail:
      "Reviewer ranks the files most likely to deserve focused review first, with reasons tied to diff shape, sensitivity, and impact.",
    tag: "Prioritized",
  },
  {
    icon: Sparkles,
    title: "Evidence + Provenance",
    detail:
      "Every report shows the signals that fired, the evidence behind them, and which data sources were actually used so the output feels trustworthy.",
    tag: "Honest",
  },
];

const hero_points = [
  "Live GitHub pull request data",
  "Deterministic scoring, not AI guesswork",
  "Top files to inspect first",
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

export function HomePage() {
  const [site_stats, set_site_stats] = useState<SiteStats | null>(null);

  useEffect(() => {
    let is_active = true;

    async function load_site_stats() {
      try {
        const next_site_stats = await get_site_stats();

        if (is_active) {
          set_site_stats(next_site_stats);
        }
      } catch {
        if (is_active) {
          set_site_stats(null);
        }
      }
    }

    void load_site_stats();

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
            <span>Deterministic merge review</span>
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
            Review the right files <br />
            before you <span className="hl">merge</span>.
          </h1>
          <p className="hero-sub">
            Paste any <b>public GitHub pull request</b> and get a structured merge report in seconds: a confidence score,
            the top files to inspect, evidence-backed risks, and clear next reviewer actions.
          </p>

          <div className="hero-points hero-points-centered">
            {hero_points.map((hero_point) => (
              <div key={hero_point} className="hero-point">
                <span className="hero-point-dot" />
                <span>{hero_point}</span>
              </div>
            ))}
          </div>

          <div className="hero-input-shell">
            <div className="hero-panel-label">Start with one pull request URL</div>
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

      <SiteFooter />
    </div>
  );
}
