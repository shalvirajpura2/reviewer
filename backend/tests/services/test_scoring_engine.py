from app.models.analysis import RiskSignal
from app.services.scoring_engine import compute_score


def test_compute_score_returns_high_confidence_for_light_risk():
    payload = compute_score(
        [
            RiskSignal(
                id="tests_present_for_risky_change",
                label="Tests changed alongside risky logic",
                severity="low",
                evidence=["tests/example.py"],
                score_impact=4,
                breakdown_key="test_risk",
            )
        ]
    )

    assert payload["score"] == 100
    assert payload["label"] == "high confidence"
    assert payload["verdict"] == "mergeable with standard review"


def test_compute_score_returns_risky_to_merge_for_heavy_penalties():
    payload = compute_score(
        [
            RiskSignal(
                id="migration_detected",
                label="Migration detected",
                severity="high",
                evidence=["db/migrations/001.sql"],
                score_impact=-18,
                breakdown_key="migration_risk",
            ),
            RiskSignal(
                id="sensitive_paths_changed",
                label="Sensitive paths changed",
                severity="high",
                evidence=["backend/app/auth.py"],
                score_impact=-16,
                breakdown_key="sensitive_code_risk",
            ),
            RiskSignal(
                id="large_pr_size",
                label="Large pull request",
                severity="high",
                evidence=["1400 total line changes"],
                score_impact=-21,
                breakdown_key="blast_radius_risk",
            ),
        ]
    )

    assert payload["score"] == 45
    assert payload["label"] == "risky to merge"
    assert payload["verdict"] == "needs deeper validation before merge"
