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
    title: "Clear merge verdict",
    detail:
      "Get a rule-based risk score, a plain-language verdict, and a clear read on how much confidence to place in the review.",
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
      "See what is driving attention: sensitive code, dependencies, config, migrations, tests, and blast radius.",
    tag: "Explained",
  },
  {
    icon: Sparkles,
    title: "Know what the result used",
    detail:
      "Every report shows when the analysis is partial, cached, or live so the output stays useful without overclaiming.",
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

export function HomePage() {
  const [site_stats, set_site_stats] = useState<SiteStats | null>(null);

  useEffect(() => {
    let is_active = true;

    async function load_home_data() {
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
            <span>Rule-based pull request review</span>
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
            Start the review <span className="hl">faster</span>.
          </h1>
          <p className="hero-sub">
            Paste a <b>public GitHub pull request</b> to see where review should start, what raised risk, and
            how much confidence to place in the result.
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
                <div className="stat-label">rule-based scoring</div>
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

