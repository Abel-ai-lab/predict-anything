from __future__ import annotations

from abel_invest import narrative, narrative_impl


PUBLIC_HELPERS_USED_BY_STRATEGY_DISCOVERY_TESTS = (
    "AGENT_CONTEXT_FILENAME",
    "EVENTS_HEADER",
    "EVIDENCE_LEDGER_FILENAME",
    "FRONTIER_JSON_FILENAME",
    "FRONTIER_MARKDOWN_FILENAME",
    "JOURNAL_GENERATED_HEADER_END",
    "RESEARCH_JOURNAL_FILENAME",
    "RESULTS_HEADER",
    "append_tsv_row",
    "branch_declaration_status",
    "branch_inputs_ready",
    "build_branch_context",
    "build_context_guide_markdown",
    "build_data_manifest_payload",
    "build_execution_constraints_payload",
    "build_probe_samples_payload",
    "build_research_journal_status",
    "build_runtime_profile_payload",
    "build_skill_dashboard_bundle",
    "check_session",
    "context_guide_path",
    "data_manifest_path",
    "dependencies_path",
    "evidence_runtime_facts",
    "execution_constraints_path",
    "graph_priority_warning_lines",
    "handle_workspace_command",
    "init_branch_dir",
    "init_session_dir",
    "journal_coverage_warning_lines",
    "load_branch_spec",
    "main",
    "persist_debug_snapshot",
    "post_skill_dashboard_bundle",
    "prepare_branch_inputs",
    "print_status",
    "probe_samples_path",
    "render_breadth_first_start_lines",
    "render_round_note",
    "render_session",
    "round_experiment_metadata",
    "run_branch_round",
    "runtime_profile_path",
    "subprocess",
    "write_branch_spec",
    "write_branch_state",
    "write_discovery",
    "write_readiness",
)


def test_narrative_impl_keeps_current_strategy_discovery_test_surface() -> None:
    missing = [
        name
        for name in PUBLIC_HELPERS_USED_BY_STRATEGY_DISCOVERY_TESTS
        if not hasattr(narrative_impl, name)
    ]

    assert missing == []


def test_narrative_package_delegates_current_helper_surface() -> None:
    mismatched = [
        name
        for name in PUBLIC_HELPERS_USED_BY_STRATEGY_DISCOVERY_TESTS
        if name != "main"
        if getattr(narrative, name) is not getattr(narrative_impl, name)
    ]

    assert mismatched == []
    assert callable(narrative.main)
