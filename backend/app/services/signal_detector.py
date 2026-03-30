from app.models.analysis import ClassifiedFile, GithubPrMetadata, RiskSignal


def detect_signals(metadata: GithubPrMetadata, files: list[ClassifiedFile]) -> list[RiskSignal]:
    signals: list[RiskSignal] = []
    sensitive_files = [file for file in files if file.is_sensitive]
    dependency_files = [file for file in files if "dependency" in file.areas]
    migration_files = [file for file in files if "migration" in file.areas]
    config_files = [file for file in files if "config" in file.areas]
    test_files = [file for file in files if "test" in file.areas]
    shared_core_files = [file for file in files if "shared_core" in file.areas]
    middleware_files = [file for file in files if "middleware" in file.areas]
    frontend_files = [file for file in files if "frontend" in file.areas and "test" not in file.areas]
    backend_files = [file for file in files if "backend" in file.areas and "test" not in file.areas]
    code_files = [file for file in files if "docs" not in file.areas and "test" not in file.areas]
    docs_only = bool(files) and all("docs" in file.areas for file in files)
    total_changes = metadata.additions + metadata.deletions
    blast_radius_score = sum(file.blast_radius_weight for file in files)
    symbol_heavy_files = [file for file in files if file.symbol_hints]

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
        signals.append(
            RiskSignal(
                id="dependency_files_updated",
                label="Dependency files updated",
                severity="medium",
                evidence=[file.filename for file in dependency_files[:4]],
                score_impact=-10,
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
        signals.append(
            RiskSignal(
                id="shared_core_module_touched",
                label="Shared or high-impact code touched",
                severity="high" if len(shared_core_files) > 1 or blast_radius_score >= 18 else "medium",
                evidence=[file.filename for file in shared_core_files[:4]] or [f"blast radius score {blast_radius_score}"],
                score_impact=-14 if len(shared_core_files) > 1 or blast_radius_score >= 18 else -9,
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
