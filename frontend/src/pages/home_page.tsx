import { useEffect, useState, type ElementType } from "react";
import { Link } from "react-router-dom";
import { Bot, Eye, TerminalSquare } from "lucide-react";

import { BackgroundBoxes } from "../components/background_boxes";
import { PrInputBar } from "../components/pr_input_bar";
import { SiteFooter } from "../components/site_footer";
import { get_site_stats, type SiteStats } from "../lib/api";

const LottiePlayer = "lottie-player" as ElementType;

const surface_items = [
  {
    icon: Eye,
    eyebrow: "Browser",
    title: "Web Review Workspace",
    detail:
      "Paste a pull request URL, get a verdict, and move through a guided review flow without hunting for where to start.",
    points: ["Paste a PR URL", "See the verdict first", "Open the right files"],
    action: "Analyze a pull request",
    href: "#review-input",
    external: false,
  },
  {
    icon: Bot,
    eyebrow: "GitHub",
    title: "GitHub Review Bot",
    detail:
      "Connect GitHub, choose a repository, and let Reviewer post summaries directly inside the pull request dashboard you already use.",
    points: ["Guided setup", "Manual or automatic", "Re-review on new pushes"],
    action: "Open GitHub Bot",
    href: "/github",
    external: false,
  },
  {
    icon: TerminalSquare,
    eyebrow: "CLI",
    title: "CLI",
    detail:
      "Use Reviewer from the terminal when you want review inside local workflows, scripts, or your usual engineering toolkit.",
    points: ["1) Install: `pip install reviewer-cli`", "2) See commands: `reviewer`", "3) Analyze: `reviewer analyze <pr-url>`", "4) Publish: `reviewer publish-summary <pr-url>`"],
    action: "View CLI setup",
    href: "https://github.com/shalvirajpura2/reviewer",
    external: true,
  },
];

const proof_points = [
  "Verdict, risk signals, and next steps in one view",
  "GitHub bot and CLI support when you need another surface",
  "Review output designed around real pull requests",
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
            <span>One reviewer, three ways to ship better pull requests</span>
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
            Review <span className="hl hl-doodle">pull requests</span> with a workspace, a bot, or a CLI.
          </h1>
          <p className="hero-sub">
            Reviewer helps you inspect pull requests in the browser, inside GitHub, or from the terminal. Start with the web workspace, or jump straight to the surface that fits your workflow.
          </p>

          <div id="review-input" className="hero-input-shell">
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

          <div className="hero-proof-row">
            {proof_points.map((proof_point) => (
              <div key={proof_point} className="hero-proof-chip">{proof_point}</div>
            ))}
          </div>
        </div>
      </div>

      <div className="surfaces-section">
        <div className="section-label">Pick how you want to use Reviewer</div>
        <div className="surface-grid">
          {surface_items.map((surface_item) => {
            const Icon = surface_item.icon;

            return (
              <div key={surface_item.title} className="surface-card">
                <div className="surface-topline">{surface_item.eyebrow}</div>
                <div className="surface-icon">
                  <Icon className="h-5 w-5" strokeWidth={1.9} />
                </div>
                <div className="surface-title">{surface_item.title}</div>
                <div className="surface-detail">{surface_item.detail}</div>
                <div className="surface-points">
                  {surface_item.points.map((point) => (
                    <div key={point} className="surface-point">{point}</div>
                  ))}
                </div>
                {surface_item.external ? (
                  <a href={surface_item.href} target="_blank" rel="noreferrer" className="surface-action">
                    {surface_item.action}
                  </a>
                ) : (
                  <Link to={surface_item.href} className="surface-action">
                    {surface_item.action}
                  </Link>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <SiteFooter />
    </div>
  );
}
