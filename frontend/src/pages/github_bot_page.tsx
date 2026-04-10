import { Bot, CheckCircle2, Github, GitPullRequest, History, LogOut, Rocket, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { SiteFooter } from "../components/site_footer";
import {
  build_github_auth_start_url,
  get_backend_health,
  get_github_bot_pull_requests,
  get_github_bot_repositories,
  get_github_web_session,
  logout_github_web_session,
  trigger_github_bot_review,
  update_github_bot_settings,
} from "../lib/api";
import type { BackendHealth, GithubWebSession } from "../lib/api";
import type { GithubBotPullRequestSummary, GithubBotRepositorySettings, GithubBotRepositorySummary } from "../types/github_bot";

const default_repository_settings: GithubBotRepositorySettings = {
  manual_review: true,
  automatic_review: false,
  review_new_pushes: false,
};

const onboarding_storage_key = "reviewer_bot_onboarding_v1";

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

const onboarding_modes = [
  {
    key: "manual",
    title: "Manual Review",
    detail: "Choose a PR when you want Reviewer to step in and publish a summary.",
  },
  {
    key: "automatic",
    title: "Automatic Review",
    detail: "Post a summary automatically whenever a new pull request opens.",
  },
  {
    key: "pushes",
    title: "Review New Pushes",
    detail: "Keep Reviewer live on the same PR when additional commits are pushed.",
  },
] as const;

const setup_steps = [
  "Install the Reviewer GitHub App on the repository you want to manage.",
  "Choose one repository and inspect only its open pull requests.",
  "Trigger a manual review now or turn on automation for future pull requests.",
];

type OnboardingModeKey = (typeof onboarding_modes)[number]["key"];

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

function mode_label(settings: GithubBotRepositorySettings) {
  if (settings.automatic_review && settings.review_new_pushes) {
    return "Auto + pushes";
  }

  if (settings.automatic_review) {
    return "Automatic";
  }

  return "Manual";
}

function format_mode_label(mode: string) {
  return mode.split("_").join(" ");
}

function format_trigger_label(trigger: string) {
  if (!trigger) {
    return "manual review";
  }

  return format_mode_label(trigger);
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

function onboarding_settings(mode: OnboardingModeKey): GithubBotRepositorySettings {
  if (mode === "pushes") {
    return {
      manual_review: true,
      automatic_review: true,
      review_new_pushes: true,
    };
  }

  if (mode === "automatic") {
    return {
      manual_review: true,
      automatic_review: true,
      review_new_pushes: false,
    };
  }

  return default_repository_settings;
}

function onboarding_mode_from_settings(settings: GithubBotRepositorySettings): OnboardingModeKey {
  if (settings.automatic_review && settings.review_new_pushes) {
    return "pushes";
  }

  if (settings.automatic_review) {
    return "automatic";
  }

  return "manual";
}

function read_onboarding_repository(login: string) {
  if (typeof window === "undefined") {
    return "";
  }

  try {
    const raw_value = window.sessionStorage.getItem(onboarding_storage_key);
    if (!raw_value) {
      return "";
    }

    const parsed_value = JSON.parse(raw_value) as { login?: string; repository?: string };
    if (parsed_value.login !== login) {
      return "";
    }

    return parsed_value.repository ?? "";
  } catch {
    return "";
  }
}

function save_onboarding_repository(login: string, repository: string) {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.setItem(
    onboarding_storage_key,
    JSON.stringify({
      login,
      repository,
    }),
  );
}

export function GithubBotPage() {
  const [repositories, set_repositories] = useState<GithubBotRepositorySummary[]>([]);
  const [selected_repository, set_selected_repository] = useState("");
  const [pull_requests, set_pull_requests] = useState<GithubBotPullRequestSummary[]>([]);
  const [selected_pull_request, set_selected_pull_request] = useState<number | null>(null);
  const [queued_pull_request, set_queued_pull_request] = useState<number | null>(null);
  const [repo_settings, set_repo_settings] = useState<Record<string, GithubBotRepositorySettings>>({});
  const [backend_health, set_backend_health] = useState<BackendHealth | null>(null);
  const [auth_session, set_auth_session] = useState<GithubWebSession | null>(null);
  const [is_loading_session, set_is_loading_session] = useState(true);
  const [is_loading_repositories, set_is_loading_repositories] = useState(false);
  const [is_loading_pull_requests, set_is_loading_pull_requests] = useState(false);
  const [is_saving_settings, set_is_saving_settings] = useState(false);
  const [is_triggering_review, set_is_triggering_review] = useState(false);
  const [is_applying_onboarding, set_is_applying_onboarding] = useState(false);
  const [is_signing_out, set_is_signing_out] = useState(false);
  const [onboarding_complete, set_onboarding_complete] = useState(false);
  const [onboarding_mode, set_onboarding_mode] = useState<OnboardingModeKey>("manual");
  const [surface_error, set_surface_error] = useState<string | null>(null);
  const [surface_feedback, set_surface_feedback] = useState<string | null>(null);

  useEffect(() => {
    const request_controller = new AbortController();

    async function load_surface() {
      set_is_loading_session(true);
      set_surface_error(null);

      try {
        const [session_response, health_response] = await Promise.all([
          get_github_web_session(request_controller.signal),
          get_backend_health(),
        ]);
        set_auth_session(session_response);
        set_backend_health(health_response);
      } catch (error) {
        if (request_controller.signal.aborted) {
          return;
        }

        set_surface_error(error instanceof Error ? error.message : "Reviewer could not load the GitHub bot dashboard.");
      } finally {
        if (!request_controller.signal.aborted) {
          set_is_loading_session(false);
        }
      }
    }

    void load_surface();

    return () => {
      request_controller.abort();
    };
  }, []);

  useEffect(() => {
    if (!auth_session?.authenticated) {
      set_repositories([]);
      set_pull_requests([]);
      set_selected_repository("");
      set_selected_pull_request(null);
      set_onboarding_complete(false);
      return;
    }

    const request_controller = new AbortController();

    async function load_repositories() {
      set_is_loading_repositories(true);
      set_surface_error(null);

      try {
        const repository_response = await get_github_bot_repositories(request_controller.signal);
        const repository_list = repository_response.repositories;
        const saved_repository = read_onboarding_repository(auth_session?.login ?? "");
        const initial_repository =
          (saved_repository && repository_list.some((repository) => repository.full_name === saved_repository) ? saved_repository : "") ||
          repository_list[0]?.full_name ||
          "";
        const initial_settings =
          repository_list.find((repository) => repository.full_name === initial_repository)?.settings ?? default_repository_settings;

        set_repositories(repository_list);
        set_repo_settings(Object.fromEntries(repository_list.map((repository) => [repository.full_name, repository.settings])));
        set_selected_repository(initial_repository);
        set_onboarding_mode(onboarding_mode_from_settings(initial_settings));
        set_onboarding_complete(Boolean(saved_repository && initial_repository));
      } catch (error) {
        if (request_controller.signal.aborted) {
          return;
        }

        set_surface_error(error instanceof Error ? error.message : "Reviewer could not load the repositories available to your GitHub account.");
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
  }, [auth_session?.authenticated, auth_session?.login]);

  useEffect(() => {
    if (!selected_repository || !auth_session?.authenticated || !onboarding_complete) {
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
  }, [auth_session?.authenticated, onboarding_complete, selected_repository]);

  const selected_repository_card = useMemo(
    () => repositories.find((repository) => repository.full_name === selected_repository) ?? null,
    [repositories, selected_repository],
  );

  const selected_repository_settings = selected_repository_card
    ? (repo_settings[selected_repository_card.full_name] ?? selected_repository_card.settings)
    : default_repository_settings;
  const selected_repository_activity = selected_repository_card?.activity ?? null;

  useEffect(() => {
    if (!selected_repository_card || onboarding_complete) {
      return;
    }

    set_onboarding_mode(onboarding_mode_from_settings(selected_repository_settings));
  }, [onboarding_complete, selected_repository_card, selected_repository_settings]);

  const selected_pull_request_card = useMemo(
    () => pull_requests.find((pull_request) => pull_request.number === selected_pull_request) ?? pull_requests[0] ?? null,
    [pull_requests, selected_pull_request],
  );

  const automation_ready = Boolean(
    backend_health?.github_app_configured
      && backend_health?.github_web_auth_configured
      && backend_health?.github_webhook_configured,
  );

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
      `${repositories.length} repositories visible for your GitHub account`,
      `${automatic_repository_count} repositories currently have Automatic Review enabled`,
      `${push_repository_count} repositories currently re-run reviews on new pushes`,
      automation_ready ? "Backend webhook automation is live for your visible repositories" : "Backend webhook automation still needs final setup",
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
      set_repositories((current) =>
        current.map((repository) =>
          repository.full_name === selected_repository_card.full_name
            ? {
                ...repository,
                activity: {
                  last_review_at: new Date().toISOString(),
                  last_pull_number: pull_request_number,
                  last_trigger: "manual_review",
                  last_action: publication.action,
                  last_comment_url: publication.html_url,
                },
              }
            : repository,
        ),
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

  async function handle_complete_onboarding() {
    if (!selected_repository_card || !auth_session?.authenticated || is_applying_onboarding) {
      return;
    }

    const next_settings = onboarding_settings(onboarding_mode);
    const repository_key = selected_repository_card.full_name;

    set_is_applying_onboarding(true);
    set_surface_error(null);
    set_surface_feedback(null);

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
      save_onboarding_repository(auth_session.login, repository_key);
      set_onboarding_complete(true);
      set_surface_feedback(`Reviewer is ready on ${repository_key} with ${mode_label(saved_settings).toLowerCase()} mode.`);
    } catch (error) {
      set_surface_error(error instanceof Error ? error.message : "Reviewer could not save the bot setup.");
    } finally {
      set_is_applying_onboarding(false);
    }
  }

  async function handle_sign_out() {
    if (is_signing_out) {
      return;
    }

    set_is_signing_out(true);
    set_surface_error(null);
    set_surface_feedback(null);

    try {
      await logout_github_web_session();
      set_auth_session({
        authenticated: false,
        configured: auth_session?.configured ?? Boolean(backend_health?.github_web_auth_configured),
        login: "",
        user_id: 0,
      });
      set_surface_feedback("Disconnected GitHub from the bot dashboard.");
    } catch (error) {
      set_surface_error(error instanceof Error ? error.message : "Reviewer could not disconnect the GitHub dashboard.");
    } finally {
      set_is_signing_out(false);
    }
  }

  if (is_loading_session) {
    return (
      <div className="github-bot-page">
        <section className="github-bot-hero">
          <div className="history-eyebrow">GitHub Review Bot</div>
          <h1 className="history-title">Loading your GitHub bot workspace.</h1>
          <p className="history-copy">Reviewer is checking your GitHub dashboard session and backend readiness.</p>
        </section>
        <section className="gb-grid-shell">
          <div className="gb-empty-state">
            <div className="gb-empty-title">Preparing dashboard</div>
            <div className="gb-empty-copy">This only takes a moment.</div>
          </div>
        </section>
        <SiteFooter />
      </div>
    );
  }

  if (!auth_session?.authenticated) {
    return (
      <div className="github-bot-page">
        <section className="gb-grid-shell">
          <div className="gb-onboarding-shell gb-onboarding-shell-wide">
            <div className="gb-onboarding-hero">
              <span className="gb-pill">GitHub Review Bot</span>
              <h1 className="gb-onboarding-title">Connect GitHub, pick a repo, choose the review mode, then land in the dashboard.</h1>
              <p className="gb-onboarding-copy">
                Reviewer only shows repositories your GitHub account can access and where the app is already installed.
              </p>
              <div className="gb-onboarding-actions">
                <a href={build_github_auth_start_url("/github")} className="gb-onboarding-primary">
                  Connect GitHub
                </a>
                <a href="https://github.com/apps/reviewer-live" target="_blank" rel="noreferrer" className="gb-onboarding-secondary">
                  Install GitHub App
                </a>
              </div>
            </div>
            <div className="gb-onboarding-preview">
              <div className="gb-preview-step">
                <span className="gb-preview-step-number">01</span>
                <div>
                  <div className="gb-preview-step-title">Connect GitHub</div>
                  <div className="gb-preview-step-copy">Start from your GitHub identity, not from a noisy global repo list.</div>
                </div>
              </div>
              <div className="gb-preview-step">
                <span className="gb-preview-step-number">02</span>
                <div>
                  <div className="gb-preview-step-title">Select a repository</div>
                  <div className="gb-preview-step-copy">Choose one repo first, then let Reviewer show only its open pull requests.</div>
                </div>
              </div>
              <div className="gb-preview-step">
                <span className="gb-preview-step-number">03</span>
                <div>
                  <div className="gb-preview-step-title">Choose the mode</div>
                  <div className="gb-preview-step-copy">Manual Review, Automatic Review, or Review New Pushes.</div>
                </div>
              </div>
            </div>
          </div>
          {surface_error ? <div className="gb-surface-message gb-surface-error">{surface_error}</div> : null}
        </section>
        <SiteFooter />
      </div>
    );
  }

  if (!onboarding_complete) {
    return (
      <div className="github-bot-page">
        <section className="gb-grid-shell">
          <div className="gb-onboarding-shell">
            <div className="gb-dashboard-head">
              <div>
                <span className="gb-pill">Setup</span>
                <h1 className="gb-dashboard-title">Choose one repository and tell Reviewer how it should behave.</h1>
              </div>
              <button type="button" className="gb-signout-button" onClick={() => void handle_sign_out()} disabled={is_signing_out}>
                <LogOut size={14} />
                {is_signing_out ? "Disconnecting..." : `@${auth_session.login}`}
              </button>
            </div>

            {surface_error ? <div className="gb-surface-message gb-surface-error">{surface_error}</div> : null}
            {surface_feedback ? <div className="gb-surface-message gb-surface-success">{surface_feedback}</div> : null}

            <div className="gb-onboarding-grid">
              <div className="gb-onboarding-panel">
                <div className="gb-section-head">
                  <span className="gb-section-kicker">Step 1</span>
                  <h2 className="gb-section-title">Select a repository</h2>
                </div>
                <p className="gb-section-copy">Only public repositories you can access and where the Reviewer app is installed appear here.</p>
                {is_loading_repositories ? <div className="gb-panel-note">Loading repositories...</div> : null}
                {!is_loading_repositories && repositories.length === 0 ? (
                  <div className="gb-empty-state">
                    <div className="gb-empty-title">No repositories ready yet</div>
                    <div className="gb-empty-copy">Install the Reviewer GitHub App on a public repository, then come back here to finish setup.</div>
                  </div>
                ) : null}
                <div className="gb-onboarding-repo-list">
                  {repositories.map((repository) => (
                    <button
                      key={repository.full_name}
                      type="button"
                      className={`gb-onboarding-repo-card ${selected_repository === repository.full_name ? "gb-onboarding-repo-card-active" : ""}`}
                      onClick={() => {
                        set_selected_repository(repository.full_name);
                        set_selected_pull_request(null);
                        set_surface_feedback(null);
                      }}
                    >
                      <div>
                        <div className="gb-onboarding-repo-name">{repository.full_name}</div>
                        <div className="gb-onboarding-repo-meta">{repository.open_pull_requests} open PRs</div>
                      </div>
                      <span className="gb-status-pill">{mode_label(repo_settings[repository.full_name] ?? repository.settings)}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="gb-onboarding-panel">
                <div className="gb-section-head">
                  <span className="gb-section-kicker">Step 2</span>
                  <h2 className="gb-section-title">Choose the review mode</h2>
                </div>
                <p className="gb-section-copy">Start with manual review, or turn on automatic PR review and push re-reviews now.</p>
                <div className="gb-onboarding-mode-grid">
                  {onboarding_modes.map((mode) => (
                    <button
                      key={mode.key}
                      type="button"
                      className={`gb-onboarding-mode-card ${onboarding_mode === mode.key ? "gb-onboarding-mode-card-active" : ""}`}
                      onClick={() => set_onboarding_mode(mode.key)}
                      disabled={!selected_repository_card}
                    >
                      <div className="gb-onboarding-mode-title">{mode.title}</div>
                      <div className="gb-onboarding-mode-copy">{mode.detail}</div>
                    </button>
                  ))}
                </div>
                <div className="gb-onboarding-footer">
                  <div className="gb-onboarding-selected">
                    <span className="gb-section-kicker">Selected</span>
                    <div className="gb-onboarding-selected-name">{selected_repository_card?.full_name ?? "Choose a repository first"}</div>
                  </div>
                  <button
                    type="button"
                    className="gb-onboarding-primary gb-inline-action"
                    onClick={() => void handle_complete_onboarding()}
                    disabled={!selected_repository_card || is_applying_onboarding}
                  >
                    <Rocket size={14} />
                    {is_applying_onboarding ? "Saving setup..." : "Finish setup"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>
        <SiteFooter />
      </div>
    );
  }

  return (
    <div className="github-bot-page">
      <section className="gb-grid-shell">
        <div className="gb-dashboard-shell">
          <div className="gb-dashboard-head">
            <div>
              <span className="gb-pill">GitHub Review Bot</span>
              <h1 className="gb-dashboard-title">{selected_repository_card?.full_name ?? "Reviewer dashboard"}</h1>
            </div>
            <div className="gb-dashboard-actions">
              <button type="button" className="gb-signout-button" onClick={() => set_onboarding_complete(false)}>
                <Rocket size={14} />
                Reconfigure
              </button>
              <button type="button" className="gb-signout-button" onClick={() => void handle_sign_out()} disabled={is_signing_out}>
                <LogOut size={14} />
                {is_signing_out ? "Disconnecting..." : `@${auth_session.login}`}
              </button>
            </div>
          </div>

        {surface_error ? <div className="gb-surface-message gb-surface-error">{surface_error}</div> : null}
        {surface_feedback ? <div className="gb-surface-message gb-surface-success">{surface_feedback}</div> : null}

        <div className="gb-dashboard-metrics">
          <div className="gb-metric-card">
            <div className="gb-metric-label">Visible repos</div>
            <div className="gb-metric-value">{is_loading_repositories ? "..." : repositories.length}</div>
          </div>
          <div className="gb-metric-card">
            <div className="gb-metric-label">Open PRs</div>
            <div className="gb-metric-value">{is_loading_pull_requests ? "..." : pull_requests.length}</div>
          </div>
          <div className="gb-metric-card">
            <div className="gb-metric-label">Automation</div>
            <div className="gb-metric-value gb-summary-value-small">{backend_health ? (automation_ready ? "live" : "partial") : "checking"}</div>
          </div>
        </div>

        <div className="gb-dashboard-grid">
          <div className="gb-dashboard-column gb-dashboard-column-repos">
            <div className="gb-dashboard-card gb-dashboard-card-tight">
            <div className="gb-panel-top">
              <div>
                <div className="gb-panel-label">repositories</div>
                <div className="gb-panel-title">Configured repos</div>
              </div>
              <Github className="gb-panel-icon" />
            </div>
            {is_loading_repositories ? <div className="gb-panel-note">Loading repositories you can manage...</div> : null}
            {!is_loading_repositories && repositories.length === 0 ? (
              <div className="gb-empty-state">
                <div className="gb-empty-title">No visible repositories yet</div>
                <div className="gb-empty-copy">Install the Reviewer GitHub App on a repository your GitHub account can access, then come back here to manage open pull requests and automation settings.</div>
                <div className="gb-empty-actions">
                  <a href="https://github.com/apps/reviewer-live" target="_blank" rel="noreferrer" className="history-action history-action-primary">
                    Install GitHub App
                  </a>
                </div>
              </div>
            ) : null}
            <div className="gb-repo-list gb-repo-list-compact">
              {repositories.map((repository) => {
                const repository_settings = repo_settings[repository.full_name] ?? repository.settings;

                return (
                  <button
                    key={repository.full_name}
                    type="button"
                    className={`gb-repo-card gb-repo-card-compact ${selected_repository === repository.full_name ? "gb-repo-card-active" : ""}`}
                    onClick={() => {
                      set_selected_repository(repository.full_name);
                      set_selected_pull_request(null);
                      set_queued_pull_request(null);
                      set_surface_feedback(null);
                    }}
                  >
                    <div className="gb-repo-top">
                      <div>
                        <div className="gb-repo-name">{repository.repo}</div>
                        <div className="gb-repo-meta">{repository.owner}</div>
                      </div>
                      <span className="gb-status-pill">{mode_label(repository_settings)}</span>
                    </div>
                    <div className="gb-repo-copy gb-repo-copy-compact">{repository.open_pull_requests} open PRs · {repository.default_branch}</div>
                  </button>
                );
              })}
            </div>
            </div>
          </div>

          <div className="gb-dashboard-column gb-dashboard-column-main">
            <div className="gb-dashboard-card">
            <div className="gb-panel-top">
              <div>
                <div className="gb-panel-label">pull requests</div>
                <div className="gb-panel-title">Review queue</div>
              </div>
              <GitPullRequest className="gb-panel-icon" />
            </div>
            <div className="gb-panel-copy gb-panel-copy-tight">
              {selected_repository_card
                ? repository_summary(selected_repository_card, selected_repository_settings)
                : "Choose a repository to see its open pull requests."}
            </div>
            {is_loading_pull_requests ? <div className="gb-panel-note">Loading open pull requests...</div> : null}
            <div className="gb-pr-list">
              {!is_loading_pull_requests && pull_requests.length > 0
                ? pull_requests.map((pull_request) => (
                    <div
                      key={`${selected_repository}-${pull_request.number}`}
                      className={`gb-pr-card gb-pr-card-dashboard ${selected_pull_request_card?.number === pull_request.number ? "gb-pr-card-active" : ""}`}
                    >
                      <button type="button" className="gb-pr-card-select" onClick={() => set_selected_pull_request(pull_request.number)}>
                        <div className="gb-pr-top">
                          <div>
                            <div className="gb-pr-repo">#{pull_request.number}</div>
                            <div className="gb-pr-title">{pull_request.title}</div>
                          </div>
                          <span className="gb-pr-updated">{format_updated_label(pull_request.updated_at)}</span>
                        </div>
                        <div className="gb-pr-summary">
                          {pull_request.author} · {pull_request.head_branch} → {pull_request.base_branch}
                        </div>
                      </button>
                      <div className="gb-pr-footer">
                        <span className="gb-pr-mode">{format_mode_label(pull_request.mode)}</span>
                        <div className="gb-pr-actions">
                          <a href={pull_request.html_url} target="_blank" rel="noreferrer" className="gb-text-link">
                            Open PR
                          </a>
                          <button
                            type="button"
                            className="gb-onboarding-primary gb-inline-action"
                            onClick={() => void handle_review_now(pull_request.number)}
                            disabled={is_triggering_review}
                          >
                            {is_triggering_review && queued_pull_request === pull_request.number ? "Reviewing..." : "Review now"}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                : null}
              {!is_loading_pull_requests && selected_repository_card && pull_requests.length === 0 ? (
                <div className="gb-empty-state">
                  <div className="gb-empty-title">No open pull requests</div>
                  <div className="gb-empty-copy">
                    {selected_repository_card.full_name} is configured correctly. Reviewer is waiting for a new open PR to review.
                  </div>
                </div>
              ) : null}
            </div>
            </div>
          </div>
            <div className="gb-dashboard-column gb-dashboard-column-side">
            <div className="gb-dashboard-card gb-dashboard-card-tight">
            <div className="gb-panel-top">
              <div>
                <div className="gb-panel-label">automation</div>
                <div className="gb-panel-title">Live controls</div>
              </div>
              <Bot className="gb-panel-icon" />
            </div>
            <div className="gb-settings-grid gb-settings-grid-tight">
              {automation_modes.map((mode) => {
                const setting_key = mode.key;
                const is_enabled = selected_repository_settings[setting_key];

                return (
                  <div key={mode.title} className={`gb-mode-card gb-mode-card-compact ${is_enabled ? "gb-mode-card-active" : ""}`}>
                    <div className="gb-mode-title">{mode.title}</div>
                    <div className="gb-mode-copy">{mode.detail}</div>
                    <div className="gb-mode-toggle-row">
                      <span className="gb-mode-status">{is_enabled ? "On" : "Off"}</span>
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

            <div className="gb-dashboard-card gb-dashboard-card-tight">
            <div className="gb-panel-top">
              <div>
                <div className="gb-panel-label">status</div>
                <div className="gb-panel-title">Current focus</div>
              </div>
              <CheckCircle2 className="gb-panel-icon" />
            </div>
              <div className="gb-focus-card gb-focus-card-first">
                <div className="gb-focus-label">Repository</div>
                <div className="gb-focus-title">{selected_repository_card?.full_name ?? "No repository selected"}</div>
                <div className="gb-focus-copy">{mode_copy(selected_repository_settings)} · {selected_repository_card?.open_pull_requests ?? 0} open PRs</div>
              </div>
              {selected_repository_activity?.last_review_at ? (
                <div className="gb-focus-card gb-focus-card-secondary">
                  <div className="gb-focus-label">Latest activity</div>
                  <div className="gb-focus-title">PR #{selected_repository_activity.last_pull_number}</div>
                  <div className="gb-focus-copy">
                    {selected_repository_activity.last_action || "updated"} via {format_trigger_label(selected_repository_activity.last_trigger)} · {format_updated_label(selected_repository_activity.last_review_at)}
                  </div>
                  {selected_repository_activity.last_comment_url ? (
                    <div className="gb-focus-actions">
                      <a href={selected_repository_activity.last_comment_url} target="_blank" rel="noreferrer" className="gb-text-link">
                        Open summary comment
                      </a>
                    </div>
                  ) : null}
                </div>
              ) : null}
              {selected_pull_request_card ? (
                <div className="gb-focus-card gb-focus-card-secondary">
                  <div className="gb-focus-label">Selected PR</div>
                  <div className="gb-focus-title">{selected_pull_request_card.title}</div>
                  <div className="gb-focus-copy">
                    {selected_pull_request_card.author} · updated {format_updated_label(selected_pull_request_card.updated_at)}
                  </div>
                </div>
              ) : null}
              <div className="gb-activity-list gb-activity-list-tight">
                {activity_items.map((activity_item) => (
                  <div key={activity_item} className="gb-activity-item">
                    <Sparkles className="gb-activity-icon" />
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
        </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
