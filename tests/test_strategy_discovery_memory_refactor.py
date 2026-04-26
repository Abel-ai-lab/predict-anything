from __future__ import annotations

import json
import subprocess
from argparse import Namespace
from pathlib import Path

from abel_strategy_discovery import narrative_impl as ni


def _sample_selected_inputs() -> list[dict]:
    return [
        {"node_id": "AAPL.price", "asset": "AAPL", "field": "price", "roles": ["selected"]},
    ]


def test_memory_scaffold_and_views(tmp_path: Path) -> None:
    session = ni.init_session_dir("TSLA", "tsla-v1", tmp_path / "research")
    branch = ni.init_branch_dir(session, "graph-v1")
    branch_spec = ni.load_branch_spec(branch)

    required_session_files = [
        ni.MEMORY_MANIFEST_FILENAME,
        ni.MEMORY_BRANCHES_FILENAME,
        ni.MEMORY_ROUNDS_FILENAME,
        ni.MEMORY_VALIDATIONS_FILENAME,
        ni.MEMORY_INSIGHTS_FILENAME,
        ni.MEMORY_LINKS_FILENAME,
        f"{ni.MEMORY_VIEWS_DIRNAME}/{ni.MEMORY_OVERVIEW_FILENAME}",
        f"{ni.MEMORY_VIEWS_DIRNAME}/{ni.MEMORY_COMPARE_FILENAME}",
    ]
    for rel in required_session_files:
        assert (session / rel).exists(), rel

    memory_text = (branch / "memory.md").read_text(encoding="utf-8")
    assert "## Branch Profile" in memory_text
    assert "## Compare Candidates" in memory_text

    branch_rows = ni.read_tsv_rows(session / ni.MEMORY_BRANCHES_FILENAME)
    assert len(branch_rows) == 1
    assert branch_rows[0]["branch_id"] == "graph-v1"
    assert branch_rows[0]["source_type"] == "causal"
    assert branch_spec["target_asset"] == "TSLA"
    assert branch_spec["target_node"] == "TSLA.price"
    assert "selected_inputs" in branch_spec


def test_manual_insight_and_link_survive_render(tmp_path: Path) -> None:
    session = ni.init_session_dir("TSLA", "tsla-v2", tmp_path / "research")
    causal = ni.init_branch_dir(session, "graph-v1")
    baseline = ni.init_branch_dir(session, "baseline-v1")

    baseline_spec = ni.load_branch_spec(baseline)
    baseline_spec["source_type"] = "baseline"
    baseline_spec["method_family"] = "rule"
    ni.write_branch_spec(baseline, baseline_spec)
    ni.render_session(session)

    ni.record_manual_insight(
        Namespace(
            branch=str(causal),
            scope="branch",
            kind="pattern",
            text="Driver concentration matters more than raw parent count.",
            rule="Prefer a tighter driver set before opening a new sibling branch.",
            confidence="high",
            round_id="",
        )
    )
    ni.record_branch_link(
        Namespace(
            from_branch=str(causal),
            to_branch=str(baseline),
            type="candidate_compare",
            match_score="0.95",
            match_basis="same ticker and same requested start",
            status="candidate",
            note="manual compare seed",
        )
    )

    insights = ni.read_tsv_rows(session / ni.MEMORY_INSIGHTS_FILENAME)
    assert any(
        row["origin"] == "manual"
        and row["statement"] == "Driver concentration matters more than raw parent count."
        for row in insights
    )

    links = ni.read_tsv_rows(session / ni.MEMORY_LINKS_FILENAME)
    assert any(
        row["origin"] == "manual"
        and row["from_branch_id"] == "graph-v1"
        and row["to_branch_id"] == "baseline-v1"
        for row in links
    )

    ni.render_session(session)

    insights = ni.read_tsv_rows(session / ni.MEMORY_INSIGHTS_FILENAME)
    links = ni.read_tsv_rows(session / ni.MEMORY_LINKS_FILENAME)
    assert any(row["origin"] == "manual" for row in insights)
    assert any(row["origin"] == "manual" for row in links)


