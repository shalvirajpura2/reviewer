from app.models.analysis import RecommendationItem, RiskSignal


recommendation_map = {
    "ci_checks_failed": RecommendationItem(
        id="fix_ci_before_merge",
        title="Fix failing CI before merge",
        detail="At least one GitHub check failed on the PR head commit, so resolve that failure before treating the score as merge-ready.",
        priority="now",
    ),
    "ci_checks_pending": RecommendationItem(
        id="wait_for_ci_checks",
        title="Wait for CI checks to finish",
        detail="Some GitHub checks are still running, so hold merge approval until those safeguards finish.",
        priority="now",
    ),
    "ci_checks_missing": RecommendationItem(
        id="verify_ci_coverage",
        title="Verify CI coverage for this PR",
        detail="GitHub did not report check runs for the PR head commit, so confirm whether CI is configured and whether required checks are expected.",
        priority="now",
    ),
    "sensitive_paths_changed": RecommendationItem(
        id="review_sensitive_logic",
        title="Review sensitive logic carefully",
        detail="Validate auth, permissions, payments, or data-layer behavior with edge cases in mind.",
        priority="now",
    ),
    "patch_structure_hints_detected": RecommendationItem(
        id="inspect_patch_structure",
        title="Inspect structural code changes",
        detail="Look closely at imports, permission paths, middleware, or database-related hunks before merge.",
        priority="now",
    ),
    "dependency_files_updated": RecommendationItem(
        id="review_dependencies",
        title="Review dependency updates",
        detail="Check release notes, lockfile changes, and transitive risk before merging.",
        priority="now",
    ),
    "dependencies_without_tests": RecommendationItem(
        id="exercise_dependency_paths",
        title="Exercise dependency-affected paths",
        detail="When dependencies change without test updates, run the flows most exposed to version and lockfile drift.",
        priority="soon",
    ),
    "lockfile_only_dependency_refresh": RecommendationItem(
        id="scan_lockfile_refresh",
        title="Scan the dependency refresh scope",
        detail="This looks closer to a lockfile refresh, so confirm whether package manifests or runtime behavior changed alongside it.",
        priority="nice_to_have",
    ),
    "migration_detected": RecommendationItem(
        id="validate_migration_rollout",
        title="Validate migration rollout and rollback",
        detail="Confirm the deployment order, data safety, and rollback path for schema changes.",
        priority="now",
    ),
    "config_files_changed": RecommendationItem(
        id="verify_config_in_staging",
        title="Verify config changes in staging",
        detail="Exercise the changed environment or workflow path and verify CI checks before approving merge.",
        priority="soon",
    ),
    "runtime_and_config_changed": RecommendationItem(
        id="trace_runtime_with_config",
        title="Trace the runtime path behind config edits",
        detail="When code and configuration move together, confirm the changed settings still match the new runtime behavior.",
        priority="now",
    ),
    "shared_core_module_touched": RecommendationItem(
        id="request_owner_review",
        title="Request owner review for shared code",
        detail="Shared or core edits can widen blast radius, so bring in the relevant code owner.",
        priority="now",
    ),
    "middleware_changed": RecommendationItem(
        id="inspect_middleware_paths",
        title="Inspect middleware behavior",
        detail="Check routing, guards, and request interception paths that may affect multiple flows.",
        priority="soon",
    ),
    "cross_stack_change": RecommendationItem(
        id="walk_the_full_user_flow",
        title="Walk the full user flow across layers",
        detail="When frontend and backend change together, test the end-to-end path instead of reviewing each layer in isolation.",
        priority="now",
    ),
    "patchless_code_changes": RecommendationItem(
        id="open_hidden_diff_context",
        title="Open files with limited diff visibility",
        detail="Some changed code came back without patch hunks, so inspect the full file view in GitHub before trusting the score completely.",
        priority="now",
    ),
    "rename_heavy_refactor": RecommendationItem(
        id="verify_refactor_mappings",
        title="Verify rename and move intent",
        detail="A rename-heavy PR can hide behavior changes, so confirm each moved file still maps to the same runtime responsibility.",
        priority="soon",
    ),
    "broad_shallow_change": RecommendationItem(
        id="review_by_surface_area",
        title="Review by surface area, not commit order",
        detail="A wide but shallow PR is easy to skim past, so group the review by risk area and ownership instead of scanning linearly.",
        priority="soon",
    ),
    "high_commit_count": RecommendationItem(
        id="check_final_state_over_commit_story",
        title="Check the final state, not just the commit story",
        detail="A long commit train can obscure the final behavior, so review the merged diff and key files directly.",
        priority="soon",
    ),
    "generated_output_changed": RecommendationItem(
        id="confirm_generated_artifacts",
        title="Confirm generated artifacts are intentional",
        detail="Generated output changed with implementation, so verify whether those files are expected build artifacts or accidental noise.",
        priority="nice_to_have",
    ),
    "no_tests_for_sensitive_change": RecommendationItem(
        id="add_regression_tests",
        title="Add tests for risky paths",
        detail="Sensitive logic changed without test coverage updates, so ask for targeted regression tests and confirm CI is green.",
        priority="now",
    ),
    "implementation_without_tests": RecommendationItem(
        id="ask_for_behavior_checks",
        title="Ask for behavior checks or targeted tests",
        detail="Implementation changed across several files without test updates, so confirm how the team validated the behavior and which CI checks covered it.",
        priority="soon",
    ),
    "no_tests_changed": RecommendationItem(
        id="confirm_test_strategy",
        title="Confirm test strategy",
        detail="No tests changed, so verify whether the current suite and CI checks still cover the edited behavior.",
        priority="soon",
    ),
    "high_file_count": RecommendationItem(
        id="split_or_stage_review",
        title="Stage the review by area",
        detail="A broad file footprint makes review harder, so split the review across ownership boundaries.",
        priority="soon",
    ),
    "large_pr_size": RecommendationItem(
        id="focus_on_high_risk_hunks",
        title="Focus on high-risk hunks first",
        detail="Start with migrations, shared modules, config, and auth surfaces before scanning lower-risk changes.",
        priority="soon",
    ),
}


def generate_recommendations(signals: list[RiskSignal]) -> list[RecommendationItem]:
    collected: dict[str, RecommendationItem] = {}

    for signal in signals:
        recommendation = recommendation_map.get(signal.id)
        if recommendation:
            collected[recommendation.id] = recommendation

    if not collected:
        collected["standard_review"] = RecommendationItem(
            id="standard_review",
            title="Run a standard merge review",
            detail="The current signals are limited, so a normal code review pass should be sufficient.",
            priority="nice_to_have",
        )

    priority_order = {"now": 0, "soon": 1, "nice_to_have": 2}
    return sorted(collected.values(), key=lambda item: priority_order[item.priority])
