import { Bot, CheckCircle2, Github, GitPullRequest, History, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { SiteFooter } from "../components/site_footer";
import {
  get_backend_health,
  get_github_bot_pull_requests,
  get_github_bot_repositories,
  trigger_github_bot_review,
  update_github_bot_settings,
} from "../lib/api";
import type { BackendHealth } from "../lib/api";
import type { GithubBotPullRequestSummary, GithubBotRepositorySettings, GithubBotRepositorySummary } from "../types/github_bot";

const default_repository_settings: GithubBotRepositorySettings = {
  manual_review: true,
  automatic_review: false,
  review_new_pushes: false,
};

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

const setup_steps = [
  "Install the Reviewer GitHub App on the repository you want to manage.",
  "Choose one connected repository and inspect only its open pull requests.",
  "Trigger a manual review now or turn on automation for future pull requests.",
];

function repo_state_class(app_installed: boolean) {
  if (app_installed) {
    return "gb-state gb-state-live";
  }

  return "gb-state gb-state-manual";
}

function mode_copy(settings: GithubBotRepositorySettings) {
  if (settings.automatic_review && settings.review_new_pushes) {
    return "review new pushes";
  }

  if (settings.automatic_review) {
    return "automatic review";
  }

  return "manual review";
}

function format_mode_label(mode: string) {
  return mode.split("_").join(" ");
}

function format_updated_label(updated_at: string) {
  if (!updated_at) {
    return "just now";
  }

  const parsed_date = new Date(updated_at);
  if (Number.isNaN(parsed_date.getTime())) {
    return updated_at;
  }

  return parsed_date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function repository_summary(repository: GithubBotRepositorySummary, settings: GithubBotRepositorySettings) {
  if (repository.open_pull_requests === 0) {
    return `${repository.full_name} is connected, but there are no open pull requests waiting for Reviewer right now.`;
  }

  if (settings.automatic_review && settings.review_new_pushes) {
    return "Reviewer is installed and will post summaries on new pull requests and on new pushes to the same PR.";
  }

  if (settings.automatic_review) {
    return "Reviewer is installed and will post a summary automatically whenever a new pull request opens.";
  }

  return "Keep the bot quiet by default, then trigger a single review when a pull request needs a deeper pass.";
}

export function GithubBotPage() {
  const [repositories, set_repositories] = useState<GithubBotRepositorySummary[]>([]);
  const [selected_repository, set_selected_repository] = useState("");
  const [pull_requests, set_pull_requests] = useState<GithubBotPullRequestSummary[]>([]);
  const [selected_pull_request, set_selected_pull_request] = useState<number | null>(null);
  const [queued_pull_request, set_queued_pull_request] = useState<number | null>(null);
  const [repo_settings, set_repo_settings] = useState<Record<string, GithubBotRepositorySettings>>({});
  const [backend_health, set_backend_health] = useState<BackendHealth | null>(null);
  const [is_loading_repositories, set_is_loading_repositories] = useState(true);
  const [is_loading_pull_requests, set_is_loading_pull_requests] = useState(false);
  const [is_saving_settings, set_is_saving_settings] = useState(false);
  const [is_triggering_review, set_is_triggering_review] = useState(false);
  const [surface_error, set_surface_error] = useState<string | null>(null);
  const [surface_feedback, set_surface_feedback] = useState<string | null>(null);

  useEffect(() => {
    const request_controller = new AbortController();

    async function load_repositories() {
      set_is_loading_repositories(true);
      set_surface_error(null);

      try {
        const [repository_response, health_response] = await Promise.all([
          get_github_bot_repositories(request_controller.signal),
          get_backend_health(),
        ]);
        set_repositories(repository_response.repositories);
        set_repo_settings(Object.fromEntries(repository_response.repositories.map((repository) => [repository.full_name, repository.settings])));
        set_backend_health(health_response);
        set_selected_repository((current) => {
          if (current && repository_response.repositories.some((repository) => repository.full_name === current)) {
            return current;
          }

          return repository_response.repositories[0]?.full_name ?? "";
        });
      } catch (error) {
        if (request_controller.signal.aborted) {
          return;
        }

        set_surface_error(error instanceof Error ? error.message : "Reviewer could not load connected GitHub repositories.");
      } finally {
        if (!request_controller.signal.aborted) {
          set_is_loading_repositories(false);
        }
      }
    }

    void load_repositories();

    return () => {
      request_controller.abort();
    };
  }, []);

  useEffect(() => {
    if (!selected_repository) {
      set_pull_requests([]);
      set_selected_pull_request(null);
      return;
    }

    const selected_repository_card = repositories.find((repository) => repository.full_name === selected_repository);
    if (!selected_repository_card) {
      return;
    }

    const repository_owner = selected_repository_card.owner;
    const repository_name = selected_repository_card.repo;
    const repository_key = selected_repository_card.full_name;
    const request_controller = new AbortController();

    async function load_pull_requests() {
      set_is_loading_pull_requests(true);
      set_surface_error(null);
      set_surface_feedback(null);
      set_queued_pull_request(null);

      try {
        const response = await get_github_bot_pull_requests(repository_owner, repository_name, request_controller.signal);
        set_pull_requests(response.pull_requests);
        set_repo_settings((current) => ({
          ...current,
          [repository_key]: response.repository.settings,
        }));
        set_repositories((current) =>
          current.map((repository) =>
            repository.full_name === response.repository.full_name ? response.repository : repository,
          ),
        );
        set_selected_pull_request((current) => {
          if (current && response.pull_requests.some((pull_request) => pull_request.number === current)) {
            return current;
          }

          return response.pull_requests[0]?.number ?? null;
        });
      } catch (error) {
        if (request_controller.signal.aborted) {
          return;
        }

        set_pull_requests([]);
        set_selected_pull_request(null);
        set_surface_error(error instanceof Error ? error.message : "Reviewer could not load open pull requests for that repository.");
      } finally {
        if (!request_controller.signal.aborted) {
          set_is_loading_pull_requests(false);
        }
      }
    }

    void load_pull_requests();

    return () => {
      request_controller.abort();
    };
  }, [selected_repository]);

  const selected_repository_card = useMemo(
    () => repositories.find((repository) => repository.full_name === selected_repository) ?? null,
    [repositories, selected_repository],
  );

  const selected_repository_settings = selected_repository_card
    ? (repo_settings[selected_repository_card.full_name] ?? selected_repository_card.settings)
    : default_repository_settings;

  const selected_pull_request_card = useMemo(
    () => pull_requests.find((pull_request) => pull_request.number === selected_pull_request) ?? pull_requests[0] ?? null,
    [pull_requests, selected_pull_request],
  );

  const automation_ready = Boolean(backend_health?.github_app_configured && backend_health?.github_webhook_configured);

  const activity_items = useMemo(() => {
    const automatic_repository_count = repositories.filter((repository) => {
      const settings = repo_settings[repository.full_name] ?? repository.settings;
      return settings.automatic_review;
    }).length;
    const push_repository_count = repositories.filter((repository) => {
      const settings = repo_settings[repository.full_name] ?? repository.settings;
      return settings.review_new_pushes;
    }).length;

    return [
      `${repositories.length} connected repositories available for the bot workspace`,
      `${automatic_repository_count} repositories currently have Automatic Review enabled`,
      `${push_repository_count} repositories currently re-run reviews on new pushes`,
      automation_ready ? "Backend webhook automation is live for connected repositories" : "Backend webhook automation still needs final setup",
    ];
  }, [automation_ready, repo_settings, repositories]);

  async function handle_toggle(setting_key: keyof GithubBotRepositorySettings) {
    if (!selected_repository_card || is_saving_settings) {
      return;
    }

    const next_settings = {
      ...selected_repository_settings,
      [setting_key]: !selected_repository_settings[setting_key],
    };
    const repository_key = selected_repository_card.full_name;
    const previous_settings = selected_repository_settings;

    set_is_saving_settings(true);
    set_surface_error(null);
    set_surface_feedback(null);
    set_repo_settings((current) => ({
      ...current,
      [repository_key]: next_settings,
    }));
    set_repositories((current) =>
      current.map((repository) =>
        repository.full_name === repository_key ? { ...repository, settings: next_settings } : repository,
      ),
    );

    try {
      const saved_settings = await update_github_bot_settings(
        selected_repository_card.owner,
        selected_repository_card.repo,
        next_settings,
      );
      set_repo_settings((current) => ({
        ...current,
        [repository_key]: saved_settings,
      }));
      set_repositories((current) =>
        current.map((repository) =>
          repository.full_name === repository_key ? { ...repository, settings: saved_settings } : repository,
        ),
      );
      set_surface_feedback(`Saved ${mode_copy(saved_settings)} settings for ${selected_repository_card.full_name}.`);
    } catch (error) {
      set_repo_settings((current) => ({
        ...current,
        [repository_key]: previous_settings,
      }));
      set_repositories((current) =>
        current.map((repository) =>
          repository.full_name === repository_key ? { ...repository, settings: previous_settings } : repository,
        ),
      );
      set_surface_error(error instanceof Error ? error.message : "Reviewer could not save repository review settings.");
    } finally {
      set_is_saving_settings(false);
    }
  }

  async function handle_review_now(pull_request_number: number) {
    if (!selected_repository_card || is_triggering_review) {
      return;
    }

    set_selected_pull_request(pull_request_number);
    set_queued_pull_request(pull_request_number);
    set_is_triggering_review(true);
    set_surface_error(null);
    set_surface_feedback(null);

    try {
      const publication = await trigger_github_bot_review(
        selected_repository_card.owner,
        selected_repository_card.repo,
        pull_request_number,
      );
      set_surface_feedback(
        publication.action === "updated"
          ? `Reviewer updated the GitHub summary on ${selected_repository_card.full_name} #${pull_request_number}.`
          : `Reviewer posted a new GitHub summary on ${selected_repository_card.full_name} #${pull_request_number}.`,
      );
    } catch (error) {
      set_surface_error(error instanceof Error ? error.message : "Reviewer could not trigger a manual GitHub review.");
    } finally {
      set_is_triggering_review(false);
    }
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
        {surface_error ? <div className="gb-surface-message gb-surface-error">{surface_error}</div> : null}
        {surface_feedback ? <div className="gb-surface-message gb-surface-success">{surface_feedback}</div> : null}

        <div className="gb-summary-grid">
          <div className="gb-summary-card">
            <div className="gb-summary-label">connected repositories</div>
            <div className="gb-summary-value">{is_loading_repositories ? "..." : repositories.length}</div>
            <div className="gb-summary-copy">Repositories where the Reviewer app is already available.</div>
          </div>
          <div className="gb-summary-card">
            <div className="gb-summary-label">open pull requests</div>
            <div className="gb-summary-value">{is_loading_pull_requests ? "..." : pull_requests.length}</div>
            <div className="gb-summary-copy">Only open pull requests appear in the bot workspace for the selected repository.</div>
          </div>
          <div className="gb-summary-card">
            <div className="gb-summary-label">automation status</div>
            <div className="gb-summary-value gb-summary-value-small">{backend_health ? (automation_ready ? "live" : "partial") : "checking"}</div>
            <div className="gb-summary-copy">{automation_ready ? "GitHub App publish and webhook automation are configured." : "Repository settings are available, but backend automation still needs final setup."}</div>
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
            {is_loading_repositories ? <div className="gb-panel-note">Loading connected repositories...</div> : null}
            {!is_loading_repositories && repositories.length === 0 ? (
              <div className="gb-empty-state">
                <div className="gb-empty-title">No connected repositories yet</div>
                <div className="gb-empty-copy">Install the Reviewer GitHub App, then come back here to manage repositories, open pull requests, and automation settings.</div>
                <div className="gb-empty-actions">
                  <a href="https://github.com/apps/reviewer-live" target="_blank" rel="noreferrer" className="history-action history-action-primary">
                    Install GitHub App
                  </a>
                </div>
              </div>
            ) : null}
            <div className="gb-repo-list">
              {repositories.map((repository) => {
                const repository_settings = repo_settings[repository.full_name] ?? repository.settings;

                return (
                  <button
                    key={repository.full_name}
                    type="button"
                    className={`gb-repo-card ${selected_repository === repository.full_name ? "gb-repo-card-active" : ""}`}
                    onClick={() => {
                      set_selected_repository(repository.full_name);
                      set_selected_pull_request(null);
                      set_queued_pull_request(null);
                      set_surface_feedback(null);
                    }}
                  >
                    <div className="gb-repo-top">
                      <div>
                        <div className="gb-repo-name">{repository.full_name}</div>
                        <div className="gb-repo-meta">{repository.open_pull_requests} open PRs</div>
                      </div>
                      <span className={repo_state_class(repository.app_installed)}>{mode_copy(repository_settings)}</span>
                    </div>
                    <div className="gb-repo-copy">{repository_summary(repository, repository_settings)}</div>
                    <div className="gb-repo-actions">
                      <span className="history-action history-action-primary">Selected repository</span>
                      <span className="history-action">{repository.default_branch}</span>
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
            {is_loading_pull_requests ? <div className="gb-panel-note">Loading open pull requests...</div> : null}
            <div className="gb-pr-list">
              {!is_loading_pull_requests && pull_requests.length > 0
                ? pull_requests.map((pull_request) => (
                    <button
                      key={`${selected_repository}-${pull_request.number}`}
                      type="button"
                      className={`gb-pr-card ${selected_pull_request_card?.number === pull_request.number ? "gb-pr-card-active" : ""}`}
                      onClick={() => set_selected_pull_request(pull_request.number)}
                    >
                      <div className="gb-pr-top">
                        <div>
                          <div className="gb-pr-repo">{selected_repository_card?.full_name} #{pull_request.number}</div>
                          <div className="gb-pr-title">{pull_request.title}</div>
                        </div>
                        <span className="gb-pr-updated">{format_updated_label(pull_request.updated_at)}</span>
                      </div>
                      <div className="gb-pr-summary">
                        {pull_request.author} opened this PR from {pull_request.head_branch} into {pull_request.base_branch}.
                      </div>
                      <div className="gb-pr-footer">
                        <span className="gb-pr-mode">{format_mode_label(pull_request.mode)}</span>
                        <button
                          type="button"
                          className="history-action history-action-primary gb-inline-action"
                          onClick={() => void handle_review_now(pull_request.number)}
                          disabled={is_triggering_review}
                        >
                          {is_triggering_review && queued_pull_request === pull_request.number ? "Reviewing..." : "Review now"}
                        </button>
                      </div>
                    </button>
                  ))
                : null}
              {!is_loading_pull_requests && selected_repository_card && pull_requests.length === 0 ? (
                <div className="gb-empty-state">
                  <div className="gb-empty-title">No open pull requests</div>
                  <div className="gb-empty-copy">
                    {selected_repository_card.full_name} is connected, but there is nothing for the bot to review right now. When a new pull request opens, it will appear here for manual or automatic review.
                  </div>
                  <div className="gb-empty-actions">
                    <span className="history-action history-action-primary">Repository connected</span>
                    <span className="history-action">Waiting for open PRs</span>
                  </div>
                </div>
              ) : null}
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
              These toggles are backed by the bot-management API and will drive webhook automation when the backend is fully configured.
            </div>
            <div className="gb-settings-grid">
              {automation_modes.map((mode) => {
                const setting_key = mode.key;
                const is_enabled = selected_repository_settings[setting_key];

                return (
                  <div key={mode.title} className={`gb-mode-card ${is_enabled ? "gb-mode-card-active" : ""}`}>
                    <div className="gb-mode-title">{mode.title}</div>
                    <div className="gb-mode-copy">{mode.detail}</div>
                    <div className="gb-mode-toggle-row">
                      <span className="gb-mode-status">{is_enabled ? "Enabled on this repository" : "Disabled on this repository"}</span>
                      <button
                        type="button"
                        className={`gb-toggle-button ${is_enabled ? "gb-toggle-button-active" : ""}`}
                        onClick={() => void handle_toggle(setting_key)}
                        disabled={!selected_repository_card || is_saving_settings}
                      >
                        {is_saving_settings ? "..." : is_enabled ? "On" : "Off"}
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
                <div className="gb-panel-title">Bot setup and automation status</div>
              </div>
              <CheckCircle2 className="gb-panel-icon" />
            </div>
            <div className="gb-status-stack">
              <div className="gb-focus-card">
                <div className="gb-focus-label">Install status</div>
                <div className="gb-focus-title">{selected_repository_card ? "GitHub App connected" : "Waiting for repositories"}</div>
                <div className="gb-focus-copy">
                  {selected_repository_card
                    ? `Reviewer is installed for ${selected_repository_card.full_name}, so this repository can use Manual Review, Automatic Review, and Review New Pushes.`
                    : "Install the GitHub App on at least one repository to unlock the bot workspace."}
                </div>
                <div className="gb-focus-row">
                  <span className={repo_state_class(automation_ready)}>{automation_ready ? "automation live" : "webhook setup needed"}</span>
                  <span className="gb-mode-status">{backend_health ? `uptime ${backend_health.uptime_seconds}s` : "checking backend health"}</span>
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
              <div className="gb-focus-title">{selected_repository_card?.full_name ?? "No repository selected"}</div>
              <div className="gb-focus-copy">
                {selected_repository_card
                  ? repository_summary(selected_repository_card, selected_repository_settings)
                  : "Choose a connected repository to view open pull requests and bot settings."}
              </div>
              <div className="gb-focus-row">
                <span className="gb-pr-mode">{mode_copy(selected_repository_settings)}</span>
                <span className="gb-mode-status">{selected_repository_card?.open_pull_requests ?? 0} open PRs available</span>
              </div>
            </div>
            {selected_pull_request_card ? (
              <div className="gb-focus-card gb-focus-card-secondary">
                <div className="gb-focus-label">Selected pull request</div>
                <div className="gb-focus-title">{selected_pull_request_card.title}</div>
                <div className="gb-focus-copy">
                  {selected_pull_request_card.author} opened this PR from {selected_pull_request_card.head_branch} into {selected_pull_request_card.base_branch}.
                </div>
                <div className="gb-focus-row">
                  <span className="gb-pr-mode">{format_mode_label(selected_pull_request_card.mode)}</span>
                  <span className="gb-mode-status">Updated {format_updated_label(selected_pull_request_card.updated_at)}</span>
                </div>
                <div className="gb-focus-actions">
                  <button
                    type="button"
                    className="history-action history-action-primary gb-inline-action"
                    onClick={() => void handle_review_now(selected_pull_request_card.number)}
                    disabled={is_triggering_review}
                  >
                    {is_triggering_review && queued_pull_request === selected_pull_request_card.number ? "Reviewing..." : "Review now"}
                  </button>
                  <a href={selected_pull_request_card.html_url} target="_blank" rel="noreferrer" className="history-action">
                    Open PR
                  </a>
                </div>
              </div>
            ) : null}
            {selected_pull_request_card && queued_pull_request === selected_pull_request_card.number && surface_feedback ? (
              <div className="gb-panel-callout gb-panel-callout-queued">
                <Sparkles className="gb-callout-icon" />
                <div>
                  <div className="gb-callout-title">Manual review sent</div>
                  <div className="gb-callout-copy">{surface_feedback}</div>
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
                <div className="gb-callout-title">Automation status</div>
                <div className="gb-callout-copy">{automation_ready ? "Automatic Review and Review New Pushes can now be driven by GitHub webhooks." : "Finish backend webhook setup to turn saved repository automation settings into live bot behavior."}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
