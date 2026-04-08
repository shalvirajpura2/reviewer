import { Bot, CheckCircle2, Github, GitPullRequest, History, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";

import { SiteFooter } from "../components/site_footer";

type RepositoryCard = {
  name: string;
  state: "installed" | "manual";
  summary: string;
  open_prs: number;
  review_mode: string;
};

type PullRequestCard = {
  title: string;
  repo: string;
  number: number;
  updated: string;
  mode: string;
  summary: string;
};

const repositories: RepositoryCard[] = [
  {
    name: "shalvirajpura2/reviewer",
    state: "installed",
    summary: "Reviewer is installed and ready to post manual or automatic summaries on open pull requests.",
    open_prs: 3,
    review_mode: "automatic review",
  },
  {
    name: "shalvirajpura2/reviewer-docs",
    state: "manual",
    summary: "Keep the bot quiet by default, then trigger a single review when a PR needs a deeper pass.",
    open_prs: 1,
    review_mode: "manual review",
  },
];

const open_pull_requests: PullRequestCard[] = [
  {
    title: "Ship GitHub App bot publishing",
    repo: "shalvirajpura2/reviewer",
    number: 18,
    updated: "6m ago",
    mode: "Automatic Review",
    summary: "Configured to review on PR open and post updates when new commits are pushed.",
  },
  {
    title: "Polish frontend clarity pass",
    repo: "shalvirajpura2/reviewer",
    number: 19,
    updated: "18m ago",
    mode: "Manual Review",
    summary: "Ready for a one-click review now from the website before merge.",
  },
  {
    title: "Refine bot repository settings UX",
    repo: "shalvirajpura2/reviewer",
    number: 20,
    updated: "31m ago",
    mode: "Review New Pushes",
    summary: "Configured to run again whenever a new commit lands on this open pull request.",
  },
  {
    title: "Tighten CLI onboarding copy",
    repo: "shalvirajpura2/reviewer-docs",
    number: 7,
    updated: "42m ago",
    mode: "Review New Pushes",
    summary: "Runs again when commits land so the GitHub summary stays fresh on the same PR.",
  },
];

const automation_modes = [
  {
    title: "Manual Review",
    detail: "Pick one open pull request and ask Reviewer to post a summary right now.",
  },
  {
    title: "Automatic Review",
    detail: "Post a Reviewer summary automatically whenever a new pull request opens.",
  },
  {
    title: "Review New Pushes",
    detail: "Re-run the summary when additional commits are pushed to the same open pull request.",
  },
];

const activity_items = [
  "Last bot summary posted 6 minutes ago on reviewer#18",
  "Automatic review is enabled on 1 repository",
  "Review New Pushes is enabled on 2 open pull requests",
];

function repo_state_class(state: RepositoryCard["state"]) {
  if (state === "installed") {
    return "gb-state gb-state-live";
  }

  return "gb-state gb-state-manual";
}

export function GithubBotPage() {
  const [selected_repository, set_selected_repository] = useState(repositories[0]?.name ?? "");

  const filtered_pull_requests = useMemo(
    () => open_pull_requests.filter((pull_request) => pull_request.repo === selected_repository),
    [selected_repository]
  );

  const selected_repository_card = repositories.find((repository) => repository.name === selected_repository) ?? repositories[0];

  return (
    <div className="github-bot-page">
      <section className="github-bot-hero">
        <div className="history-eyebrow">GitHub Review Bot</div>
        <h1 className="history-title">Select a repository, choose an open pull request, and let Reviewer handle the GitHub summary flow.</h1>
        <p className="history-copy">
          This is the management surface for the GitHub bot. Repositories stay connected here, only open pull requests show up, and you can decide whether Reviewer should run manually or automatically.
        </p>
        <div className="history-actions">
          <a href="https://github.com/apps/reviewer-live" target="_blank" rel="noreferrer" className="history-action history-action-primary">
            Install GitHub App
          </a>
          <a href="https://github.com/shalvirajpura2/reviewer" target="_blank" rel="noreferrer" className="history-action">
            Open project GitHub
          </a>
        </div>
      </section>

      <section className="gb-grid-shell">
        <div className="gb-summary-grid">
          <div className="gb-summary-card">
            <div className="gb-summary-label">connected repositories</div>
            <div className="gb-summary-value">{repositories.length}</div>
            <div className="gb-summary-copy">Repositories where the Reviewer app is already available.</div>
          </div>
          <div className="gb-summary-card">
            <div className="gb-summary-label">open pull requests</div>
            <div className="gb-summary-value">{filtered_pull_requests.length}</div>
            <div className="gb-summary-copy">Only open pull requests appear in the bot workspace for the selected repository.</div>
          </div>
          <div className="gb-summary-card">
            <div className="gb-summary-label">active repository</div>
            <div className="gb-summary-value gb-summary-value-small">{selected_repository_card?.review_mode ?? "manual review"}</div>
            <div className="gb-summary-copy">Current selection: {selected_repository_card?.name ?? "No repository selected"}</div>
          </div>
        </div>

        <div className="gb-main-grid">
          <div className="gb-panel">
            <div className="gb-panel-top">
              <div>
                <div className="gb-panel-label">repositories</div>
                <div className="gb-panel-title">Connected repositories</div>
              </div>
              <Github className="gb-panel-icon" />
            </div>
            <div className="gb-panel-copy">
              Choose where the GitHub bot should be active. Repository settings control whether reviews stay manual or become automatic.
            </div>
            <div className="gb-repo-list">
              {repositories.map((repository) => (
                <button
                  key={repository.name}
                  type="button"
                  className={`gb-repo-card ${selected_repository === repository.name ? "gb-repo-card-active" : ""}`}
                  onClick={() => set_selected_repository(repository.name)}
                >
                  <div className="gb-repo-top">
                    <div>
                      <div className="gb-repo-name">{repository.name}</div>
                      <div className="gb-repo-meta">{repository.open_prs} open PRs</div>
                    </div>
                    <span className={repo_state_class(repository.state)}>{repository.review_mode}</span>
                  </div>
                  <div className="gb-repo-copy">{repository.summary}</div>
                  <div className="gb-repo-actions">
                    <span className="history-action history-action-primary">Selected repository</span>
                    <span className="history-action">Adjust settings</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="gb-panel">
            <div className="gb-panel-top">
              <div>
                <div className="gb-panel-label">pull requests</div>
                <div className="gb-panel-title">Open pull requests ready for review</div>
              </div>
              <GitPullRequest className="gb-panel-icon" />
            </div>
            <div className="gb-panel-copy">
              Users should only see open pull requests here. The manual trigger path starts from this queue, not from closed or merged work.
            </div>
            <div className="gb-pr-list">
              {filtered_pull_requests.map((pull_request) => (
                <div key={`${pull_request.repo}-${pull_request.number}`} className="gb-pr-card">
                  <div className="gb-pr-top">
                    <div>
                      <div className="gb-pr-repo">{pull_request.repo} #{pull_request.number}</div>
                      <div className="gb-pr-title">{pull_request.title}</div>
                    </div>
                    <span className="gb-pr-updated">{pull_request.updated}</span>
                  </div>
                  <div className="gb-pr-summary">{pull_request.summary}</div>
                  <div className="gb-pr-footer">
                    <span className="gb-pr-mode">{pull_request.mode}</span>
                    <button type="button" className="history-action history-action-primary">Review now</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="gb-support-grid">
          <div className="gb-panel">
            <div className="gb-panel-top">
              <div>
                <div className="gb-panel-label">automation</div>
                <div className="gb-panel-title">Review modes</div>
              </div>
              <Bot className="gb-panel-icon" />
            </div>
            <div className="gb-mode-list">
              {automation_modes.map((mode) => (
                <div key={mode.title} className="gb-mode-card">
                  <div className="gb-mode-title">{mode.title}</div>
                  <div className="gb-mode-copy">{mode.detail}</div>
                  <div className="gb-mode-toggle-row">
                    <span className="gb-mode-status">Available in repo settings</span>
                    <span className="gb-mode-toggle">Toggle</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="gb-panel">
            <div className="gb-panel-top">
              <div>
                <div className="gb-panel-label">activity</div>
                <div className="gb-panel-title">Bot status snapshot</div>
              </div>
              <History className="gb-panel-icon" />
            </div>
            <div className="gb-activity-list">
              {activity_items.map((activity_item) => (
                <div key={activity_item} className="gb-activity-item">
                  <CheckCircle2 className="gb-activity-icon" />
                  <span>{activity_item}</span>
                </div>
              ))}
            </div>
            <div className="gb-panel-callout">
              <Sparkles className="gb-callout-icon" />
              <div>
                <div className="gb-callout-title">Next backend slice</div>
                <div className="gb-callout-copy">Wire this screen to real repository, open PR, and automation-setting APIs.</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
