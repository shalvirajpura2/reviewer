from app.models.analysis import RiskBreakdownItem, RiskSignal


breakdown_labels = {
    "sensitive_code_risk": "Sensitive code risk",
    "dependency_risk": "Dependency risk",
    "migration_risk": "Migration risk",
    "config_risk": "Config risk",
    "test_risk": "Test risk",
    "blast_radius_risk": "Blast radius risk",
}


def clamp_score(score: int) -> int:
    return max(0, min(100, score))


def build_breakdown_summary(key: str, score: int) -> str:
    if score >= 20:
        return f"{breakdown_labels[key]} is elevated and should shape the review plan."
    if score >= 10:
        return f"{breakdown_labels[key]} is present but contained."
    return f"{breakdown_labels[key]} is limited in this pull request."


def compute_score(signals: list[RiskSignal]) -> dict[str, object]:
    base_score = 100
    total_penalty = sum(abs(signal.score_impact) for signal in signals if signal.score_impact < 0)
    total_relief = sum(signal.score_impact for signal in signals if signal.score_impact > 0)
    score = clamp_score(base_score - total_penalty + total_relief)

    if score >= 85:
        label = "high confidence"
        verdict = "mergeable with standard review"
    elif score >= 70:
        label = "moderate confidence"
        verdict = "mergeable with focused review"
    elif score >= 50:
        label = "low confidence"
        verdict = "review carefully before merge"
    else:
        label = "risky to merge"
        verdict = "needs deeper validation before merge"

    breakdown_map = {key: 0 for key in breakdown_labels}

    for signal in signals:
        if signal.score_impact < 0:
            breakdown_map[signal.breakdown_key] += abs(signal.score_impact)

    risk_breakdown = [
        RiskBreakdownItem(
            key=key,
            label=breakdown_labels[key],
            score=breakdown_score,
            summary=build_breakdown_summary(key, breakdown_score),
        )
        for key, breakdown_score in breakdown_map.items()
    ]

    return {
        "score": score,
        "label": label,
        "verdict": verdict,
        "risk_breakdown": risk_breakdown,
        "score_summary": {
            "base_score": base_score,
            "total_penalty": total_penalty,
            "total_relief": total_relief,
            "score_version": "v1.1-deterministic",
        },
    }
