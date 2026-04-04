from app.models.analysis import (
    AnalysisContext,
    AnalysisCoverage,
    ChangedFilePreviewGroup,
    ClassifiedFile,
    GithubCommitSummary,
    GithubPrMetadata,
    PrAnalysisResult,
    RiskSignal,
    ScoreSummary,
    TopRiskFile,
)
from app.services.recommendation_engine import generate_recommendations
from app.services.scoring_engine import compute_score


analysis_limitations = [
    "This analysis does not inspect CI status or deployment health.",
    "Patch structure hints are based on changed hunks, not full repository semantics.",
    "Reviewer does not compute real coverage deltas or repository-wide dependency graphs yet.",
]


TOP_FILE_REASON_LABELS = {
    "migration": "schema or migration path changed",
    "config": "runtime or workflow configuration changed",
    "dependency": "dependency surface changed",
    "shared_core": "shared or reused code touched",
    "middleware": "request or auth flow touched",
    "api": "API boundary changed",
    "frontend": "user-facing behavior may shift",
    "backend": "server-side behavior changed",
    "test": "tests changed alongside implementation",
    "generated": "generated output changed",
    "lockfile": "lockfile or dependency pin changed",
}


def build_affected_areas(files: list[ClassifiedFile]) -> list[str]:
    tags: set[str] = set()
    for file in files:
        for tag in file.tags:
            tags.add(tag)
    return list(tags)[:10]


def build_review_focus(signals: list[RiskSignal]) -> list[str]:
    ranked_signals = sorted(
        [signal for signal in signals if signal.score_impact < 0],
        key=lambda item: (item.severity == "high", abs(item.score_impact)),
        reverse=True,
    )
    return [signal.label for signal in ranked_signals[:3]]


def build_analysis_coverage(
    files: list[ClassifiedFile],
    total_files: int,
    partial_reasons: list[str],
) -> AnalysisCoverage:
    patchless_files = sum(1 for file in files if not file.patch)
    files_analyzed = len(files)
    normalized_total_files = max(total_files, files_analyzed)
    coverage_partial_reasons = list(partial_reasons)

    if patchless_files > 0:
        coverage_partial_reasons.append(
            f"GitHub did not provide patch hunks for {patchless_files} changed files, so structure hints are limited there."
        )

    return AnalysisCoverage(
        files_analyzed=files_analyzed,
        total_files=normalized_total_files,
        patchless_files=patchless_files,
        is_partial=bool(coverage_partial_reasons),
        partial_reasons=coverage_partial_reasons,
    )


def build_confidence_in_score(
    files: list[ClassifiedFile],
    signals: list[RiskSignal],
    commits: list[GithubCommitSummary],
    coverage: AnalysisCoverage,
    cache_status: str,
) -> str:
    if cache_status == "fallback" or coverage.is_partial:
        return "low"

    if len(files) >= 35 or len(commits) >= 20:
        return "low"

    if len(files) <= 8 and len(signals) <= 4 and coverage.patchless_files == 0:
        return "high"

    return "medium"


def build_confidence_summary(
    files: list[ClassifiedFile],
    commits: list[GithubCommitSummary],
    cache_status: str,
    coverage: AnalysisCoverage,
) -> str:
    scope_summary = f"{coverage.files_analyzed} of {coverage.total_files} changed files analyzed"
    patch_summary = f"{coverage.patchless_files} files without patch hunks" if coverage.patchless_files else "full patch hints where available"

    if cache_status == "fallback":
        return (
            f"Showing the latest saved analysis because GitHub could not serve a fresh review right now. "
            f"Saved context covers {scope_summary} and {len(commits)} commits. Patch coverage note: {patch_summary}."
        )

    if len(files) >= 35 or len(commits) >= 20:
        return (
            f"Built from GitHub metadata, {scope_summary}, {len(commits)} commits, deterministic scoring rules, "
            f"and patch-level structure hints. The review surface is broad enough that this score should guide triage more than final approval. "
            f"Patch coverage note: {patch_summary}. Response source: {cache_status}."
        )

    return (
        f"Built from GitHub metadata, {scope_summary}, {len(commits)} commits, deterministic scoring rules, "
        f"and patch-level structure hints. Patch coverage note: {patch_summary}. Response source: {cache_status}."
    )


def pick_group_files(files: list[ClassifiedFile], matcher) -> list[ClassifiedFile]:
    return sorted(
        [file for file in files if matcher(file)],
        key=lambda item: (item.blast_radius_weight, item.changes),
        reverse=True,
    )[:5]


def build_file_groups(files: list[ClassifiedFile]) -> list[ChangedFilePreviewGroup]:
    groups = [
        ChangedFilePreviewGroup(
            label="Highest risk",
            files=pick_group_files(files, lambda file: file.is_sensitive or file.blast_radius_weight >= 4),
        ),
        ChangedFilePreviewGroup(
            label="Config / Infra",
            files=pick_group_files(
                files,
                lambda file: "config" in file.areas or "dependency" in file.areas or "infra" in file.areas,
            ),
        ),
        ChangedFilePreviewGroup(
            label="Shared / Core",
            files=pick_group_files(files, lambda file: "shared_core" in file.areas or "api" in file.areas),
        ),
        ChangedFilePreviewGroup(
            label="Tests",
            files=pick_group_files(files, lambda file: "test" in file.areas),
        ),
    ]

    return [group for group in groups if group.files]


