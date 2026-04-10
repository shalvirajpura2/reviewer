import { useEffect, useState, type ElementType } from "react";
import { Link } from "react-router-dom";
import { Activity, Bot, Eye, ShieldCheck, Sparkles, TerminalSquare } from "lucide-react";

import { BackgroundBoxes } from "../components/background_boxes";
import { PrInputBar } from "../components/pr_input_bar";
import { SiteFooter } from "../components/site_footer";
import { get_site_stats, type SiteStats } from "../lib/api";

const LottiePlayer = "lottie-player" as ElementType;

const feature_items = [
  {
    icon: ShieldCheck,
    title: "Decide faster",
    detail:
      "Get a deterministic risk score, a plain-language verdict, and a clear sense of how much confidence to place in the review.",
    tag: "Verdict",
  },
  {
    icon: Eye,
    title: "Open the right files first",
    detail:
      "Reviewer ranks the files worth opening first so you can start with the highest-impact part of the pull request.",
    tag: "Focus",
  },
  {
    icon: Activity,
    title: "See what is driving risk",
    detail:
      "Review signals stay legible: sensitive code, dependencies, config, migrations, tests, and blast radius.",
    tag: "Signals",
  },
  {
    icon: Sparkles,
    title: "Trust the output",
    detail:
      "Every report shows when analysis is live, cached, or partial so the result stays useful without pretending to know more than it does.",
    tag: "Source-aware",
  },
];

const surface_items = [
  {
    icon: Eye,
    eyebrow: "Browser",
    title: "Web Review Workspace",
    detail:
      "Paste a pull request URL and move through a guided review workspace built for humans, not just raw output.",
    points: ["Read the verdict first", "Follow a guided review path", "Understand what needs attention"],
  },
  {
    icon: Bot,
    eyebrow: "GitHub",
    title: "GitHub Review Bot",
    detail:
      "Connect GitHub, choose a repository, and let Reviewer post summaries directly inside the pull request.",
    points: ["Set up the repo once", "Manual or automatic", "Re-review on new pushes"],
  },
  {
    icon: TerminalSquare,
    eyebrow: "CLI",
    title: "CLI",
    detail:
      "Bring Reviewer into your local workflow with a terminal-first experience for analyzing and publishing review summaries.",
    points: ["Terminal-first workflow", "`reviewer analyze`", "`reviewer publish-summary`"],
  },
];

const launch_paths = [
  {
    title: "Start in the browser",
    detail: "Use Reviewer like a guided review desk. Paste a PR, read the verdict, and follow the review path.",
    action: "Analyze a pull request",
    href: "/",
    external: false,
  },
  {
    title: "Install the bot",
    detail: "Connect GitHub, choose the repository you want to use, and let Reviewer guide the setup before you reach the dashboard.",
    action: "Set up GitHub Bot",
    href: "/github",
    external: false,
  },
  {
    title: "Bring it to the terminal",
    detail: "Use the CLI when review belongs in shell scripts, local workflows, or an engineer's usual toolkit.",
    action: "See CLI setup",
    href: "https://github.com/shalvirajpura2/reviewer",
    external: true,
  },
];

const proof_points = [
  "Clear verdict, risk signals, and next steps",
  "One product across web, GitHub, and CLI",
  "Review output built for real pull requests",
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
            <span>Review pull requests on the web, in GitHub, or from the terminal</span>
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
            Review <span className="hl">pull requests</span> with a workspace, a bot, or a CLI.
          </h1>
          <p className="hero-sub">
            Reviewer gives you three ways to work: a <b>guided web review workspace</b>, a <b>GitHub review bot</b>, and a <b>CLI</b> for terminal-first workflows. Choose the path that fits how you review code.
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

          <div className="hero-proof-row">
            {proof_points.map((proof_point) => (
              <div key={proof_point} className="hero-proof-chip">{proof_point}</div>
            ))}
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
        <div className="section-label">Pick your path</div>
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

      <div className="launch-paths-section">
        <div className="section-label">How to start</div>
        <div className="launch-paths-grid">
          {launch_paths.map((launch_path) => (
            <div key={launch_path.title} className="launch-path-card">
              <div className="launch-path-title">{launch_path.title}</div>
              <div className="launch-path-detail">{launch_path.detail}</div>
              {launch_path.external ? (
                <a href={launch_path.href} target="_blank" rel="noreferrer" className="launch-path-action">
                  {launch_path.action}
                </a>
              ) : (
                <Link to={launch_path.href} className="launch-path-action">
                  {launch_path.action}
                </Link>
              )}
            </div>
          ))}
        </div>
      </div>

      <SiteFooter />
    </div>
  );
}
