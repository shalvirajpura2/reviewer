import type { BackendAnalysisResult } from "../types/review";
import { normalize_pr_url, pr_url_validation_message } from "./pr_url";

const configured_backend_url = import.meta.env.VITE_BACKEND_URL?.replace(/\/$/, "");

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

  try {
    response = await fetch(`${resolve_backend_url()}${path}`, init);
  } catch {
    throw new Error("Network error. Please check your connection and try again.");
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

export async function analyze_pr(pr_url: string, force_refresh = false): Promise<BackendAnalysisResult> {
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
