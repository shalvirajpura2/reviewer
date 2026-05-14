import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GithubBotPage } from "./github_bot_page";
import {
  get_backend_health,
  get_github_bot_pull_requests,
  get_github_bot_repositories,
  get_github_web_session,
  trigger_github_bot_review,
  update_github_bot_settings,
} from "../lib/api";
import { button_by_text, click_element, create_deferred, render_component, wait_for } from "../test/component_test_utils";
import { build_bot_pull_request, build_bot_repository } from "../test/fixtures";

vi.mock("../lib/api", () => ({
  build_github_app_install_url: vi.fn(() => "https://github.com/apps/reviewer-live/installations/new"),
  build_github_auth_start_url: vi.fn(() => "http://localhost:8000/api/auth/github/start?next=%2Fgithub"),
  get_backend_health: vi.fn(),
  get_github_bot_pull_requests: vi.fn(),
  get_github_bot_repositories: vi.fn(),
  get_github_web_session: vi.fn(),
  logout_github_web_session: vi.fn(),
  trigger_github_bot_review: vi.fn(),
  update_github_bot_settings: vi.fn(),
}));

const get_github_web_session_mock = vi.mocked(get_github_web_session);
const get_backend_health_mock = vi.mocked(get_backend_health);
const get_github_bot_repositories_mock = vi.mocked(get_github_bot_repositories);
const get_github_bot_pull_requests_mock = vi.mocked(get_github_bot_pull_requests);
const update_github_bot_settings_mock = vi.mocked(update_github_bot_settings);
const trigger_github_bot_review_mock = vi.mocked(trigger_github_bot_review);

function render_github_bot_page() {
  return render_component(
    <MemoryRouter initialEntries={["/github"]}>
      <GithubBotPage />
    </MemoryRouter>,
  );
}

describe("GithubBotPage", () => {
  beforeEach(() => {
    get_github_web_session_mock.mockReset();
    get_backend_health_mock.mockReset();
    get_github_bot_repositories_mock.mockReset();
    get_github_bot_pull_requests_mock.mockReset();
    update_github_bot_settings_mock.mockReset();
    trigger_github_bot_review_mock.mockReset();
    document.body.innerHTML = "";
  });

  it("shows session loading, then unauthenticated connect navigation", async () => {
    const deferred = create_deferred<Awaited<ReturnType<typeof get_github_web_session>>>();
    get_github_web_session_mock.mockReturnValueOnce(deferred.promise);
    const view = await render_github_bot_page();

    expect(document.body.textContent).toContain("Loading your GitHub bot workspace.");

    deferred.resolve({ authenticated: false, configured: true, login: "", user_id: 0, csrf_token: "" });
    await wait_for(() => {
      const connect_link = document.body.querySelector<HTMLAnchorElement>("a.gb-onboarding-primary");
      expect(connect_link?.textContent).toContain("Connect GitHub");
      expect(connect_link?.getAttribute("href")).toContain("/api/auth/github/start");
    });

    await view.unmount();
  });

  it("surfaces repository API failures after authentication", async () => {
    get_github_web_session_mock.mockResolvedValueOnce({
      authenticated: true,
      configured: true,
      login: "shalv",
      user_id: 1,
      csrf_token: "csrf-token",
    });
    get_backend_health_mock.mockResolvedValueOnce({
      status: "ok",
      github_token_configured: true,
      github_app_configured: true,
      github_web_auth_configured: true,
      github_webhook_configured: true,
      reviewer_publish_github_token_configured: false,
      reviewer_publish_api_token_configured: false,
      database_configured: true,
      uptime_seconds: 12,
      cache_ttl_seconds: 60,
      stale_cache_ttl_seconds: 300,
    });
    get_github_bot_repositories_mock.mockRejectedValueOnce(new Error("Repository list failed."));
    const view = await render_github_bot_page();

    await wait_for(() => {
      expect(document.body.textContent).toContain("Repository list failed.");
    });

    await view.unmount();
  });

  it("loads repositories, saves setup, and handles manual review API failures", async () => {
    const repository = build_bot_repository();
    get_github_web_session_mock.mockResolvedValueOnce({
      authenticated: true,
      configured: true,
      login: "shalv",
      user_id: 1,
      csrf_token: "csrf-token",
    });
    get_backend_health_mock.mockResolvedValueOnce({
      status: "ok",
      github_token_configured: true,
      github_app_configured: true,
      github_web_auth_configured: true,
      github_webhook_configured: true,
      reviewer_publish_github_token_configured: false,
      reviewer_publish_api_token_configured: false,
      database_configured: true,
      uptime_seconds: 12,
      cache_ttl_seconds: 60,
      stale_cache_ttl_seconds: 300,
    });
    get_github_bot_repositories_mock.mockResolvedValueOnce({ repositories: [repository] });
    update_github_bot_settings_mock.mockResolvedValueOnce(repository.settings);
    get_github_bot_pull_requests_mock.mockResolvedValueOnce({
      repository,
      pull_requests: [build_bot_pull_request()],
    });
    trigger_github_bot_review_mock.mockRejectedValueOnce(new Error("Manual review failed."));
    const view = await render_github_bot_page();

    await wait_for(() => {
      expect(document.body.textContent).toContain("Choose the review mode");
    });

    await click_element(button_by_text("Save mode"));
    await wait_for(() => {
      expect(document.body.textContent).toContain("Saved manual mode for acme/reviewer.");
    });

    await click_element(button_by_text("Continue to dashboard"));
    await wait_for(() => {
      expect(document.body.textContent).toContain("Open pull requests");
      expect(document.body.textContent).toContain("Tighten review flow");
    });

    await click_element(button_by_text("Review now"));
    await wait_for(() => {
      expect(document.body.textContent).toContain("Manual review failed.");
    });

    expect(update_github_bot_settings_mock).toHaveBeenCalledWith("acme", "reviewer", repository.settings, "csrf-token");
    expect(trigger_github_bot_review_mock).toHaveBeenCalledWith("acme", "reviewer", 42, "csrf-token");

    await view.unmount();
  });
});
