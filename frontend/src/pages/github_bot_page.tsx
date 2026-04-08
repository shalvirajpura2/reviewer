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

type RepositorySettings = {
  manual_review: boolean;
  automatic_review: boolean;
  review_new_pushes: boolean;
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

const initial_settings: Record<string, RepositorySettings> = {
  "shalvirajpura2/reviewer": {
    manual_review: true,
    automatic_review: true,
    review_new_pushes: true,
  },
  "shalvirajpura2/reviewer-docs": {
    manual_review: true,
    automatic_review: false,
    review_new_pushes: false,
  },
};

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
    key: "manual_review",
    title: "Manual Review",
    detail: "Pick one open pull request and ask Reviewer to post a summary right now.",
  },
  {
    key: "automatic_review",
    title: "Automatic Review",
    detail: "Post a Reviewer summary automatically whenever a new pull request opens.",
  },
  {
    key: "review_new_pushes",
    title: "Review New Pushes",
    detail: "Re-run the summary when additional commits are pushed to the same open pull request.",
  },
] as const;

const activity_items = [
  "Last bot summary posted 6 minutes ago on reviewer#18",
  "Automatic review is enabled on 1 repository",
  "Review New Pushes is enabled on 2 open pull requests",
];

const setup_steps = [
  "Install the Reviewer GitHub App on the repository you want to manage.",
  "Choose one connected repository and inspect only its open pull requests.",
  "Trigger a manual review now or turn on automation for future pull requests.",
];

function repo_state_class(state: RepositoryCard["state"]) {
  if (state === "installed") {
    return "gb-state gb-state-live";
  }

  return "gb-state gb-state-manual";
}

function mode_copy(settings: RepositorySettings) {
  if (settings.automatic_review && settings.review_new_pushes) {
    return "automatic review";
  }

  if (settings.automatic_review) {
    return "automatic review";
  }

  return "manual review";
}

