import type { BackendAnalysisResult, BackendMetadata } from "../types/review";
import type {
  GithubBotPullRequestsResponse,
  GithubBotRepositoriesResponse,
  GithubBotRepositorySettings,
  ReviewCommentPublication,
} from "../types/github_bot";
import { normalize_pr_url, pr_url_validation_message } from "./pr_url";

const configured_backend_url = import.meta.env.VITE_BACKEND_URL?.replace(/\/$/, "");
const request_timeout_ms = 30000;

export type SiteStats = {
  visitor_count: number;
  prs_analyzed: number;
  deterministic_scoring_rate: number;
  avg_report_time_seconds: number | null;
};

export type RepoStars = {
  stars: number;
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

function resolve_backend_url() {
  return configured_backend_url || "http://localhost:8000";
}

async function parse_json_response<T>(response: Response): Promise<T | null> {
  try {
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

async function request_json<T>(path: string, init?: RequestInit, fallback_message = "Request failed.") {
  let response: Response;
  const request_controller = new AbortController();
  const upstream_signal = init?.signal;
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
    response = await fetch(`${resolve_backend_url()}${path}`, {
      ...init,
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

  const payload = await parse_json_response<T | ApiErrorPayload>(response);

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
  return request_json<SiteStats>("/api/stats", undefined, "Reviewer stats are unavailable.");
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
  return request_json<SiteStats>(
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
}

export async function get_repo_stars(): Promise<RepoStars> {
  return request_json<RepoStars>("/api/stats/repo-stars", undefined, "Reviewer repo stars are unavailable.");
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
): Promise<GithubBotRepositorySettings> {
  return request_json<GithubBotRepositorySettings>(
    `/api/github-bot/repositories/${owner}/${repo}/settings`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(settings),
    },
    "Reviewer could not save repository review settings."
  );
}

export async function trigger_github_bot_review(owner: string, repo: string, pull_number: number): Promise<ReviewCommentPublication> {
  return request_json<ReviewCommentPublication>(
    `/api/github-bot/repositories/${owner}/${repo}/review`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Reviewer-Client-Id": get_or_create_client_id(),
      },
      body: JSON.stringify({ pull_number }),
    },
    "Reviewer could not trigger a manual GitHub review for that pull request."
  );
}
