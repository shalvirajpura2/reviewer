import { useEffect, useState, type ElementType } from "react";
import { Activity, Bot, Eye, ShieldCheck, Sparkles, TerminalSquare } from "lucide-react";

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

const surface_items = [
  {
    icon: Eye,
    eyebrow: "Review in browser",
    title: "Web Review Workspace",
    detail:
      "Paste a public pull request URL, inspect the verdict, follow the top files, and understand exactly what pushed risk up or down.",
    points: ["Paste PR URL", "Guided review workspace", "Explainable verdict"],
  },
  {
    icon: Bot,
    eyebrow: "Review in GitHub",
    title: "GitHub Review Bot",
    detail:
      "Install the Reviewer app on a repository, select an open pull request, and choose whether reviews should run manually or automatically.",
    points: ["Manual Review", "Automatic Review", "Review New Pushes"],
  },
  {
    icon: TerminalSquare,
    eyebrow: "Review in terminal",
    title: "CLI",
    detail:
      "Install Reviewer locally, sign in once, analyze pull requests from the terminal, and publish summaries through the hosted backend flow.",
    points: ["reviewer login", "reviewer analyze <pr-url>", "reviewer publish-summary <pr-url>"],
  },
];

const bot_steps = [
  "Connect GitHub",
  "Choose repository",
  "Select an open PR",
  "Review now or enable automation",
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
            <span>Three review surfaces, one shared engine</span>
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
            Review on the <span className="hl">website</span>, in <span className="hl">GitHub</span>, or from the <span className="hl">terminal</span>.
          </h1>
          <p className="hero-sub">
            Reviewer is no longer just a web report. Use the <b>Web Review Workspace</b>, the <b>GitHub Review Bot</b>, or the <b>CLI</b> depending on where your team wants review feedback to land.
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

      <div className="surfaces-section">
        <div className="section-label">Choose your surface</div>
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
              </div>
            );
          })}
        </div>
      </div>

      <div className="bot-flow-section">
        <div className="section-label">GitHub Review Bot flow</div>
        <div className="bot-flow-card">
          <div className="bot-flow-copy">
            <div className="bot-flow-title">Install once, choose how Reviewer should behave on each repository.</div>
            <div className="bot-flow-detail">
              The website should guide users through repository selection, open pull request selection, and the two bot modes that matter: <b>Manual Review</b> and <b>Automatic Review</b>.
            </div>
          </div>
          <div className="bot-flow-steps">
            {bot_steps.map((step, index) => (
              <div key={step} className="bot-flow-step">
                <div className="bot-flow-step-number">0{index + 1}</div>
                <div className="bot-flow-step-label">{step}</div>
              </div>
            ))}
          </div>
          <div className="bot-flow-modes">
            <div className="bot-mode-chip">Manual Review</div>
            <div className="bot-mode-chip">Automatic Review</div>
            <div className="bot-mode-chip">Review New Pushes</div>
          </div>
        </div>
      </div>

      <SiteFooter />
    </div>
  );
}
