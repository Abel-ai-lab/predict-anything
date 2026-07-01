from __future__ import annotations

import json
import sys
from pathlib import Path

from abel_invest import cli
from abel_invest.narrative_core.evidence import graph_frontier
from abel_invest.narrative_core.rendering.session_rendering import render_session
from abel_invest.narrative_core.state import write_session_state


def _run_cli(monkeypatch, argv: list[str]) -> int:
    monkeypatch.setattr(sys, "argv", ["abel-invest", *argv])
    return cli.main()


def test_init_session_writes_default_gate_envelope_trace_and_context(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    root = tmp_path / "research"

    assert _run_cli(
        monkeypatch,
        [
            "init-session",
            "--ticker",
            "MSFT",
            "--exp-id",
            "r1-default",
            "--root",
            str(root),
            "--allow-outside-workspace",
            "--no-discover",
        ],
    ) == 0

    session = root / "msft" / "r1-default"
    state = json.loads((session / "session_state.json").read_text(encoding="utf-8"))
    envelope = state["gate_envelope"]
    trace = json.loads((session / "gate_decision_trace.json").read_text(encoding="utf-8"))
    context = (session / "agent_context.md").read_text(encoding="utf-8")
    output = capsys.readouterr().out

    assert envelope["user_request"]["defaulted"] is True
    assert envelope["user_request"]["default_policy"] == "current_gate_compat"
    assert envelope["selected_gate"]["gate_id"] == "generated:current-gate-compat-v1"
    assert envelope["gate_hash"] == trace["gate_hash"]
    assert envelope["selected_gate"]["gate_id"] in context
    assert envelope["gate_hash"] in context
    assert "selected_gate: generated:current-gate-compat-v1" in output
    assert "gate_hash: sha256:" in output


def test_explicit_objective_and_branch_freeze_gate_hash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "research"

    assert _run_cli(
        monkeypatch,
        [
            "init-session",
            "--ticker",
            "TSLA",
            "--exp-id",
            "r1-balanced",
            "--root",
            str(root),
            "--allow-outside-workspace",
            "--no-discover",
            "--objective",
            "Find a robust daily TSLA strategy with controlled drawdown.",
        ],
    ) == 0
    session = root / "tsla" / "r1-balanced"
    before_state = json.loads((session / "session_state.json").read_text(encoding="utf-8"))
    before_trace = json.loads((session / "gate_decision_trace.json").read_text(encoding="utf-8"))
    before_hash = before_state["gate_envelope"]["gate_hash"]

    assert _run_cli(
        monkeypatch,
        ["init-branch", "--session", str(session), "--branch-id", "smoke-freeze"],
    ) == 0
    assert _run_cli(monkeypatch, ["status", "--session", str(session)]) == 0

    after_state = json.loads((session / "session_state.json").read_text(encoding="utf-8"))
    after_trace = json.loads((session / "gate_decision_trace.json").read_text(encoding="utf-8"))
    envelope = after_state["gate_envelope"]

    assert envelope["gate_hash"] == before_hash
    assert after_trace == before_trace
    assert envelope["selected_gate"]["gate_id"] == "generated:daily-balanced-controlled-dd-v1"
    dimensions = {check["dimension"] for check in envelope["selected_gate"]["checks"]}
    assert {"max_dd", "sharpe", "search_width"}.issubset(dimensions)
    assert "candidate_metrics" not in json.dumps(after_trace)
    assert "verdict" not in json.dumps(after_trace)


def test_legacy_session_render_synthesizes_without_mutating_state(tmp_path: Path) -> None:
    session = tmp_path / "research" / "tsla" / "legacy"
    session.mkdir(parents=True)
    graph_frontier.write_graph_frontier(
        session,
        graph_frontier.build_pending_graph_frontier("TSLA", backtest_start="2020-01-01"),
    )
    write_session_state(session, {"mode": "standard"})
    before = (session / "session_state.json").read_text(encoding="utf-8")

    render_session(session)

    after = (session / "session_state.json").read_text(encoding="utf-8")
    context = (session / "agent_context.md").read_text(encoding="utf-8")
    assert before == after
    assert "## Gate Envelope" in context
    assert "generated:current-gate-compat-v1" in context
