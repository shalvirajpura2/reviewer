export type GithubBotRepositorySettings = {
  manual_review: boolean;
  automatic_review: boolean;
  review_new_pushes: boolean;
};

export type GithubBotRepositoryActivity = {
  last_review_at: string;
  last_pull_number: number;
  last_trigger: string;
  last_action: string;
  last_comment_url: string | null;
};

export type GithubBotRepositorySummary = {
  owner: string;
  repo: string;
  full_name: string;
  installation_id: number;
  default_branch: string;
  app_installed: boolean;
  open_pull_requests: number;
  settings: GithubBotRepositorySettings;
  activity: GithubBotRepositoryActivity;
};

export type GithubBotPullRequestSummary = {
  number: number;
  title: string;
  author: string;
  updated_at: string;
  html_url: string;
  base_branch: string;
  head_branch: string;
  draft: boolean;
  mode: string;
};

export type GithubBotRepositoriesResponse = {
  repositories: GithubBotRepositorySummary[];
};

export type GithubBotPullRequestsResponse = {
  repository: GithubBotRepositorySummary;
  pull_requests: GithubBotPullRequestSummary[];
};

export type ReviewCommentPublication = {
  action: "created" | "updated";
  comment_id: number;
  html_url: string | null;
  body: string;
};