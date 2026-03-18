import { Database, FileSearch, Github, ShieldCheck } from "lucide-react";

import { SiteFooter } from "../components/site_footer";


const pipeline_steps = [
  {
    number: "01",
    icon: Github,
    title: "Paste a public GitHub pull request",
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
      "The backend turns raw diff data into a concrete review model: sensitive paths, blast radius, churn, migrations, config changes, and test presence.",
    points: [
      "Path sensitivity and area classification",
      "Diff shape and review surface extraction",
      "Signals prepared for deterministic scoring",
    ],
    code: `changed_files -> areas + sensitivity
patch_hints -> imports, config, migration
review_context -> blast_radius + coverage_signals`,
  },
  {
    number: "03",
    icon: ShieldCheck,
    title: "Run deterministic merge analysis",
    description:
      "Reviewer applies explainable scoring rules to rank risk signals, compute merge confidence, and generate next reviewer actions without pretending to understand what it does not know.",
    points: [
      "Verdict and merge confidence score",
      "Top risks with evidence",
      "Prioritized next actions",
    ],
    code: `score = deterministic_rules(review_context)
risks = ranked_signals(review_context)
actions = reviewer_actions(score, risks)`,
  },
  {
    number: "04",
    icon: FileSearch,
    title: "Return a focused merge report",
    description:
      "The result page is built for speed: verdict first, then what changed, what matters, which files deserve attention, and why.",
    points: [
      "Top files to inspect first",
      "Signal evidence and provenance",
      "Fast merge decision summary",
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

export function AboutPage() {
  return (
    <div className="page active">
      <div className="how-page-shell">
        <div className="how-hero how-hero-upgraded">
          <div className="hero-eyebrow">
            <span className="hero-dot" />
            <span>How Reviewer works</span>
          </div>
          <h1 className="how-h1">A fast merge review system built around real PR signals.</h1>
          <p className="how-sub">
            Reviewer does one job well: turn a public GitHub pull request into a structured, explainable merge report that helps engineers know where to look before they approve.
          </p>
          <div className="how-trust-row">
            {trust_points.map((trust_point) => (
              <div key={trust_point} className="how-trust-chip">{trust_point}</div>
            ))}
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
              <span>Merge report</span>
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

          <div className="how-bottom-grid">
            <div className="output-preview how-preview-panel">
              <div className="output-title">sample output fields</div>
              <div className="output-fields output-fields-compact how-preview-output-grid">
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

            <div className="how-limit-panel">
              <div className="a-panel-title">guardrails</div>
              <div className="limit-item">Static analysis only</div>
              <div className="limit-item">No secrets scanning</div>
              <div className="limit-item">Public repos only</div>
              <div className="limit-item">Interprets diffs, does not execute code</div>
            </div>
          </div>
        </div>
      </div>

      <SiteFooter />
    </div>
  );
}
