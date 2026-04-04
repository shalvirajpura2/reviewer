from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    pr_url: str = Field(min_length=1)
    force_refresh: bool = False


class PreviewRequest(BaseModel):
    pr_url: str = Field(min_length=1)


class GithubPrMetadata(BaseModel):
    owner: str
    repo: str
    pull_number: int
    repo_full_name: str
    title: str
    author: str
    author_avatar_url: str
    base_branch: str
    head_branch: str
    head_sha: str = ""
    commits: int
    additions: int
    deletions: int
    changed_files: int
    html_url: str
    created_at: str
    updated_at: str


class GithubCommitSummary(BaseModel):
    sha: str
    message: str
    author: str
    authored_at: str | None = None
    html_url: str | None = None


class ChangedFile(BaseModel):
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: str | None = None
    blob_url: str | None = None
    previous_filename: str | None = None


class ClassifiedFile(ChangedFile):
    areas: list[str]
    tags: list[str]
    is_sensitive: bool
    blast_radius_weight: int
    symbol_hints: list[str] = []


class RiskSignal(BaseModel):
    id: str
    label: str
    severity: Literal["low", "medium", "high"]
    evidence: list[str]
    score_impact: int
    breakdown_key: Literal[
        "sensitive_code_risk",
        "dependency_risk",
        "migration_risk",
        "config_risk",
        "test_risk",
        "blast_radius_risk",
    ]


class RiskBreakdownItem(BaseModel):
    key: Literal[
        "sensitive_code_risk",
        "dependency_risk",
        "migration_risk",
        "config_risk",
        "test_risk",
        "blast_radius_risk",
    ]
    label: str
    score: int
    summary: str


class RecommendationItem(BaseModel):
    id: str
    title: str
    detail: str
    priority: Literal["now", "soon", "nice_to_have"]


class ChangedFilePreviewGroup(BaseModel):
    label: str
    files: list[ClassifiedFile]


class TopRiskFile(BaseModel):
    filename: str
    risk_level: Literal["low", "medium", "high"]
    reasons: list[str]
    patch_excerpt: list[str] = []
    changes: int
    areas: list[str]
    is_sensitive: bool
    blob_url: str | None = None


class ScoreSummary(BaseModel):
    base_score: int
    total_penalty: int
    total_relief: int
    score_version: str


class AnalysisCoverage(BaseModel):
    files_analyzed: int
    total_files: int
    patchless_files: int
    is_partial: bool
    partial_reasons: list[str]


class AnalysisContext(BaseModel):
    confidence_in_score: Literal["high", "medium", "low"]
    summary: str
    limitations: list[str]
    data_sources: list[str]
    cache_status: Literal["live", "cached", "fallback"]
    coverage: AnalysisCoverage


class PrPreviewResult(BaseModel):
    metadata: GithubPrMetadata


class PrAnalysisResult(BaseModel):
    metadata: GithubPrMetadata
    score: int
    label: Literal[
        "high confidence",
        "moderate confidence",
        "low confidence",
        "risky to merge",
    ]
    verdict: str
    review_focus: list[str]
    affected_areas: list[str]
    risk_breakdown: list[RiskBreakdownItem]
    triggered_signals: list[RiskSignal]
    recommendations: list[RecommendationItem]
    changed_file_groups: list[ChangedFilePreviewGroup]
    top_risk_files: list[TopRiskFile]
    commits: list[GithubCommitSummary]
    score_summary: ScoreSummary
    analysis_context: AnalysisContext
