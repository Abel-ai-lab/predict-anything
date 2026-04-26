from __future__ import annotations

import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

from abel_strategy_discovery import narrative_impl as ni


def _sample_discovery() -> dict:
    return {
        "ticker": "TSLA",
        "target_node": "TSLA.price",
        "parents": [{"ticker": "AAPL", "field": "price"}, {"ticker": "MSFT", "field": "price"}],
        "blanket_new": [],
        "children": [],
        "backtest": {"start": "2020-01-01"},
    }


def _sample_readiness() -> dict:
    return {
        "results": [
            {
                "ticker": "TSLA",
                "status": "full",
                "usable": True,
                "covers_requested_start": True,
            },
            {
                "ticker": "AAPL",
                "status": "full",
                "usable": True,
                "covers_requested_start": True,
            },
            {
                "ticker": "MSFT",
                "status": "partial",
                "usable": True,
                "covers_requested_start": False,
            },
        ],
        "coverage_hints": {
            "target_safe_start": "2020-01-01",
            "dense_overlap_hint_start": "2020-03-01",
        },
    }


def _sample_selected_inputs() -> list[dict]:
    return [
        {"node_id": "TSLA.volume", "asset": "TSLA", "field": "volume", "roles": ["selected"]},
        {"node_id": "MSFT.price", "asset": "MSFT", "field": "price", "roles": ["selected"]},
    ]