def build_patch_excerpt(file: ClassifiedFile, max_lines: int = 8) -> list[str]:
    if not file.patch:
        return []

    excerpt_lines: list[str] = []

    for patch_line in file.patch.splitlines():
        if patch_line.startswith("@@"):
            if excerpt_lines:
                break
            excerpt_lines.append(patch_line[:180])
            continue

        if not patch_line.startswith(("+", "-")) or patch_line.startswith(("+++", "---")):
            continue

        trimmed_line = patch_line.rstrip()
        if not trimmed_line:
            continue

        excerpt_lines.append(trimmed_line[:180])
        if len(excerpt_lines) >= max_lines:
            break

    return excerpt_lines


def build_file_reasons(file: ClassifiedFile, test_files_present: bool) -> list[str]:
    reasons: list[str] = []

    if file.is_sensitive:
        reasons.append("sensitive execution path touched")

    if file.blast_radius_weight >= 4:
        reasons.append("high blast radius across shared code")
    elif file.blast_radius_weight >= 3:
        reasons.append("moderate blast radius")

    if file.status == "renamed" and file.previous_filename:
        reasons.append(f"renamed from {file.previous_filename}")

    for area in file.areas:
        label = TOP_FILE_REASON_LABELS.get(area)
        if label and label not in reasons:
            reasons.append(label)

    if file.symbol_hints:
        reasons.append(f"structural hints: {', '.join(file.symbol_hints[:2])}")

    if not test_files_present and (file.is_sensitive or file.blast_radius_weight >= 4):
        reasons.append("no test changes detected for this risk area")

    if not file.patch:
        reasons.append("patch hunk unavailable from GitHub")

    if file.changes >= 120:
        reasons.append(f"large diff footprint ({file.changes} lines)")
    elif file.changes >= 50:
        reasons.append(f"meaningful diff footprint ({file.changes} lines)")

    return reasons[:4] or ["changed in this pull request"]


def compute_top_file_score(file: ClassifiedFile, test_files_present: bool) -> int:
    score = file.blast_radius_weight * 10 + min(file.changes, 180)

    if file.is_sensitive:
        score += 25

    if "migration" in file.areas:
        score += 20

    if "config" in file.areas or "dependency" in file.areas:
        score += 14

    if "shared_core" in file.areas or "api" in file.areas or "middleware" in file.areas:
        score += 10

    if file.symbol_hints:
        score += 8

    if file.status == "renamed" and file.previous_filename:
        score += 6

    if not test_files_present and (file.is_sensitive or file.blast_radius_weight >= 4):
        score += 12

    if "generated" in file.areas or "asset" in file.areas:
        score -= 10

    return score


def build_top_risk_files(files: list[ClassifiedFile]) -> list[TopRiskFile]:
    test_files_present = any("test" in file.areas for file in files)

    ranked_files = sorted(
        files,
        key=lambda file: (compute_top_file_score(file, test_files_present), file.changes),
        reverse=True,
    )[:5]

    top_files: list[TopRiskFile] = []
    for file in ranked_files:
        file_score = compute_top_file_score(file, test_files_present)
        if file_score >= 70:
            risk_level = "high"
        elif file_score >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"

        top_files.append(
            TopRiskFile(
                filename=file.filename,
                risk_level=risk_level,
                reasons=build_file_reasons(file, test_files_present),
                patch_excerpt=build_patch_excerpt(file),
                changes=file.changes,
                areas=file.areas,
                is_sensitive=file.is_sensitive,
                blob_url=file.blob_url,
            )
        )

    return top_files


def build_result(
    metadata: GithubPrMetadata,
    files: list[ClassifiedFile],
    commits: list[GithubCommitSummary],
    signals: list[RiskSignal],
    cache_status: str = "live",
    total_files: int | None = None,
    partial_reasons: list[str] | None = None,
) -> PrAnalysisResult:
    score_payload = compute_score(signals)
    coverage = build_analysis_coverage(files, total_files or len(files), partial_reasons or [])

    return PrAnalysisResult(
        metadata=metadata,
        score=score_payload["score"],
        label=score_payload["label"],
        verdict=score_payload["verdict"],
        review_focus=build_review_focus(signals),
        affected_areas=build_affected_areas(files),
        risk_breakdown=score_payload["risk_breakdown"],
        triggered_signals=signals,
        recommendations=generate_recommendations(signals),
        changed_file_groups=build_file_groups(files),
        top_risk_files=build_top_risk_files(files),
        commits=commits,
        score_summary=ScoreSummary(**score_payload["score_summary"]),
        analysis_context=AnalysisContext(
            confidence_in_score=build_confidence_in_score(files, signals, commits, coverage, cache_status),
            summary=build_confidence_summary(files, commits, cache_status, coverage),
            limitations=analysis_limitations,
            data_sources=["GitHub PR metadata", "GitHub changed files", "GitHub commits", "deterministic rules engine"],
            cache_status=cache_status,
            coverage=coverage,
        ),
    )
