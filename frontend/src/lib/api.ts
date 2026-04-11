import type { BackendAnalysisResult, BackendMetadata } from "../types/review";
import type {
  GithubBotPullRequestsResponse,
  GithubBotRepositoriesResponse,
  GithubBotRepositorySettings,
  ReviewCommentPublication,
} from "../types/github_bot";
import { normalize_pr_url, pr_url_validation_message } from "./pr_url";

const configured_backend_url = import.meta.env.VITE_BACKEND_URL?.replace(/\/$/, "");
const configured_github_app_slug = import.meta.env.VITE_GITHUB_APP_SLUG?.trim() || "reviewer-live";
const request_timeout_ms = 30000;
const reviewer_csrf_cookie_name = "reviewer_web_csrf";
let cached_site_stats: SiteStats | null = null;
let site_stats_inflight_request: Promise<SiteStats> | null = null;
let cached_repo_stars: RepoStars | null = null;
let repo_stars_inflight_request: Promise<RepoStars> | null = null;

export type SiteStats = {
  visitor_count: number;
  prs_analyzed: number;
  deterministic_scoring_rate: number;
  avg_report_time_seconds: number | null;
};

export type RepoStars = {
  stars: number;
};

export type BackendHealth = {
  status: string;
  github_token_configured: boolean;
  github_app_configured: boolean;
  github_web_auth_configured: boolean;
  github_webhook_configured: boolean;
  reviewer_publish_github_token_configured: boolean;
  database_configured: boolean;
  uptime_seconds: number;
  cache_ttl_seconds: number;
  stale_cache_ttl_seconds: number;
};
export type RecentAnalysis = {
  repo_name: string;
  pr_number: number;
  title: string;
  pr_url: string;
  score: number;
  verdict: string;
  confidence_label: string;
  analyzed_at: string;
  cache_status: string;
};

export type PrPreview = {
  metadata: BackendMetadata;
};

type ApiErrorPayload = {
  message?: string;
  detail?: string;
};

export type GithubWebSession = {
  authenticated: boolean;
  configured: boolean;
  login: string;
  user_id: number;
  csrf_token: string;
};

function resolve_backend_url() {
  return configured_backend_url || "http://localhost:8000";
}

function read_cookie_value(cookie_name: string): string {
  const encoded_name = `${encodeURIComponent(cookie_name)}=`;
  const raw_cookie = document.cookie || "";

  for (const part of raw_cookie.split(";")) {
    const trimmed_part = part.trim();
    if (!trimmed_part.startsWith(encoded_name)) {
      continue;
    }

    return decodeURIComponent(trimmed_part.slice(encoded_name.length));
  }

  return "";
}

function is_mutating_request(init?: RequestInit): boolean {
  const request_method = (init?.method || "GET").toUpperCase();
  return request_method === "POST" || request_method === "PUT" || request_method === "PATCH" || request_method === "DELETE";
}

function with_latest_csrf_header(init?: RequestInit): RequestInit | undefined {
  const csrf_token = read_cookie_value(reviewer_csrf_cookie_name).trim();
  if (!csrf_token) {
    return init;
  }

  const next_headers = new Headers(init?.headers);
  next_headers.set("X-Reviewer-CSRF", csrf_token);

  return {
    ...(init || {}),
    headers: next_headers,
  };
}

async function silently_refresh_web_session_context() {
  try {
    await fetch(`${resolve_backend_url()}/api/auth/session`, {
      method: "GET",
      credentials: "include",
    });
  } catch {
    // Ignore refresh failures and keep the original request error handling path.
  }
}

function should_retry_after_csrf_failure(path: string, init: RequestInit | undefined, response: Response, payload: unknown): payload is ApiErrorPayload {
  if (path === "/api/auth/session") {
    return false;
  }

  if (!is_mutating_request(init) || response.status !== 403) {
    return false;
  }

  const api_error = payload as ApiErrorPayload | null;
  const combined_message = `${api_error?.message || ""} ${api_error?.detail || ""}`.toLowerCase();
  return combined_message.includes("csrf");
}

