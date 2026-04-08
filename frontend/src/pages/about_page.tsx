import { Database, FileSearch, Github, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { SiteFooter } from "../components/site_footer";

const product_surfaces = [
  {
    eyebrow: "Review in browser",
    title: "Web Review Workspace",
    detail:
      "Paste a public pull request URL and move through the verdict, signals, top files, and next steps in one guided workspace.",
    points: ["Paste PR URL", "Inspect risks and verdict", "Follow the top-file path"],
  },
  {
    eyebrow: "Review in GitHub",
    title: "GitHub Review Bot",
    detail:
      "Install the Reviewer app on a repository, pick an open pull request, and choose whether review should run manually or automatically.",
    points: ["Manual Review", "Automatic Review", "Review New Pushes"],
  },
  {
    eyebrow: "Review in terminal",
    title: "CLI",
    detail:
      "Use Reviewer from the terminal when you want a fast local workflow, then publish the summary through the hosted bot path.",
    points: ["reviewer login", "reviewer analyze <pr-url>", "reviewer publish-summary <pr-url>"],
  },
];

const pipeline_steps = [
  {
    number: "01",
    icon: Github,
    title: "Read the pull request from GitHub",
    description:
      "Reviewer validates the PR URL, resolves the repository, and fetches the pull request, changed files, and commit history directly from GitHub.",
    points: [
      "Pull request metadata and branch context",
      "Changed files, patch hunks, additions, and deletions",
      "Recent commits and commit messages",
    ],
    code: `GET /repos/{owner}/{repo}/pulls/{number}
GET /repos/{owner}/{repo}/pulls/{number}/files
GET /repos/{owner}/{repo}/pulls/{number}/commits`,
  },
  {
    number: "02",
    icon: Database,
    title: "Build structured review context",
    description:
      "The backend turns raw diff data into a review model: sensitive paths, blast radius, migrations, config changes, patch visibility, and test presence.",
    points: [
      "Path sensitivity and area classification",
      "Diff shape and review surface extraction",
      "Signals prepared for rule-based scoring",
    ],
    code: `changed_files -> areas + sensitivity
patch_hints -> imports, config, migration
review_context -> blast_radius + coverage_signals`,
  },
  {
    number: "03",
    icon: ShieldCheck,
    title: "Run rule-based review scoring",
    description:
      "Reviewer applies explainable rules to rank risk signals, estimate merge confidence, and generate reviewer actions without pretending to know what it cannot verify.",
    points: [
      "Verdict and merge confidence score",
      "Top risks with evidence",
      "Prioritized next actions",
    ],
    code: `score = rule_based_risk_score(review_context)
risks = ranked_signals(review_context)
actions = reviewer_actions(score, risks)`,
  },
  {
    number: "04",
    icon: FileSearch,
    title: "Return a guided review workspace",
    description:
      "The result page is built for speed: verdict first, then what matters, which files deserve attention, and what still needs human judgment.",
    points: [
      "Top files to inspect first",
      "Signal evidence and provenance",
      "A focused review path",
    ],
    code: `result -> verdict
result -> top_risk_files
result -> signal_evidence + provenance`,
  },
];

const output_fields = [
  { label: "verdict", value: "FOCUSED REVIEW", tone: "amber" },
  { label: "confidence", value: "61", suffix: "/100" },
  { label: "top file", value: "src/auth/session.ts", tone: "red" },
  { label: "top risk", value: "Missing tests", tone: "amber" },
  { label: "files changed", value: "14" },
  { label: "source", value: "GitHub live" },
];

const trust_points = [
  "Deterministic scoring",
  "GitHub-backed data",
  "Evidence before confidence",
  "Built for fast review",
];

const bot_modes = [
  "Manual Review for one selected open pull request",
  "Automatic Review when a new pull request opens",
  "Review New Pushes when new commits are added",
];

const reliability_points = [
  "Shows when analysis is cached, partial, or using a saved fallback.",
  "Uses GitHub metadata, changed files, commits, and patch hints instead of invented context.",
  "Ranks files and signals before asking for reviewer attention.",
];

const guardrail_points = [
  "Static analysis only",
  "No secrets scanning",
  "Public repos only",
  "Interprets diffs, does not execute code",
];

export function AboutPage() {
  return (
    <div className="page active">
      <div className="how-page-shell">
        <div className="how-hero how-hero-upgraded">
          <div className="hero-eyebrow">
            <span className="hero-dot" />
            <span>How Reviewer works</span>
          </div>
          <h1 className="how-h1">One review engine, delivered across the website, GitHub, and the terminal.</h1>
          <p className="how-sub">
            Reviewer turns a public GitHub pull request into structured review output, then delivers it through the <b>Web Review Workspace</b>, the <b>GitHub Review Bot</b>, and the <b>CLI</b> so teams can work where they already review code.
          </p>
          <div className="how-trust-row">
            {trust_points.map((trust_point) => (
              <div key={trust_point} className="how-trust-chip">{trust_point}</div>
            ))}
          </div>
        </div>

        <div className="surfaces-section">
          <div className="section-label">Product surfaces</div>
          <div className="surface-grid">
            {product_surfaces.map((product_surface) => (
              <div key={product_surface.title} className="surface-card">
                <div className="surface-topline">{product_surface.eyebrow}</div>
                <div className="surface-title">{product_surface.title}</div>
                <div className="surface-detail">{product_surface.detail}</div>
                <div className="surface-points">
                  {product_surface.points.map((point) => (
                    <div key={point} className="surface-point">{point}</div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bot-flow-section">
          <div className="section-label">GitHub bot behavior</div>
          <div className="bot-flow-card">
            <div className="bot-flow-copy">
              <div className="bot-flow-title">Connect a repository, select an open pull request, then decide how hands-on Reviewer should be.</div>
              <div className="bot-flow-detail">
                The website should guide users through repository selection, open pull request selection, and the two operating styles that matter: trigger a review yourself or let the GitHub bot handle it automatically.
              </div>
            </div>
            <div className="bot-flow-steps">
              {bot_modes.map((mode, index) => (
                <div key={mode} className="bot-flow-step">
                  <div className="bot-flow-step-number">0{index + 1}</div>
                  <div className="bot-flow-step-label">{mode}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="how-overview-grid">
          <div className="how-overview-card how-overview-system-card">
            <div className="a-panel-title">system view</div>
            <div className="how-system-flow">
              <span>PR URL</span>
              <span>GitHub data</span>
              <span>Review context</span>
              <span>Scoring</span>
              <span>Review workspace</span>
            </div>
          </div>
          <div className="how-overview-card how-overview-output-card">
            <div className="a-panel-title">what comes back</div>
            <div className="output-fields output-fields-compact how-overview-output-grid">
              {output_fields.map((output_field) => (
                <div key={output_field.label} className="output-field how-output-field">
                  <div className="of-label">{output_field.label}</div>
                  <div className={`of-val how-of-val ${output_field.tone ?? ""}`.trim()}>
                    {output_field.value}
                    {output_field.suffix ? <span className="of-suffix">{output_field.suffix}</span> : null}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="steps-section steps-section-upgraded">
          <div className="section-label">The pipeline</div>

          <div className="how-steps-grid">
            {pipeline_steps.map((pipeline_step) => {
              const Icon = pipeline_step.icon;

              return (
                <div key={pipeline_step.number} className="how-step-card">
                  <div className="how-step-top">
                    <div className="how-step-number">{pipeline_step.number}</div>
                    <div className="how-step-icon">
                      <Icon className="h-4 w-4" strokeWidth={1.9} />
                    </div>
                  </div>
                  <div className="step-title">{pipeline_step.title}</div>
                  <div className="step-desc">{pipeline_step.description}</div>
                  <div className="how-step-points">
                    {pipeline_step.points.map((point) => (
                      <div key={point} className="how-step-point">{point}</div>
                    ))}
                  </div>
                  <div className="step-code">{pipeline_step.code}</div>
                </div>
              );
            })}
          </div>

          <div className="how-bottom-grid how-bottom-grid-balanced">
            <div className="how-limit-panel">
              <div className="a-panel-title">why this feels trustworthy</div>
              {reliability_points.map((point) => (
                <div key={point} className="limit-item">{point}</div>
              ))}
            </div>

            <div className="how-limit-panel">
              <div className="a-panel-title">guardrails</div>
              {guardrail_points.map((point) => (
                <div key={point} className="limit-item">{point}</div>
              ))}
            </div>
          </div>

          <div className="how-footer-actions">
            <Link to="/" className="history-action history-action-primary">Analyze a PR</Link>
            <a href="https://github.com/apps/reviewer-live" className="history-action" target="_blank" rel="noreferrer">Install GitHub App</a>
          </div>
        </div>
      </div>

      <SiteFooter />
    </div>
  );
}
