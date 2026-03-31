from app.models.analysis import RiskSignal
from app.services.recommendation_engine import generate_recommendations


def test_generate_recommendations_sorts_by_priority_and_dedupes():
    signals = [
        RiskSignal(
            id="config_files_changed",
            label="Config or workflow files changed",
            severity="medium",
            evidence=[".github/workflows/deploy.yml"],
            score_impact=-8,
            breakdown_key="config_risk",
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
            id="sensitive_paths_changed",
            label="Sensitive paths changed",
            severity="high",
            evidence=["backend/app/session.py"],
            score_impact=-16,
            breakdown_key="sensitive_code_risk",
        ),
    ]

    recommendations = generate_recommendations(signals)

    assert [item.id for item in recommendations] == ["review_sensitive_logic", "verify_config_in_staging"]


def test_generate_recommendations_returns_standard_review_when_empty():
    recommendations = generate_recommendations([])

    assert len(recommendations) == 1
    assert recommendations[0].id == "standard_review"