def _write_runtime_files(branch: Path) -> None:
    ni.dependencies_path(branch).parent.mkdir(parents=True, exist_ok=True)
    ni.dependencies_path(branch).write_text(
        json.dumps(
            {
                "version": 1,
                "cache": {
                    "adapter": "abel",
                    "timeframe": "1d",
                    "profile": "daily",
                    "cache_root": "/tmp/cache",
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
                        {
                            "symbol": "MSFT",
                            "ok": True,
                            "row_count": 90,
                            "available_range": {"start": "2020-03-01", "end": "2020-12-31"},
                        },
                    ],
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ni.runtime_profile_path(branch).write_text(
        json.dumps(
            {
                "profile": "daily",
                "target": "TSLA",
                "target_asset": "TSLA",
                "target_node": "TSLA.price",
                "decision_event": "bar_close",
                "execution_delay_bars": 2,
                "return_basis": "close_to_close",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ni.execution_constraints_path(branch).write_text(
        json.dumps({"long_only": False, "position_bounds": [-0.5, 0.5]}, indent=2),
        encoding="utf-8",
    )
    ni.data_manifest_path(branch).write_text(
        json.dumps(
            {
                "version": 2,
                "target_asset": "TSLA",
                "target_node": "TSLA.price",
                "selected_inputs": _sample_selected_inputs(),
                "feeds": [
                    {
                        "name": "primary",
                        "node_id": "TSLA.price",
                        "asset": "TSLA",
                        "field": "price",
                        "symbol": "TSLA",
                        "role": "target",
                        "runtime_field": "close",
                        "adapter": "abel",
                        "timeframe": "1d",
                        "profile": "daily",
                        "cache_root": "/tmp/cache",
                    },
                    {
                        "name": "TSLA.volume",
                        "node_id": "TSLA.volume",
                        "asset": "TSLA",
                        "field": "volume",
                        "symbol": "TSLA",
                        "role": "input",
                        "runtime_field": "volume",
                        "adapter": "abel",
                        "timeframe": "1d",
                        "profile": "daily",
                        "cache_root": "/tmp/cache",
                    },
                    {
                        "name": "MSFT.price",
                        "node_id": "MSFT.price",
                        "asset": "MSFT",
                        "field": "price",
                        "symbol": "MSFT",
                        "role": "input",
                        "runtime_field": "close",
                        "adapter": "abel",
                        "timeframe": "1d",
                        "profile": "daily",
                        "cache_root": "/tmp/cache",
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ni.window_availability_path(branch).write_text(
        json.dumps(
            {
                "version": 1,
                "target_node": "TSLA.price",
                "requested_start": "2020-01-01",
                "requested_end": None,
                "overlap_mode": "target_only",
                "target_window": {
                    "start": "2020-01-01T00:00:00+00:00",
                    "end": "2020-12-31T00:00:00+00:00",
                },
                "effective_window": {
                    "start": "2020-03-01T00:00:00+00:00",
                    "end": "2020-12-31T00:00:00+00:00",
                },
                "limiting_inputs": ["MSFT.price"],
                "per_input_coverage": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ni.probe_samples_path(branch).write_text(
        json.dumps(
            {
                "version": 2,
                "target_asset": "TSLA",
                "target_node": "TSLA.price",
                "requested_start": "2020-01-01",
                "sample_decision_dates": ["2020-01-01", "2020-06-17", "2020-12-31"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ni.context_guide_path(branch).write_text(
        "# TSLA Branch Context Guide\n\n- use `ctx.target.series(\"close\")`\n",
        encoding="utf-8",
    )
    ni.persist_prepared_branch_contract(branch, ni.load_discovery(branch.parent.parent))


def test_prepare_branch_inputs_writes_runtime_contract_artifacts(tmp_path, monkeypatch) -> None:
    session = ni.init_session_dir("TSLA", "tsla-v1", tmp_path / "research")
    ni.write_discovery(session, _sample_discovery())
    ni.write_readiness(session, _sample_readiness())
    branch = ni.init_branch_dir(session, "graph-v1")

    spec = ni.load_branch_spec(branch)
    spec["target_asset"] = "TSLA"
    spec["target_node"] = "TSLA.price"
    spec["requested_start"] = "2020-01-01"
    spec["selected_inputs"] = _sample_selected_inputs()
    spec["position_bounds"] = [-1.0, 1.0]
    ni.write_branch_spec(branch, spec)

    calls = []

    def fake_subprocess_run(command, cwd=None, capture_output=None, text=None, env=None):
        calls.append(list(command))
        output_path = Path(command[command.index("--output-json") + 1])
        output_path.write_text(
            json.dumps(
                {
                    "adapter": "abel",
                    "timeframe": "1d",
                    "profile": "daily",
                    "results": [
                        {
                            "symbol": "TSLA",
                            "ok": True,
                            "row_count": 150,
                            "available_range": {"start": "2020-01-01", "end": "2020-12-31"},
                        },
                        {
                            "symbol": "AAPL",
                            "ok": True,
                            "row_count": 150,
                            "available_range": {"start": "2020-01-01", "end": "2020-12-31"},
                        },
                        {
                            "symbol": "MSFT",
                            "ok": True,
                            "row_count": 110,
                            "available_range": {"start": "2020-03-01", "end": "2020-12-31"},
                        },
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(ni.subprocess, "run", fake_subprocess_run)

    result = ni.prepare_branch_inputs(
        Namespace(
            branch=str(branch),
            python_bin=sys.executable,
            cache_limit=400,
        )
    )

    assert result == 0
    assert calls and "warm-cache" in calls[0]
    assert ni.branch_inputs_ready(branch)

    runtime_profile = json.loads(ni.runtime_profile_path(branch).read_text(encoding="utf-8"))
    data_manifest = json.loads(ni.data_manifest_path(branch).read_text(encoding="utf-8"))
    window_report = json.loads(ni.window_availability_path(branch).read_text(encoding="utf-8"))
    probe_samples = json.loads(ni.probe_samples_path(branch).read_text(encoding="utf-8"))
    context_guide = ni.context_guide_path(branch).read_text(encoding="utf-8")

    assert runtime_profile["target"] == "TSLA"
    assert runtime_profile["target_node"] == "TSLA.price"
    assert [feed["name"] for feed in data_manifest["feeds"]] == ["primary", "TSLA.volume", "MSFT.price"]
    assert data_manifest["selected_inputs"][0]["node_id"] == "TSLA.volume"
    assert data_manifest["feeds"][1]["runtime_field"] == "volume"
    assert data_manifest["feeds"][1]["alignment_mode"] == "asof_to_target_decision"
    assert window_report["effective_window"]["start"] == "2020-03-01T00:00:00+00:00"
    assert window_report["start_alignment"]["avoidable_gap_days"] == 60
    assert probe_samples["target_asset"] == "TSLA"
    assert len(probe_samples["sample_decision_dates"]) >= 2
    assert "DecisionContext" in context_guide
    assert "window_availability.json" in context_guide
    assert "avoidable_gap_days" in context_guide
    assert 'ctx.feed("TSLA.volume").asof_series("volume")' in context_guide


def test_prepare_branch_inputs_passes_csv_adapter_and_path(tmp_path, monkeypatch) -> None:
    session = ni.init_session_dir("TSLA", "tsla-v1-csv", tmp_path / "research")
    ni.write_discovery(session, _sample_discovery())
    ni.write_readiness(session, _sample_readiness())
    branch = ni.init_branch_dir(session, "baseline-v1")

    csv_path = tmp_path / "bars.csv"
    csv_path.write_text(
        "timestamp,symbol,close\n"
        "2020-01-01T00:00:00Z,TSLA,100\n"
        "2020-01-02T00:00:00Z,TSLA,101\n",
        encoding="utf-8",
    )

    spec = ni.load_branch_spec(branch)
    spec["target_asset"] = "TSLA"
    spec["target_node"] = "TSLA.price"
    spec["requested_start"] = "2020-01-01"
    spec["selected_inputs"] = []
    spec["source_type"] = "baseline"
    spec["method_family"] = "rule"
    spec["data_requirements"] = {
        "timeframe": "1d",
        "adapter": "csv",
        "path": str(csv_path),
    }
    ni.write_branch_spec(branch, spec)

    calls = []

    def fake_subprocess_run(command, cwd=None, capture_output=None, text=None, env=None):
        calls.append(list(command))
        output_path = Path(command[command.index("--output-json") + 1])
        output_path.write_text(
            json.dumps(
                {
                    "adapter": "csv",
                    "path": str(csv_path),
                    "timeframe": "1d",
                    "profile": "daily",
                    "results": [
                        {
                            "symbol": "TSLA",
                            "ok": True,
                            "row_count": 150,
                            "available_range": {"start": "2020-01-01", "end": "2020-12-31"},
                        }
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(ni.subprocess, "run", fake_subprocess_run)

    result = ni.prepare_branch_inputs(
        Namespace(
            branch=str(branch),
            python_bin=sys.executable,
            cache_limit=400,
        )
    )

    assert result == 0
    assert calls and "warm-cache" in calls[0]
    assert "--adapter" in calls[0]
    assert calls[0][calls[0].index("--adapter") + 1] == "csv"
    assert "--path" in calls[0]
    assert calls[0][calls[0].index("--path") + 1] == str(csv_path)

    data_manifest = json.loads(ni.data_manifest_path(branch).read_text(encoding="utf-8"))
    assert data_manifest["feeds"][0]["adapter"] == "csv"
    assert data_manifest["feeds"][0]["path"] == str(csv_path)


def test_build_branch_context_prefers_prepared_runtime_inputs(tmp_path) -> None:
    session = ni.init_session_dir("TSLA", "tsla-v2", tmp_path / "research")
    discovery = _sample_discovery()
    readiness = _sample_readiness()
    ni.write_discovery(session, discovery)
    ni.write_readiness(session, readiness)
    branch = ni.init_branch_dir(session, "graph-v1")

    spec = ni.load_branch_spec(branch)
    spec["target_asset"] = "TSLA"
    spec["target_node"] = "TSLA.price"
    spec["selected_inputs"] = _sample_selected_inputs()
    ni.write_branch_spec(branch, spec)
    _write_runtime_files(branch)

    context = ni.build_branch_context(
        branch=branch,
        session=session,
        discovery=discovery,
        readiness=readiness,
        round_id="round-001",
        backtest_start="2020-01-01",
    )

    assert context["runtime_profile"]["execution_delay_bars"] == 2
    assert context["_execution_constraints"]["position_bounds"] == [-0.5, 0.5]
    assert sorted(context["_feeds"].keys()) == ["MSFT.price", "TSLA.volume", "primary"]
    assert context["_feeds"]["TSLA.volume"]["symbol"] == "TSLA"
    assert context["_feeds"]["TSLA.volume"]["default_field"] == "volume"
    assert context["data_manifest"]["selected_inputs"][1]["node_id"] == "MSFT.price"


def test_build_branch_context_preserves_csv_feed_path(tmp_path) -> None:
    session = ni.init_session_dir("TSLA", "tsla-v2-csv", tmp_path / "research")
    discovery = _sample_discovery()
    readiness = _sample_readiness()
    ni.write_discovery(session, discovery)
    ni.write_readiness(session, readiness)
    branch = ni.init_branch_dir(session, "graph-v1")

    spec = ni.load_branch_spec(branch)
    spec["target_asset"] = "TSLA"
    spec["target_node"] = "TSLA.price"
    spec["selected_inputs"] = []
    ni.write_branch_spec(branch, spec)
    _write_runtime_files(branch)

    csv_path = str(tmp_path / "bars.csv")
    dependencies = json.loads(ni.dependencies_path(branch).read_text(encoding="utf-8"))
    dependencies["cache"]["adapter"] = "csv"
    dependencies["cache"]["path"] = csv_path
    ni.dependencies_path(branch).write_text(json.dumps(dependencies), encoding="utf-8")

    data_manifest = json.loads(ni.data_manifest_path(branch).read_text(encoding="utf-8"))
    data_manifest["feeds"] = [
        {
            **data_manifest["feeds"][0],
            "adapter": "csv",
            "path": csv_path,
        }
    ]
    ni.data_manifest_path(branch).write_text(json.dumps(data_manifest), encoding="utf-8")

    context = ni.build_branch_context(
        branch=branch,
        session=session,
        discovery=discovery,
        readiness=readiness,
        round_id="round-001",
        backtest_start="2020-01-01",
    )

    assert context["_feeds"]["primary"]["adapter"] == "csv"
    assert context["_feeds"]["primary"]["path"] == csv_path


def test_debug_branch_run_blocks_on_stale_prepared_contract(tmp_path, capsys) -> None:
    session = ni.init_session_dir("TSLA", "tsla-v3-debug", tmp_path / "research")
    discovery = _sample_discovery()
    readiness = _sample_readiness()
    ni.write_discovery(session, discovery)
    ni.write_readiness(session, readiness)
    branch = ni.init_branch_dir(session, "graph-v1")

    spec = ni.load_branch_spec(branch)
    spec["target_asset"] = "TSLA"
    spec["target_node"] = "TSLA.price"
    spec["requested_start"] = "2020-01-01"
    spec["selected_inputs"] = _sample_selected_inputs()
    ni.write_branch_spec(branch, spec)
    _write_runtime_files(branch)

    spec["requested_start"] = "2020-02-01"
    ni.write_branch_spec(branch, spec)

    result = ni.debug_branch_run(
        Namespace(
            branch=str(branch),
            python_bin=sys.executable,
        )
    )

    captured = capsys.readouterr()
    assert result == 2
    assert "Prepared branch inputs are stale" in captured.err
    assert "changed_fields=requested_start" in captured.err


def test_build_branch_context_includes_experiment_metadata(tmp_path, monkeypatch) -> None:
    session = ni.init_session_dir("TSLA", "tsla-v4-context", tmp_path / "research")
    discovery = _sample_discovery()
    readiness = _sample_readiness()
    ni.write_discovery(session, discovery)
    ni.write_readiness(session, readiness)
    branch = ni.init_branch_dir(session, "graph-v1")

    spec = ni.load_branch_spec(branch)
    spec["target_asset"] = "TSLA"
    spec["target_node"] = "TSLA.price"
    spec["requested_start"] = "2020-01-01"
    spec["selected_inputs"] = _sample_selected_inputs()
    ni.write_branch_spec(branch, spec)
    _write_runtime_files(branch)

    monkeypatch.setenv("ABEL_EXPERIMENT_PROTOCOL_ID", "alpha-exec-sandbox-v1")
    monkeypatch.setenv("ABEL_EXPERIMENT_MODE", "baseline")
    monkeypatch.setenv("ABEL_EXPERIMENT_ROUND_BUDGET", "10")
    monkeypatch.setenv("ABEL_SKILLS_COMMIT", "skills-sha-123")
    monkeypatch.setenv("ABEL_EDGE_COMMIT", "edge-sha-456")

    context = ni.build_branch_context(
        branch=branch,
        session=session,
        discovery=discovery,
        readiness=readiness,
        round_id="round-001",
        backtest_start="2020-01-01",
    )

    assert context["experiment"] == {
        "protocol_id": "alpha-exec-sandbox-v1",
        "experiment_mode": "baseline",
        "round_budget": "10",
        "abel_skills_commit": "skills-sha-123",
        "abel_edge_commit": "edge-sha-456",
    }


def test_round_experiment_metadata_returns_blank_shape_when_context_is_missing(tmp_path) -> None:
    session = ni.init_session_dir("TSLA", "tsla-v5-context-shape", tmp_path / "research")
    branch = ni.init_branch_dir(session, "graph-v1")

    assert ni.round_experiment_metadata(branch, "round-001") == {
        "protocol_id": "",
        "experiment_mode": "",
        "round_budget": "",
        "abel_skills_commit": "",
        "abel_edge_commit": "",
    }


def test_run_branch_round_blocks_on_stale_prepared_contract(tmp_path, capsys) -> None:
    session = ni.init_session_dir("TSLA", "tsla-v3-run", tmp_path / "research")
    discovery = _sample_discovery()
    readiness = _sample_readiness()
    ni.write_discovery(session, discovery)
    ni.write_readiness(session, readiness)
    branch = ni.init_branch_dir(session, "graph-v1")

    spec = ni.load_branch_spec(branch)
    spec["target_asset"] = "TSLA"
    spec["target_node"] = "TSLA.price"
    spec["requested_start"] = "2020-01-01"
    spec["selected_inputs"] = _sample_selected_inputs()
    ni.write_branch_spec(branch, spec)
    _write_runtime_files(branch)

    spec["selected_inputs"] = [{"node_id": "AAPL.price", "asset": "AAPL", "field": "price"}]
    ni.write_branch_spec(branch, spec)

    result = ni.run_branch_round(
        Namespace(
            branch=str(branch),
            mode="explore",
            description="stale contract check",
            input_note="",
            hypothesis="stale contract should block run",
            expected_signal="",
            trigger="contract drift",
            change_summary="manual selected input change",
            time_spent_min="1",
            summary="",
            next_step="",
            action=[],
            python_bin=None,
            allow_untouched_template=True,
        )
    )

    captured = capsys.readouterr()
    assert result == 2
    assert "Prepared branch inputs are stale" in captured.err
    assert "changed_fields=selected_inputs" in captured.err
