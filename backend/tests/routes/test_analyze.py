from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.models.analysis import GithubPrMetadata, PrAnalysisResult, PrPreviewResult
from app.models.analysis import AnalysisContext, AnalysisCoverage, ScoreSummary

client = TestClient(app)


def build_metadata():
    return GithubPrMetadata(
        owner="acme",
        repo="reviewer",
        pull_number=9,
        repo_full_name="acme/reviewer",
        title="Review API contract",
        author="shalv",
        author_avatar_url="https://example.com/avatar.png",
        base_branch="main",
        head_branch="feat/tests",
        commits=2,
        additions=22,
        deletions=4,
        changed_files=2,
        html_url="https://github.com/acme/reviewer/pull/9",
        created_at="2026-03-31T10:00:00Z",
        updated_at="2026-03-31T11:00:00Z",
    )


def test_preview_route_maps_invalid_request():
    response = client.post("/api/preview", json={"pr_url": "bad-url"})

    assert response.status_code == 400
    assert response.json()["error_code"] == "invalid_request"


def test_analyze_route_returns_request_id(monkeypatch):
    async def fake_analyze_pull_request(pr_url: str, client_key: str, force_refresh: bool):
        return PrAnalysisResult(
            metadata=build_metadata(),
            score=88,
            label="high confidence",
            verdict="mergeable with standard review",
            review_focus=["Sensitive paths changed"],
            affected_areas=["shared-core"],
            risk_breakdown=[],
            triggered_signals=[],
            recommendations=[],
            changed_file_groups=[],
            top_risk_files=[],
            commits=[],
            score_summary=ScoreSummary(base_score=100, total_penalty=12, total_relief=0, score_version="v1.2-deterministic"),
            analysis_context=AnalysisContext(
                confidence_in_score="high",
                summary="Built from backend evidence.",
                limitations=[],
                data_sources=["GitHub PR metadata"],
                cache_status="live",
                coverage=AnalysisCoverage(files_analyzed=2, total_files=2, patchless_files=0, is_partial=False, partial_reasons=[]),
            ),
        )

    monkeypatch.setattr("app.routes.analyze.analyze_pull_request", fake_analyze_pull_request)

    response = client.post("/api/analyze", json={"pr_url": "https://github.com/acme/reviewer/pull/9"}, headers={"x-request-id": "req-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "req-123"
    assert response.json()["analysis_context"]["summary"] == "Built from backend evidence."


def test_resolve_client_key_ignores_spoofed_client_id_header():
    request = SimpleNamespace(
        headers={"x-reviewer-client-id": "client-a", "x-forwarded-for": "1.1.1.1"},
        client=SimpleNamespace(host="8.8.4.4"),
    )

    from app.routes.analyze import resolve_client_key

    assert resolve_client_key(request) == "8.8.4.4"


def test_resolve_client_key_trusts_forwarded_ip_only_from_local_proxy():
    request = SimpleNamespace(
        headers={"x-forwarded-for": "8.8.8.8, 1.1.1.1"},
        client=SimpleNamespace(host="127.0.0.1"),
    )

    from app.routes.analyze import resolve_client_key

    assert resolve_client_key(request) == "8.8.8.8"