export function GithubBotPage() {
  const [selected_repository, set_selected_repository] = useState(repositories[0]?.name ?? "");
  const [selected_pull_request, set_selected_pull_request] = useState<number | null>(null);
  const [queued_pull_request, set_queued_pull_request] = useState<number | null>(null);
  const [repo_settings, set_repo_settings] = useState<Record<string, RepositorySettings>>(initial_settings);

  const filtered_pull_requests = useMemo(
    () => open_pull_requests.filter((pull_request) => pull_request.repo === selected_repository),
    [selected_repository]
  );

  const selected_repository_card = repositories.find((repository) => repository.name === selected_repository) ?? repositories[0];
  const selected_repository_settings = repo_settings[selected_repository] ?? initial_settings[selected_repository];
  const selected_pull_request_card = filtered_pull_requests.find((pull_request) => pull_request.number === selected_pull_request) ?? filtered_pull_requests[0] ?? null;

  function toggle_setting(setting_key: keyof RepositorySettings) {
    set_repo_settings((current) => ({
      ...current,
      [selected_repository]: {
        ...(current[selected_repository] ?? initial_settings[selected_repository]),
        [setting_key]: !(current[selected_repository] ?? initial_settings[selected_repository])[setting_key],
      },
    }));
  }

  function queue_manual_review(pull_request_number: number) {
    set_selected_pull_request(pull_request_number);
    set_queued_pull_request(pull_request_number);
  }

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
            <div className="gb-summary-value gb-summary-value-small">{mode_copy(selected_repository_settings)}</div>
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
              {repositories.map((repository) => {
                const repository_settings = repo_settings[repository.name] ?? initial_settings[repository.name];

                return (
                  <button
                    key={repository.name}
                    type="button"
                    className={`gb-repo-card ${selected_repository === repository.name ? "gb-repo-card-active" : ""}`}
                    onClick={() => {
                      set_selected_repository(repository.name);
                      set_selected_pull_request(null);
                      set_queued_pull_request(null);
                    }}
                  >
                    <div className="gb-repo-top">
                      <div>
                        <div className="gb-repo-name">{repository.name}</div>
                        <div className="gb-repo-meta">{repository.open_prs} open PRs</div>
                      </div>
                      <span className={repo_state_class(repository.state)}>{mode_copy(repository_settings)}</span>
                    </div>
                    <div className="gb-repo-copy">{repository.summary}</div>
                    <div className="gb-repo-actions">
                      <span className="history-action history-action-primary">Selected repository</span>
                      <span className="history-action">Adjust settings</span>
                    </div>
                  </button>
                );
              })}
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
                <button
                  key={`${pull_request.repo}-${pull_request.number}`}
                  type="button"
                  className={`gb-pr-card ${selected_pull_request_card?.number === pull_request.number ? "gb-pr-card-active" : ""}`}
                  onClick={() => set_selected_pull_request(pull_request.number)}
                >
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
                    <button type="button" className="history-action history-action-primary gb-inline-action" onClick={() => queue_manual_review(pull_request.number)}>
                      Review now
                    </button>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="gb-support-grid">
          <div className="gb-panel">
            <div className="gb-panel-top">
              <div>
                <div className="gb-panel-label">automation</div>
                <div className="gb-panel-title">Repository review settings</div>
              </div>
              <Bot className="gb-panel-icon" />
            </div>
            <div className="gb-panel-copy">
              These toggles should be stored per repository. For now, they update the UI state so the product behavior is understandable before we wire the backend settings API.
            </div>
            <div className="gb-settings-grid">
              {automation_modes.map((mode) => {
                const setting_key = mode.key;
                const is_enabled = selected_repository_settings?.[setting_key] ?? false;

                return (
                  <div key={mode.title} className={`gb-mode-card ${is_enabled ? "gb-mode-card-active" : ""}`}>
                    <div className="gb-mode-title">{mode.title}</div>
                    <div className="gb-mode-copy">{mode.detail}</div>
                    <div className="gb-mode-toggle-row">
                      <span className="gb-mode-status">{is_enabled ? "Enabled on this repository" : "Disabled on this repository"}</span>
                      <button type="button" className={`gb-toggle-button ${is_enabled ? "gb-toggle-button-active" : ""}`} onClick={() => toggle_setting(setting_key)}>
                        {is_enabled ? "On" : "Off"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="gb-panel">
            <div className="gb-panel-top">
              <div>
                <div className="gb-panel-label">setup</div>
                <div className="gb-panel-title">Bot setup and repository status</div>
              </div>
              <CheckCircle2 className="gb-panel-icon" />
            </div>
            <div className="gb-status-stack">
              <div className="gb-focus-card">
                <div className="gb-focus-label">Install status</div>
                <div className="gb-focus-title">GitHub App connected</div>
                <div className="gb-focus-copy">
                  Reviewer is already installed for {selected_repository_card?.name}, so this repository can use Manual Review, Automatic Review, and Review New Pushes.
                </div>
              </div>
              <div className="gb-focus-card gb-focus-card-secondary">
                <div className="gb-focus-label">What happens next</div>
                <div className="gb-step-list">
                  {setup_steps.map((step, index) => (
                    <div key={step} className="gb-step-item">
                      <span className="gb-step-number">{index + 1}</span>
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="gb-panel">
            <div className="gb-panel-top">
              <div>
                <div className="gb-panel-label">selection</div>
                <div className="gb-panel-title">Current bot focus</div>
              </div>
              <History className="gb-panel-icon" />
            </div>
            <div className="gb-focus-card">
              <div className="gb-focus-label">Repository</div>
              <div className="gb-focus-title">{selected_repository_card?.name}</div>
              <div className="gb-focus-copy">{selected_repository_card?.summary}</div>
              <div className="gb-focus-row">
                <span className="gb-pr-mode">{mode_copy(selected_repository_settings)}</span>
                <span className="gb-mode-status">{filtered_pull_requests.length} open PRs available</span>
              </div>
            </div>
            {selected_pull_request_card ? (
              <div className="gb-focus-card gb-focus-card-secondary">
                <div className="gb-focus-label">Selected pull request</div>
                <div className="gb-focus-title">{selected_pull_request_card.title}</div>
                <div className="gb-focus-copy">{selected_pull_request_card.summary}</div>
                <div className="gb-focus-row">
                  <span className="gb-pr-mode">{selected_pull_request_card.mode}</span>
                  <span className="gb-mode-status">Updated {selected_pull_request_card.updated}</span>
                </div>
                <div className="gb-focus-actions">
                  <button type="button" className="history-action history-action-primary gb-inline-action" onClick={() => queue_manual_review(selected_pull_request_card.number)}>
                    Review now
                  </button>
                  <span className="history-action">Manual Review</span>
                </div>
              </div>
            ) : null}
            {selected_pull_request_card && queued_pull_request === selected_pull_request_card.number ? (
              <div className="gb-panel-callout gb-panel-callout-queued">
                <Sparkles className="gb-callout-icon" />
                <div>
                  <div className="gb-callout-title">Manual review queued</div>
                  <div className="gb-callout-copy">
                    Reviewer is ready to post a GitHub summary for {selected_pull_request_card.repo} #{selected_pull_request_card.number}. This will map cleanly to the backend manual trigger in the next slice.
                  </div>
                </div>
              </div>
            ) : null}
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