def test_run_branch_round_updates_memory_and_status(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    session = ni.init_session_dir("TSLA", "tsla-v3", tmp_path / "research")
    causal = ni.init_branch_dir(session, "graph-v1")
    baseline = ni.init_branch_dir(session, "baseline-v1")

    baseline_spec = ni.load_branch_spec(baseline)
    baseline_spec["source_type"] = "baseline"
    baseline_spec["method_family"] = "rule"
    ni.write_branch_spec(baseline, baseline_spec)

    for branch in (causal, baseline):
        deps_path = ni.dependencies_path(branch)
        deps_path.parent.mkdir(parents=True, exist_ok=True)
        dependencies = {
            "version": 2,
            "branch_id": branch.name,
            "target_asset": "TSLA",
            "target_node": "TSLA.price",
            "selected_inputs": _sample_selected_inputs(),
            "requested_start": "2020-01-01",
            "cache": {
                "adapter": "abel",
                "timeframe": "1d",
                "profile": "daily",
                "results": [
                    {
                        "symbol": "TSLA",
                        "ok": True,
                        "row_count": 120,
                        "available_range": {"start": "2020-01-01", "end": "2020-12-31"},
                    },
                    {
                        "symbol": "AAPL",
                        "ok": True,
                        "row_count": 120,
                        "available_range": {"start": "2020-01-01", "end": "2020-12-31"},
                    },
                ],
            },
        }
        deps_path.write_text(json.dumps(dependencies), encoding="utf-8")
        runtime_profile = ni.build_runtime_profile_payload(
            target_asset="TSLA",
            target_node="TSLA.price",
        )
        execution_constraints = ni.build_execution_constraints_payload(ni.load_branch_spec(branch))
        data_manifest = ni.build_data_manifest_payload(
            target_asset="TSLA",
            target_node="TSLA.price",
            selected_inputs=ni.branch_selected_inputs(
                {"selected_inputs": _sample_selected_inputs()}
            ),
            cache_payload=dependencies["cache"],
            readiness={},
        )
        window_report = ni.build_window_availability_report(
            requested_start="2020-01-01",
            data_manifest=data_manifest,
            overlap_mode="target_only",
        )
        probe_samples = ni.build_probe_samples_payload(
            target_asset="TSLA",
            requested_start="2020-01-01",
            data_manifest=data_manifest,
            window_report=window_report,
        )
        ni.runtime_profile_path(branch).write_text(
            json.dumps(runtime_profile),
            encoding="utf-8",
        )
        ni.execution_constraints_path(branch).write_text(
            json.dumps(execution_constraints),
            encoding="utf-8",
        )
        ni.data_manifest_path(branch).write_text(
            json.dumps(data_manifest),
            encoding="utf-8",
        )
        ni.window_availability_path(branch).write_text(
            json.dumps(window_report),
            encoding="utf-8",
        )
        ni.probe_samples_path(branch).write_text(
            json.dumps(probe_samples),
            encoding="utf-8",
        )
        ni.context_guide_path(branch).write_text(
            ni.build_context_guide_markdown(
                target_asset="TSLA",
                target_node="TSLA.price",
                runtime_profile=runtime_profile,
                execution_constraints=execution_constraints,
                data_manifest=data_manifest,
                window_report=window_report,
            ),
            encoding="utf-8",
        )
        ni.persist_prepared_branch_contract(branch, ni.load_discovery(session))

    def fake_subprocess_run(command, cwd=None, capture_output=None, text=None, env=None, check=False, input=None):
        if "evaluate" in command:
            workdir = Path(command[command.index("--workdir") + 1])
            result_path = Path(command[command.index("--output-json") + 1])
            report_path = Path(command[command.index("--output-md") + 1])
            handoff_path = Path(command[command.index("--output-handoff") + 1])
            if workdir.name == "baseline-v1":
                sharpe = 1.8
                lo_adj = 2.4
                total_return = 0.42
            else:
                sharpe = 2.6
                lo_adj = 3.1
                total_return = 0.63
            payload = {
                "verdict": "PASS",
                "score": "7/7",
                "failures": [],
                "warnings": [],
                "profile": "crypto_daily",
                "K": 1,
                "metrics": {
                    "sharpe": sharpe,
                    "lo_adjusted": lo_adj,
                    "position_ic": 0.0,
                    "omega": 1.5,
                    "total_return": total_return,
                    "max_dd": -0.08,
                },
                "requested_window": {"start": "2020-01-01", "end": None},
                "effective_window": {"start": "2020-01-01", "end": "2020-12-31"},
                "diagnostics": {
                    "failure_signature": "clean_pass",
                    "runtime_stage": "evaluate",
                    "signal": {"active_days": 120, "total_days": 252},
                    "hints": ["carry forward the current signal family"],
                },
            }
            result_path.write_text(json.dumps(payload), encoding="utf-8")
            report_path.write_text("# validation\n", encoding="utf-8")
            handoff_path.write_text(json.dumps({"ok": True}), encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(ni.subprocess, "run", fake_subprocess_run)

    ni.run_branch_round(
        Namespace(
            branch=str(baseline),
            mode="explore",
            description="baseline momentum rule",
            input_note="",
            hypothesis="baseline trend persistence",
            expected_signal="",
            trigger="baseline seed",
            change_summary="first baseline pass",
            time_spent_min="12",
            summary="",
            next_step="compare against causal branch",
            action=[],
            python_bin=None,
            allow_untouched_template=True,
        )
    )
    ni.run_branch_round(
        Namespace(
            branch=str(causal),
            mode="explore",
            description="causal driver vote",
            input_note="",
            hypothesis="top discovered parents vote the target",
            expected_signal="",
            trigger="graph discovery seed",
            change_summary="first causal pass",
            time_spent_min="15",
            summary="",
            next_step="compare against baseline branch",
            action=[],
            python_bin=None,
            allow_untouched_template=True,
        )
    )

    validations = ni.read_tsv_rows(session / ni.MEMORY_VALIDATIONS_FILENAME)
    rounds = ni.read_tsv_rows(session / ni.MEMORY_ROUNDS_FILENAME)
    links = ni.read_tsv_rows(session / ni.MEMORY_LINKS_FILENAME)
    assert len(validations) == 2
    assert len(rounds) == 2
    assert any(
        row["link_type"] == "candidate_compare"
        and row["from_branch_id"] == "graph-v1"
        and row["to_branch_id"] == "baseline-v1"
        for row in links
    )

    compare_view = (session / ni.MEMORY_VIEWS_DIRNAME / ni.MEMORY_COMPARE_FILENAME).read_text(
        encoding="utf-8"
    )
    assert "graph-v1" in compare_view
    assert "baseline-v1" in compare_view

    ni.print_status(session)
    status_output = capsys.readouterr().out
    assert "Memory:" in status_output

    assert ni.check_session(session, strict=False) == 0


def test_run_branch_round_persists_experiment_metadata_to_memory_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    session = ni.init_session_dir("TSLA", "tsla-v4-metadata", tmp_path / "research")
    branch = ni.init_branch_dir(session, "baseline-v1")

    spec = ni.load_branch_spec(branch)
    spec["source_type"] = "baseline"
    spec["method_family"] = "rule"
    ni.write_branch_spec(branch, spec)

    deps_path = ni.dependencies_path(branch)
    deps_path.parent.mkdir(parents=True, exist_ok=True)
    dependencies = {
        "version": 2,
        "branch_id": branch.name,
        "target_asset": "TSLA",
        "target_node": "TSLA.price",
        "selected_inputs": _sample_selected_inputs(),
        "requested_start": "2020-01-01",
        "cache": {
            "adapter": "abel",
            "timeframe": "1d",
            "profile": "daily",
            "results": [
                {
                    "symbol": "TSLA",
                    "ok": True,
                    "row_count": 120,
                    "available_range": {"start": "2020-01-01", "end": "2020-12-31"},
                },
                {
                    "symbol": "AAPL",
                    "ok": True,
                    "row_count": 120,
                    "available_range": {"start": "2020-01-01", "end": "2020-12-31"},
                },
            ],
        },
    }
    deps_path.write_text(json.dumps(dependencies), encoding="utf-8")
    runtime_profile = ni.build_runtime_profile_payload(
        target_asset="TSLA",
        target_node="TSLA.price",
    )
    execution_constraints = ni.build_execution_constraints_payload(ni.load_branch_spec(branch))
    data_manifest = ni.build_data_manifest_payload(
        target_asset="TSLA",
        target_node="TSLA.price",
        selected_inputs=ni.branch_selected_inputs({"selected_inputs": _sample_selected_inputs()}),
        cache_payload=dependencies["cache"],
        readiness={},
    )
    window_report = ni.build_window_availability_report(
        requested_start="2020-01-01",
        data_manifest=data_manifest,
        overlap_mode="target_only",
    )
    probe_samples = ni.build_probe_samples_payload(
        target_asset="TSLA",
        requested_start="2020-01-01",
        data_manifest=data_manifest,
        window_report=window_report,
    )
    ni.runtime_profile_path(branch).write_text(json.dumps(runtime_profile), encoding="utf-8")
    ni.execution_constraints_path(branch).write_text(
        json.dumps(execution_constraints),
        encoding="utf-8",
    )
    ni.data_manifest_path(branch).write_text(json.dumps(data_manifest), encoding="utf-8")
    ni.window_availability_path(branch).write_text(json.dumps(window_report), encoding="utf-8")
    ni.probe_samples_path(branch).write_text(json.dumps(probe_samples), encoding="utf-8")
    ni.context_guide_path(branch).write_text(
        ni.build_context_guide_markdown(
            target_asset="TSLA",
            target_node="TSLA.price",
            runtime_profile=runtime_profile,
            execution_constraints=execution_constraints,
            data_manifest=data_manifest,
            window_report=window_report,
        ),
        encoding="utf-8",
    )
    ni.persist_prepared_branch_contract(branch, ni.load_discovery(session))

    monkeypatch.setenv("ABEL_EXPERIMENT_PROTOCOL_ID", "alpha-exec-sandbox-v1")
    monkeypatch.setenv("ABEL_EXPERIMENT_MODE", "baseline")
    monkeypatch.setenv("ABEL_EXPERIMENT_ROUND_BUDGET", "10")
    monkeypatch.setenv("ABEL_SKILLS_COMMIT", "skills-sha-123")
    monkeypatch.setenv("ABEL_EDGE_COMMIT", "edge-sha-456")

    def fake_subprocess_run(command, cwd=None, capture_output=None, text=None, env=None, check=False, input=None):
        if "evaluate" in command:
            result_path = Path(command[command.index("--output-json") + 1])
            report_path = Path(command[command.index("--output-md") + 1])
            handoff_path = Path(command[command.index("--output-handoff") + 1])
            payload = {
                "verdict": "PASS",
                "score": "7/7",
                "failures": [],
                "warnings": [],
                "profile": "equity_daily",
                "K": 1,
                "metrics": {
                    "sharpe": 2.1,
                    "lo_adjusted": 2.6,
                    "position_ic": 0.0,
                    "omega": 1.4,
                    "total_return": 0.34,
                    "max_dd": -0.09,
                },
                "requested_window": {"start": "2020-01-01", "end": None},
                "effective_window": {"start": "2020-01-01", "end": "2020-12-31"},
                "diagnostics": {
                    "failure_signature": "clean_pass",
                    "runtime_stage": "evaluate",
                    "signal": {"active_days": 120, "total_days": 252},
                    "hints": ["keep going"],
                },
            }
            result_path.write_text(json.dumps(payload), encoding="utf-8")
            report_path.write_text("# validation\n", encoding="utf-8")
            handoff_path.write_text(json.dumps({"ok": True}), encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(ni.subprocess, "run", fake_subprocess_run)

    ni.run_branch_round(
        Namespace(
            branch=str(branch),
            mode="explore",
            description="baseline momentum rule",
            input_note="",
            hypothesis="baseline trend persistence",
            expected_signal="",
            trigger="baseline seed",
            change_summary="first baseline pass",
            time_spent_min="12",
            summary="",
            next_step="continue baseline exploration",
            action=[],
            python_bin=None,
            allow_untouched_template=True,
        )
    )

    context = json.loads((branch / "outputs" / "round-001-alpha-context.json").read_text(encoding="utf-8"))
    manifest = json.loads((session / ni.MEMORY_MANIFEST_FILENAME).read_text(encoding="utf-8"))

    expected = {
        "protocol_id": "alpha-exec-sandbox-v1",
        "experiment_mode": "baseline",
        "round_budget": "10",
        "abel_skills_commit": "skills-sha-123",
        "abel_edge_commit": "edge-sha-456",
    }
    assert context["experiment"] == expected
    assert manifest["experiment"] == expected


def test_memory_manifest_uses_latest_round_experiment_metadata_without_mixing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    session = ni.init_session_dir("TSLA", "tsla-v5-metadata", tmp_path / "research")
    first = ni.init_branch_dir(session, "baseline-v1")
    second = ni.init_branch_dir(session, "graph-v1")

    second_spec = ni.load_branch_spec(second)
    second_spec["source_type"] = "causal"
    second_spec["method_family"] = "graph"
    ni.write_branch_spec(second, second_spec)

    for branch in (first, second):
        deps_path = ni.dependencies_path(branch)
        deps_path.parent.mkdir(parents=True, exist_ok=True)
        dependencies = {
            "version": 2,
            "branch_id": branch.name,
            "target_asset": "TSLA",
            "target_node": "TSLA.price",
            "selected_inputs": _sample_selected_inputs(),
            "requested_start": "2020-01-01",
            "cache": {
                "adapter": "abel",
                "timeframe": "1d",
                "profile": "daily",
                "results": [
                    {
                        "symbol": "TSLA",
                        "ok": True,
                        "row_count": 120,
                        "available_range": {"start": "2020-01-01", "end": "2020-12-31"},
                    },
                    {
                        "symbol": "AAPL",
                        "ok": True,
                        "row_count": 120,
                        "available_range": {"start": "2020-01-01", "end": "2020-12-31"},
                    },
                ],
            },
        }
        deps_path.write_text(json.dumps(dependencies), encoding="utf-8")
        runtime_profile = ni.build_runtime_profile_payload(
            target_asset="TSLA",
            target_node="TSLA.price",
        )
        execution_constraints = ni.build_execution_constraints_payload(ni.load_branch_spec(branch))
        data_manifest = ni.build_data_manifest_payload(
            target_asset="TSLA",
            target_node="TSLA.price",
            selected_inputs=ni.branch_selected_inputs({"selected_inputs": _sample_selected_inputs()}),
            cache_payload=dependencies["cache"],
            readiness={},
        )
        window_report = ni.build_window_availability_report(
            requested_start="2020-01-01",
            data_manifest=data_manifest,
            overlap_mode="target_only",
        )
        probe_samples = ni.build_probe_samples_payload(
            target_asset="TSLA",
            requested_start="2020-01-01",
            data_manifest=data_manifest,
            window_report=window_report,
        )
        ni.runtime_profile_path(branch).write_text(json.dumps(runtime_profile), encoding="utf-8")
        ni.execution_constraints_path(branch).write_text(
            json.dumps(execution_constraints),
            encoding="utf-8",
        )
        ni.data_manifest_path(branch).write_text(json.dumps(data_manifest), encoding="utf-8")
        ni.window_availability_path(branch).write_text(json.dumps(window_report), encoding="utf-8")
        ni.probe_samples_path(branch).write_text(json.dumps(probe_samples), encoding="utf-8")
        ni.context_guide_path(branch).write_text(
            ni.build_context_guide_markdown(
                target_asset="TSLA",
                target_node="TSLA.price",
                runtime_profile=runtime_profile,
                execution_constraints=execution_constraints,
                data_manifest=data_manifest,
                window_report=window_report,
            ),
            encoding="utf-8",
        )
        ni.persist_prepared_branch_contract(branch, ni.load_discovery(session))

    def fake_subprocess_run(command, cwd=None, capture_output=None, text=None, env=None, check=False, input=None):
        if "evaluate" in command:
            result_path = Path(command[command.index("--output-json") + 1])
            report_path = Path(command[command.index("--output-md") + 1])
            handoff_path = Path(command[command.index("--output-handoff") + 1])
            payload = {
                "verdict": "PASS",
                "score": "7/7",
                "failures": [],
                "warnings": [],
                "profile": "equity_daily",
                "K": 1,
                "metrics": {
                    "sharpe": 2.1,
                    "lo_adjusted": 2.6,
                    "position_ic": 0.0,
                    "omega": 1.4,
                    "total_return": 0.34,
                    "max_dd": -0.09,
                },
                "requested_window": {"start": "2020-01-01", "end": None},
                "effective_window": {"start": "2020-01-01", "end": "2020-12-31"},
                "diagnostics": {
                    "failure_signature": "clean_pass",
                    "runtime_stage": "evaluate",
                    "signal": {"active_days": 120, "total_days": 252},
                    "hints": ["keep going"],
                },
            }
            result_path.write_text(json.dumps(payload), encoding="utf-8")
            report_path.write_text("# validation\n", encoding="utf-8")
            handoff_path.write_text(json.dumps({"ok": True}), encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(ni.subprocess, "run", fake_subprocess_run)

    monkeypatch.setenv("ABEL_EXPERIMENT_PROTOCOL_ID", "protocol-one")
    monkeypatch.setenv("ABEL_EXPERIMENT_MODE", "baseline")
    monkeypatch.setenv("ABEL_EXPERIMENT_ROUND_BUDGET", "10")
    monkeypatch.setenv("ABEL_SKILLS_COMMIT", "skills-old")
    monkeypatch.setenv("ABEL_EDGE_COMMIT", "edge-old")
    ni.run_branch_round(
        Namespace(
            branch=str(first),
            mode="explore",
            description="baseline momentum rule",
            input_note="",
            hypothesis="baseline trend persistence",
            expected_signal="",
            trigger="baseline seed",
            change_summary="first baseline pass",
            time_spent_min="12",
            summary="",
            next_step="continue baseline exploration",
            action=[],
            python_bin=None,
            allow_untouched_template=True,
        )
    )

    monkeypatch.setenv("ABEL_EXPERIMENT_PROTOCOL_ID", "protocol-two")
    monkeypatch.setenv("ABEL_EXPERIMENT_MODE", "causal")
    monkeypatch.setenv("ABEL_EXPERIMENT_ROUND_BUDGET", "8")
    monkeypatch.setenv("ABEL_SKILLS_COMMIT", "skills-new")
    monkeypatch.setenv("ABEL_EDGE_COMMIT", "edge-new")
    ni.run_branch_round(
        Namespace(
            branch=str(second),
            mode="explore",
            description="causal driver vote",
            input_note="",
            hypothesis="top discovered parents vote the target",
            expected_signal="",
            trigger="graph discovery seed",
            change_summary="first causal pass",
            time_spent_min="15",
            summary="",
            next_step="compare against baseline branch",
            action=[],
            python_bin=None,
            allow_untouched_template=True,
        )
    )

    manifest = json.loads((session / ni.MEMORY_MANIFEST_FILENAME).read_text(encoding="utf-8"))

    assert manifest["experiment"] == {
        "protocol_id": "protocol-two",
        "experiment_mode": "causal",
        "round_budget": "8",
        "abel_skills_commit": "skills-new",
        "abel_edge_commit": "edge-new",
    }
