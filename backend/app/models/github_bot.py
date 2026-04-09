from pydantic import BaseModel


class GithubBotRepositorySettings(BaseModel):
    manual_review: bool = True
    automatic_review: bool = False
    review_new_pushes: bool = False


class GithubBotRepositoryActivity(BaseModel):
    last_review_at: str = ""
    last_pull_number: int = 0
    last_trigger: str = ""
    last_action: str = ""
    last_comment_url: str | None = None


class GithubBotRepositorySummary(BaseModel):
    owner: str
    repo: str
    full_name: str
    installation_id: int
    default_branch: str
    app_installed: bool = True
    open_pull_requests: int = 0
    settings: GithubBotRepositorySettings
    activity: GithubBotRepositoryActivity


class GithubBotPullRequestSummary(BaseModel):
    number: int
    title: str
    author: str
    updated_at: str
    html_url: str
    base_branch: str
    head_branch: str
    draft: bool = False
    mode: str


class GithubBotRepositoriesResponse(BaseModel):
    repositories: list[GithubBotRepositorySummary]


class GithubBotPullRequestsResponse(BaseModel):
    repository: GithubBotRepositorySummary
    pull_requests: list[GithubBotPullRequestSummary]


class GithubBotRepositorySettingsUpdate(BaseModel):
    manual_review: bool = True
    automatic_review: bool = False
    review_new_pushes: bool = False


class GithubBotManualReviewRequest(BaseModel):
    pull_number: int


class GithubBotWebhookResult(BaseModel):
    status: str
    event: str
    action: str | None = None
    detail: str