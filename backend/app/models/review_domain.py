from typing import Literal

from pydantic import BaseModel

from app.models.analysis import (
    AnalysisContext,
    ChangedFilePreviewGroup,
    GithubCommitSummary,
    GithubPrMetadata,
    RecommendationItem,
    RiskBreakdownItem,
    RiskSignal,
    SafeguardSummary,
    ScoreSummary,
    TopRiskFile,
)


class ReviewFinding(BaseModel):
    id: str
    severity: Literal["low", "medium", "high"]
    confidence: Literal["low", "medium", "high"]
    category: Literal["signal", "file", "safeguard", "recommendation"]
    title: str
    body: str
    path: str | None = None
    line: int | None = None
    end_line: int | None = None
    evidence: list[str] = []
    blob_url: str | None = None
    suggested_action: str | None = None
    publishable_inline: bool = False
    publishable_summary: bool = True


class ReviewAnalysis(BaseModel):
    metadata: GithubPrMetadata
    score: int
    label: Literal[
        "high confidence",
        "moderate confidence",
        "low confidence",
        "risky to merge",
    ]
    verdict: str
    summary: str
    review_focus: list[str]
    affected_areas: list[str]
    risk_breakdown: list[RiskBreakdownItem]
    triggered_signals: list[RiskSignal]
    findings: list[ReviewFinding]
    recommendations: list[RecommendationItem]
    safeguards: SafeguardSummary
    changed_file_groups: list[ChangedFilePreviewGroup]
    top_risk_files: list[TopRiskFile]
    commits: list[GithubCommitSummary]
    score_summary: ScoreSummary
    analysis_context: AnalysisContext
