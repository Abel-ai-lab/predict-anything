from __future__ import annotations

import json
import sys
from pathlib import Path

from abel_invest import cli

from ._branch_runtime_helpers import (  # noqa: F401
    _complete_candidate_spec,
    _edge_result,
    _record_synthetic_round,
    _sample_discovery,
    _sample_readiness,
    _write_runtime_files,
)
from . import api as ni


def _run_cli(monkeypatch, argv: list[str]) -> int:
    monkeypatch.setattr(sys, "argv", ["abel-invest", *argv])
    return cli.main()


def _record_prepared_candidate(tmp_path: Path) -> tuple[Path, Path]:
    session = ni.init_session_dir("TSLA", "tsla-artifact-digest", tmp_path / "research")
    ni.write_graph_frontier_from_discovery_payload(session, _sample_discovery())
    ni.write_readiness(session, _sample_readiness())
    branch = ni.init_branch_dir(session, "graph-v1")
    spec = _complete_candidate_spec(branch, selected_inputs=["AAPL", "MSFT"])
    _write_runtime_files(branch)
    _record_synthetic_round(
        session,
        branch,
        spec=spec,
        result=_edge_result(traced_inputs=["AAPL", "MSFT"], sharpe=2.4),
    )
    ni.render_session(session)
    return session, branch


def _record_second_failed_candidate(session: Path) -> Path:
    branch = ni.init_branch_dir(session, "graph-v2")
    spec = _complete_candidate_spec(branch, selected_inputs=["GPC"])
    _write_runtime_files(branch)
    _record_synthetic_round(
        session,
        branch,
        spec=spec,
        result=_edge_result(
            traced_inputs=["GPC"],
            verdict="FAIL",
            sharpe=2.1,
            metric_failures=[
                {
                    "metric": "dsr",
                    "message": "T6 DSR 55.0% < 90%",
                }
            ],
            k=42,
        ),
        decision="discard",
    )
    ni.render_session(session)
    return branch


def test_artifact_digest_json_summarizes_session_without_full_artifact_dump(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    session, _branch = _record_prepared_candidate(tmp_path)

    assert _run_cli(monkeypatch, ["artifact-digest", "--session", str(session), "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "abel-invest.artifact-digest/v1"
    assert payload["scope"] == "session"
    assert payload["ticker"] == "TSLA"
    assert payload["session_digest"]["branch_count"] == 1
    assert payload["session_digest"]["round_count"] == 1
    assert payload["session_digest"]["frontier"]["graph_candidates_available"] is True

    branch_digest = payload["branches"][0]
    assert branch_digest["branch_id"] == "graph-v1"
    assert branch_digest["declaration"]["selected_inputs"] == ["AAPL", "MSFT"]
    assert branch_digest["prepared_inputs"]["feed_count"] == 3
    assert branch_digest["prepared_inputs"]["cache_ok_count"] == 3
    assert branch_digest["latest_round"]["verdict"] == "PASS"
    assert branch_digest["latest_round"]["metrics"]["sharpe"] == "2.400"
    assert branch_digest["latest_round"]["artifact_presence"] == {
        "result": True,
        "report": True,
        "handoff": True,
    }


def test_artifact_digest_text_can_focus_single_branch(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _session, branch = _record_prepared_candidate(tmp_path)

    assert _run_cli(monkeypatch, ["artifact-digest", "--branch", str(branch)]) == 0

    output = capsys.readouterr().out
    assert "Artifact digest: TSLA branch" in output
    assert "- graph-v1: rounds=1 latest=round-001 keep PASS 7/7" in output
    assert "result: branches/graph-v1/outputs/round-001-edge-result.json" in output
    assert "edge-result" in output
    assert "prepared_inputs" not in output


def test_artifact_digest_session_compact_surfaces_bounded_loop_state(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    session, branch = _record_prepared_candidate(tmp_path)
    failed_branch = _record_second_failed_candidate(session)

    assert _run_cli(monkeypatch, ["artifact-digest", "--session", str(session), "--compact"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "abel-invest.artifact-digest/v1"
    assert payload["mode"] == "compact"
    assert payload["scope"] == "session"
    assert payload["loop_state_only"] is True
    assert payload["not_user_report"] is True
    assert payload["use_for"] == ["resume", "checkpoint_recovery", "branch_backtrack"]
    assert payload["do_not_use_for"] == ["final_ranking", "user_report"]
    assert payload["final_report_source"].endswith(f"best-strategy --session {session} --json")
    assert payload["status"]["branch_count"] == 2
    assert payload["status"]["recorded_round_count"] == 2
    assert payload["latest_round"]["branch_id"] == failed_branch.name
    assert payload["latest_round"]["primary_blockers"] == ["T6 DSR 55.0% < 90%"]
    assert payload["best_so_far"]["branch_id"] == branch.name
    assert payload["best_so_far"]["verdict"] == "PASS"
    assert len(payload["recent_branches"]) == 2
    assert "branches" not in payload
    assert "prepared_inputs" not in json.dumps(payload)


def test_artifact_digest_branch_compact_surfaces_failure_facts(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    session, _branch = _record_prepared_candidate(tmp_path)
    failed_branch = _record_second_failed_candidate(session)

    assert _run_cli(monkeypatch, ["artifact-digest", "--branch", str(failed_branch), "--compact"]) == 0

    payload = json.loads(capsys.readouterr().out)
    latest = payload["latest_round"]
    assert payload["mode"] == "compact"
    assert payload["scope"] == "branch"
    assert payload["loop_state_only"] is True
    assert payload["not_user_report"] is True
    assert payload["final_report_source"].endswith(f"best-strategy --session {session} --json")
    assert payload["branch_id"] == "graph-v2"
    assert payload["declaration"]["selected_inputs"] == ["GPC"]
    assert latest["verdict"] == "FAIL"
    assert latest["primary_blockers"] == ["T6 DSR 55.0% < 90%"]
    assert latest["metrics"]["K"] == "1"
    assert latest["decision_facts"]["semantic_ready"] is True
    assert latest["decision_facts"]["has_primary_blocker"] is True
    assert latest["artifact_paths"]["result"] == "branches/graph-v2/outputs/round-001-edge-result.json"


def test_artifact_digest_requires_session_or_branch(monkeypatch, capsys) -> None:
    assert _run_cli(monkeypatch, ["artifact-digest"]) == 2

    err = capsys.readouterr().err
    assert "one of the arguments --session --branch is required" in err


def test_artifact_digest_rejects_session_and_branch_together(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    session, branch = _record_prepared_candidate(tmp_path)

    assert (
        _run_cli(
            monkeypatch,
            ["artifact-digest", "--session", str(session), "--branch", str(branch)],
        )
        == 2
    )

    err = capsys.readouterr().err
    assert "argument --branch: not allowed with argument --session" in err


def test_artifact_digest_rejects_json_and_compact_together(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    session, _branch = _record_prepared_candidate(tmp_path)

    assert _run_cli(monkeypatch, ["artifact-digest", "--session", str(session), "--json", "--compact"]) == 2

    err = capsys.readouterr().err
    assert "not allowed with argument" in err
