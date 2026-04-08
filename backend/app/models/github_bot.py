from pydantic import BaseModel


class GithubBotRepositorySettings(BaseModel):
    manual_review: bool = True
    automatic_review: bool = False
    review_new_pushes: bool = False


class GithubBotRepositorySummary(BaseModel):
    owner: str
    repo: str
    full_name: str
    installation_id: int
    default_branch: str
    app_installed: bool = True
    open_pull_requests: int = 0
    settings: GithubBotRepositorySettings


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