async function parse_json_response<T>(response: Response): Promise<T | null> {
  try {
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

async function request_json<T>(path: string, init?: RequestInit, fallback_message = "Request failed.") {
  async function run_request(request_init?: RequestInit): Promise<Response> {
    const request_controller = new AbortController();
    const upstream_signal = request_init?.signal;
    const timeout_id = window.setTimeout(() => {
      request_controller.abort();
    }, request_timeout_ms);

    function abort_request() {
      request_controller.abort();
    }

    if (upstream_signal?.aborted) {
      request_controller.abort();
    } else {
      upstream_signal?.addEventListener("abort", abort_request, { once: true });
    }

    try {
      return await fetch(`${resolve_backend_url()}${path}`, {
        ...request_init,
        credentials: "include",
        signal: request_controller.signal,
      });
    } catch (error) {
      if (upstream_signal?.aborted) {
        throw new Error("Request cancelled.");
      }

      if (error instanceof DOMException && error.name === "AbortError") {
        throw new Error("Request timed out. Please try again.");
      }

      throw new Error("Network error. Please check your connection and try again.");
    } finally {
      window.clearTimeout(timeout_id);
      upstream_signal?.removeEventListener("abort", abort_request);
    }
  }

  let response = await run_request(init);
  let payload = await parse_json_response<T | ApiErrorPayload>(response);

  if (should_retry_after_csrf_failure(path, init, response, payload)) {
    await silently_refresh_web_session_context();
    response = await run_request(with_latest_csrf_header(init));
    payload = await parse_json_response<T | ApiErrorPayload>(response);
  }

  if (!response.ok) {
    const api_error = payload as ApiErrorPayload | null;
    throw new Error(api_error?.message || api_error?.detail || fallback_message);
  }

  if (payload === null) {
    throw new Error(fallback_message);
  }

  return payload as T;
}

export function get_or_create_client_id() {
  const storage_key = "reviewer_client_id_v1";
  const existing_client_id = window.localStorage.getItem(storage_key);
  if (existing_client_id) {
    return existing_client_id;
  }

  const next_client_id = window.crypto?.randomUUID?.() ?? `reviewer-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  window.localStorage.setItem(storage_key, next_client_id);
  return next_client_id;
}

export async function preview_pr(pr_url: string): Promise<PrPreview> {
  const normalized_pr_url = normalize_pr_url(pr_url);
  const validation_error = pr_url_validation_message(normalized_pr_url);

  if (validation_error) {
    throw new Error(validation_error);
  }

  return request_json<PrPreview>(
    "/api/preview",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Reviewer-Client-Id": get_or_create_client_id(),
      },
      body: JSON.stringify({ pr_url: normalized_pr_url }),
    },
    "Reviewer could not preview that pull request."
  );
}

export async function analyze_pr(pr_url: string, force_refresh = false, signal?: AbortSignal): Promise<BackendAnalysisResult> {
  const normalized_pr_url = normalize_pr_url(pr_url);
  const validation_error = pr_url_validation_message(normalized_pr_url);

  if (validation_error) {
    throw new Error(validation_error);
  }

  return request_json<BackendAnalysisResult>(
    "/api/analyze",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Reviewer-Client-Id": get_or_create_client_id(),
      },
      body: JSON.stringify({ pr_url: normalized_pr_url, force_refresh }),
      signal,
    },
    "Reviewer could not analyze that pull request."
  );
}

export async function get_site_stats(): Promise<SiteStats> {
  if (cached_site_stats) {
    return cached_site_stats;
  }

  if (site_stats_inflight_request) {
    return site_stats_inflight_request;
  }

  site_stats_inflight_request = request_json<SiteStats>("/api/stats", undefined, "Reviewer stats are unavailable.")
    .then((stats) => {
      cached_site_stats = stats;
      return stats;
    })
    .finally(() => {
      site_stats_inflight_request = null;
    });

  return site_stats_inflight_request;
}

export async function get_recent_analyses(): Promise<RecentAnalysis[]> {
  const payload = await request_json<{ items: RecentAnalysis[] }>(
    "/api/stats/recent-analyses",
    undefined,
    "Reviewer recent analyses are unavailable."
  );

  return payload.items;
}

export async function record_site_visit(client_id: string): Promise<SiteStats> {
  const stats = await request_json<SiteStats>(
    "/api/stats/visit",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ client_id }),
    },
    "Reviewer visit stats are unavailable."
  );

  cached_site_stats = stats;
  return stats;
}

export async function get_repo_stars(): Promise<RepoStars> {
  if (cached_repo_stars) {
    return cached_repo_stars;
  }

  if (repo_stars_inflight_request) {
    return repo_stars_inflight_request;
  }

  repo_stars_inflight_request = request_json<RepoStars>("/api/stats/repo-stars", undefined, "Reviewer repo stars are unavailable.")
    .then((repo_stars) => {
      cached_repo_stars = repo_stars;
      return repo_stars;
    })
    .finally(() => {
      repo_stars_inflight_request = null;
    });

  return repo_stars_inflight_request;
}

export async function get_github_bot_repositories(signal?: AbortSignal): Promise<GithubBotRepositoriesResponse> {
  return request_json<GithubBotRepositoriesResponse>(
    "/api/github-bot/repositories",
    {
      method: "GET",
      signal,
    },
    "Reviewer could not load connected GitHub repositories."
  );
}

export async function get_github_web_session(signal?: AbortSignal): Promise<GithubWebSession> {
  return request_json<GithubWebSession>(
    "/api/auth/session",
    {
      method: "GET",
      signal,
    },
    "Reviewer could not load the GitHub dashboard session."
  );
}

export async function logout_github_web_session(csrf_token: string): Promise<void> {
  await request_json<{ ok: boolean }>(
    "/api/auth/logout",
    {
      method: "POST",
      headers: {
        "X-Reviewer-CSRF": csrf_token,
      },
    },
    "Reviewer could not clear the GitHub dashboard session."
  );
}

export function build_github_auth_start_url(next_path = "/github") {
  return `${resolve_backend_url()}/api/auth/github/start?next=${encodeURIComponent(next_path)}`;
}

export function build_github_app_install_url(next_path = "/github") {
  const normalized_next_path = next_path.startsWith("/") ? next_path : `/${next_path}`;
  const callback_url = `${resolve_backend_url()}/api/auth/github/app-install/callback`;
  const encoded_callback_url = encodeURIComponent(callback_url);
  const encoded_state = encodeURIComponent(normalized_next_path);
  const encoded_slug = encodeURIComponent(configured_github_app_slug);
  return `https://github.com/apps/${encoded_slug}/installations/new?state=${encoded_state}&redirect_uri=${encoded_callback_url}`;
}

export async function get_github_bot_pull_requests(owner: string, repo: string, signal?: AbortSignal): Promise<GithubBotPullRequestsResponse> {
  return request_json<GithubBotPullRequestsResponse>(
    `/api/github-bot/repositories/${owner}/${repo}/pulls`,
    {
      method: "GET",
      signal,
    },
    "Reviewer could not load open pull requests for that repository."
  );
}

export async function update_github_bot_settings(
  owner: string,
  repo: string,
  settings: GithubBotRepositorySettings,
  csrf_token: string,
): Promise<GithubBotRepositorySettings> {
  return request_json<GithubBotRepositorySettings>(
    `/api/github-bot/repositories/${owner}/${repo}/settings`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "X-Reviewer-CSRF": csrf_token,
      },
      body: JSON.stringify(settings),
    },
    "Reviewer could not save repository review settings."
  );
}

export async function trigger_github_bot_review(owner: string, repo: string, pull_number: number, csrf_token: string): Promise<ReviewCommentPublication> {
  return request_json<ReviewCommentPublication>(
    `/api/github-bot/repositories/${owner}/${repo}/review`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Reviewer-Client-Id": get_or_create_client_id(),
        "X-Reviewer-CSRF": csrf_token,
      },
      body: JSON.stringify({ pull_number }),
    },
    "Reviewer could not trigger a manual GitHub review for that pull request."
  );
}

export async function get_backend_health(): Promise<BackendHealth> {
  return request_json<BackendHealth>("/health", undefined, "Reviewer backend health is unavailable.");
}
