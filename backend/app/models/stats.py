from pydantic import BaseModel


class PublicStatsResponse(BaseModel):
    visitor_count: int
    prs_analyzed: int
    deterministic_scoring_rate: int
    avg_report_time_seconds: float | None


class RepoStarsResponse(BaseModel):
    stars: int


class RecordVisitRequest(BaseModel):
    client_id: str


class RecentAnalysisItem(BaseModel):
    repo_name: str
    pr_number: int
    title: str
    pr_url: str
    score: int
    verdict: str
    confidence_label: str
    confidence_in_score: str | None = None
    analyzed_at: str
    source_updated_at: str | None = None
    cache_status: str
    files_changed: int | None = None
    files_analyzed: int | None = None
    is_partial: bool | None = None


class RecentAnalysesResponse(BaseModel):
    items: list[RecentAnalysisItem]
