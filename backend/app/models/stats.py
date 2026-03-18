from pydantic import BaseModel


class PublicStatsResponse(BaseModel):
    visitor_count: int
    prs_analyzed: int
    deterministic_scoring_rate: int
    avg_report_time_seconds: float | None


class RepoStarsResponse(BaseModel):
    stars: int
