from datetime import datetime, timedelta, timezone

from app.models.analysis import CheckRunSummary, ClassifiedFile, GithubCommitSummary, GithubPrMetadata, RiskSignal


historical_ci_cutoff_days = 30


def is_historical_merged_pr(metadata: GithubPrMetadata) -> bool:
    if not metadata.merged:
        return False

    timestamp = metadata.merged_at or metadata.updated_at
    try:
        parsed_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return False

    return datetime.now(timezone.utc) - parsed_at >= timedelta(days=historical_ci_cutoff_days)


def detect_signals(
    metadata: GithubPrMetadata,
    files: list[ClassifiedFile],
    commits: list[GithubCommitSummary],
    check_runs: list[CheckRunSummary] | None = None,
) -> list[RiskSignal]:
    signals: list[RiskSignal] = []
    sensitive_files = [file for file in files if file.is_sensitive]
    dependency_files = [file for file in files if "dependency" in file.areas]
    lockfiles = [file for file in files if "lockfile" in file.areas]
    migration_files = [file for file in files if "migration" in file.areas]
    config_files = [file for file in files if "config" in file.areas]
    test_files = [file for file in files if "test" in file.areas]
    shared_core_files = [file for file in files if "shared_core" in file.areas]
    middleware_files = [file for file in files if "middleware" in file.areas]
    frontend_files = [file for file in files if "frontend" in file.areas and "test" not in file.areas]
    backend_files = [file for file in files if "backend" in file.areas and "test" not in file.areas]
    code_files = [
        file
        for file in files
        if "docs" not in file.areas and "test" not in file.areas and "asset" not in file.areas
    ]
    patchless_code_files = [file for file in code_files if not file.patch]
    renamed_files = [file for file in files if file.status == "renamed"]
    generated_files = [file for file in files if "generated" in file.areas]
    docs_only = bool(files) and all("docs" in file.areas for file in files)
    tests_only = bool(test_files) and not code_files and not docs_only
    total_changes = metadata.additions + metadata.deletions
    blast_radius_score = sum(file.blast_radius_weight for file in files)
    symbol_heavy_files = [file for file in files if file.symbol_hints]
    average_changes_per_file = total_changes / max(1, metadata.changed_files)
    normalized_check_runs = check_runs or []
    historical_merged_pr = is_historical_merged_pr(metadata)
    failed_checks = [
        check_run
        for check_run in normalized_check_runs
        if (check_run.conclusion or "").lower() in {"failure", "timed_out", "cancelled", "action_required"}
    ]
    pending_checks = [
        check_run
        for check_run in normalized_check_runs
        if check_run.status.lower() in {"queued", "in_progress", "waiting", "requested", "pending"}
        and (check_run.conclusion or "").lower() not in {"success", "neutral", "skipped"}
    ]

    if docs_only:
        return [
            RiskSignal(
                id="docs_only_change",
                label="Docs-only pull request",
                severity="low",
                evidence=[file.filename for file in files[:3]],
                score_impact=0,
                breakdown_key="sensitive_code_risk",
            )
        ]

    if tests_only:
        return [
            RiskSignal(
                id="tests_only_change",
                label="Tests-only pull request",
                severity="low",
                evidence=[file.filename for file in test_files[:4]],
                score_impact=3,
                breakdown_key="test_risk",
            )
        ]

    if failed_checks:
        signals.append(
            RiskSignal(
                id="ci_checks_failed",
                label="CI checks are failing",
                severity="high",
                evidence=[
                    f"{check_run.name}: {check_run.conclusion or check_run.status}"
                    for check_run in failed_checks[:4]
                ],
                score_impact=-18,
                breakdown_key="test_risk",
            )
        )
    elif pending_checks:
        signals.append(
            RiskSignal(
                id="ci_checks_pending",
                label="CI checks are still running",
                severity="medium",
                evidence=[f"{check_run.name}: {check_run.status}" for check_run in pending_checks[:4]],
                score_impact=-8,
                breakdown_key="test_risk",
            )
        )
    elif code_files and not normalized_check_runs and not historical_merged_pr:
        signals.append(
            RiskSignal(
                id="ci_checks_missing",
                label="No CI checks reported for this commit",
                severity="medium",
                evidence=["GitHub did not return check runs for the PR head commit"],
                score_impact=-10,
                breakdown_key="test_risk",
            )
        )
    if sensitive_files:
        signals.append(
            RiskSignal(
                id="sensitive_paths_changed",
                label="Sensitive paths changed",
                severity="high" if len(sensitive_files) > 2 else "medium",
                evidence=[file.filename for file in sensitive_files[:4]],
                score_impact=-16 if len(sensitive_files) > 2 else -10,
                breakdown_key="sensitive_code_risk",
            )
        )

    if symbol_heavy_files:
        signals.append(
            RiskSignal(
                id="patch_structure_hints_detected",
                label="Patch structure hints detected",
                severity="medium",
                evidence=[
                    f"{file.filename}: {', '.join(file.symbol_hints[:3])}"
                    for file in symbol_heavy_files[:3]
                ],
                score_impact=-5,
                breakdown_key="sensitive_code_risk",
            )
        )

    if dependency_files:
        dependency_severity = "high" if len(dependency_files) >= 3 and not lockfiles else "medium"
        dependency_impact = -12 if dependency_severity == "high" else -10
        signals.append(
            RiskSignal(
                id="dependency_files_updated",
                label="Dependency files updated",
                severity=dependency_severity,
                evidence=[file.filename for file in dependency_files[:4]],
                score_impact=dependency_impact,
                breakdown_key="dependency_risk",
            )
        )

    if migration_files:
        signals.append(
            RiskSignal(
                id="migration_detected",
                label="Migration detected",
                severity="high",
                evidence=[file.filename for file in migration_files[:4]],
                score_impact=-18,
                breakdown_key="migration_risk",
            )
        )

    if config_files:
        signals.append(
            RiskSignal(
                id="config_files_changed",
                label="Config or workflow files changed",
                severity="medium",
                evidence=[file.filename for file in config_files[:4]],
                score_impact=-8,
                breakdown_key="config_risk",
            )
        )

    if config_files and code_files:
        signals.append(
            RiskSignal(
                id="runtime_and_config_changed",
                label="Runtime and config changed together",
                severity="medium",
                evidence=[file.filename for file in (config_files + code_files)[:4]],
                score_impact=-7,
                breakdown_key="config_risk",
            )
        )

    if shared_core_files or blast_radius_score >= 12:
        is_high_blast_radius = len(shared_core_files) > 1 or blast_radius_score >= 18
        signals.append(
            RiskSignal(
                id="shared_core_module_touched",
                label="Shared or high-impact code touched",
                severity="high" if is_high_blast_radius else "medium",
                evidence=[file.filename for file in shared_core_files[:4]] or [f"blast radius score {blast_radius_score}"],
                score_impact=-14 if is_high_blast_radius else -9,
                breakdown_key="blast_radius_risk",
            )
        )

    if middleware_files:
        signals.append(
            RiskSignal(
                id="middleware_changed",
                label="Middleware behavior changed",
                severity="medium",
                evidence=[file.filename for file in middleware_files[:4]],
                score_impact=-8,
                breakdown_key="sensitive_code_risk",
            )
        )

    if frontend_files and backend_files and metadata.changed_files >= 6:
        signals.append(
            RiskSignal(
                id="cross_stack_change",
                label="Frontend and backend changed together",
                severity="medium",
                evidence=[file.filename for file in (frontend_files[:2] + backend_files[:2])],
                score_impact=-7,
                breakdown_key="blast_radius_risk",
            )
        )

    if dependency_files and not test_files:
        signals.append(
            RiskSignal(
                id="dependencies_without_tests",
                label="Dependencies changed without test updates",
                severity="medium",
                evidence=[file.filename for file in dependency_files[:3]],
                score_impact=-5,
                breakdown_key="dependency_risk",
            )
        )

    if len(lockfiles) >= 2 and len(lockfiles) == len(dependency_files):
        signals.append(
            RiskSignal(
                id="lockfile_only_dependency_refresh",
                label="Lockfile-heavy dependency refresh",
                severity="low",
                evidence=[file.filename for file in lockfiles[:3]],
                score_impact=2,
                breakdown_key="dependency_risk",
            )
        )

    if patchless_code_files:
        signals.append(
            RiskSignal(
                id="patchless_code_changes",
                label="Some code changes lack patch visibility",
                severity="high" if len(patchless_code_files) >= 3 else "medium",
                evidence=[file.filename for file in patchless_code_files[:4]],
                score_impact=-8 if len(patchless_code_files) >= 3 else -5,
                breakdown_key="sensitive_code_risk",
            )
        )

    if len(renamed_files) >= 3:
        signals.append(
            RiskSignal(
                id="rename_heavy_refactor",
                label="Rename-heavy refactor",
                severity="medium",
                evidence=[file.filename for file in renamed_files[:4]],
                score_impact=-6,
                breakdown_key="blast_radius_risk",
            )
        )

    if metadata.changed_files >= 20:
        signals.append(
            RiskSignal(
                id="high_file_count",
                label="High file count",
                severity="high" if metadata.changed_files >= 40 else "medium",
                evidence=[f"{metadata.changed_files} files changed"],
                score_impact=-12 if metadata.changed_files >= 40 else -7,
                breakdown_key="blast_radius_risk",
            )
        )

    if total_changes >= 600:
        signals.append(
            RiskSignal(
                id="large_pr_size",
                label="Large pull request",
                severity="high" if total_changes >= 1200 else "medium",
                evidence=[f"{total_changes} total line changes"],
                score_impact=-12 if total_changes >= 1200 else -8,
                breakdown_key="blast_radius_risk",
            )
        )

    if metadata.changed_files >= 12 and average_changes_per_file <= 18:
        signals.append(
            RiskSignal(
                id="broad_shallow_change",
                label="Broad but shallow change spread",
                severity="medium",
                evidence=[f"{metadata.changed_files} files with about {round(average_changes_per_file)} changes each on average"],
                score_impact=-6,
                breakdown_key="blast_radius_risk",
            )
        )

    if metadata.commits >= 15 or len(commits) >= 15:
        signals.append(
            RiskSignal(
                id="high_commit_count",
                label="Many commits in this pull request",
                severity="medium",
                evidence=[f"{max(metadata.commits, len(commits))} commits in review scope"],
                score_impact=-5,
                breakdown_key="blast_radius_risk",
            )
        )

    if sensitive_files and not test_files:
        signals.append(
            RiskSignal(
                id="no_tests_for_sensitive_change",
                label="Risky changes landed without tests",
                severity="high",
                evidence=[file.filename for file in sensitive_files[:3]],
                score_impact=-14,
                breakdown_key="test_risk",
            )
        )

    if sensitive_files and test_files:
        signals.append(
            RiskSignal(
                id="tests_present_for_risky_change",
                label="Tests changed alongside risky logic",
                severity="low",
                evidence=[file.filename for file in test_files[:4]],
                score_impact=4,
                breakdown_key="test_risk",
            )
        )

    if generated_files and not test_files and len(generated_files) >= 2 and len(code_files) >= len(generated_files):
        signals.append(
            RiskSignal(
                id="generated_output_changed",
                label="Generated output changed with implementation",
                severity="low",
                evidence=[file.filename for file in generated_files[:3]],
                score_impact=-2,
                breakdown_key="blast_radius_risk",
            )
        )

    if not test_files and len(code_files) >= 5:
        signals.append(
            RiskSignal(
                id="implementation_without_tests",
                label="Implementation changed without nearby tests",
                severity="medium",
                evidence=[file.filename for file in code_files[:4]],
                score_impact=-8,
                breakdown_key="test_risk",
            )
        )
    elif not test_files and metadata.changed_files >= 8:
        signals.append(
            RiskSignal(
                id="no_tests_changed",
                label="No tests changed",
                severity="medium",
                evidence=["No test files were updated in this pull request"],
                score_impact=-6,
                breakdown_key="test_risk",
            )
        )

    return signals
