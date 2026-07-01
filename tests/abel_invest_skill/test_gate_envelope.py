from __future__ import annotations

import json

import pytest

from abel_invest.narrative_core.gate_envelope import (
    GATE_DECISION_TRACE_FILENAME,
    build_gate_decision_trace,
    build_gate_envelope,
    build_user_request,
    compute_gate_identity,
    render_gate_envelope_summary,
    write_gate_decision_trace,
)


def test_build_user_request_defaults_to_current_gate_for_missing_objective():
    request = build_user_request("")

    assert request["defaulted"] is True
    assert request["default_policy"] == "current_gate_compat"
    assert request["raw_prompt"]["text"] == ""
    assert request["raw_prompt"]["source"]["kind"] == "default"
    assert request["objective"]["metric"] == "sharpe"
    assert request["objective"]["target"] == 2.0
    assert request["limits"]["edge_required_gates"] == "pass_all_current_required"


def test_build_gate_envelope_current_default():
    envelope = build_gate_envelope(
        ticker="MSFT",
        mode="standard",
        objective_text="",
        discovery={"target_node": "MSFT.price"},
        backtest_start="2020-01-01",
        created_at="2026-06-30T00:00:00Z",
    )

    assert envelope["schema"] == "abel-invest.gate-envelope/v1"
    assert envelope["gate_hash"] == envelope["identity"]["gate_hash"]
    assert envelope["selected_gate"]["gate_id"] == "generated:current-gate-compat-v1"
    assert envelope["user_request"]["defaulted"] is True
    assert envelope["target_binding"]["target"] == "MSFT"
    assert envelope["target_binding"]["target_node"] == "MSFT.price"
    assert envelope["edge_vocabulary"]["dimensions_used"] == [
        "edge_required_gates",
        "search_width",
        "sharpe",
    ]


def test_build_gate_envelope_balanced_drawdown_request():
    envelope = build_gate_envelope(
        ticker="TSLA",
        mode="standard",
        objective_text="Find a robust daily TSLA strategy with controlled drawdown.",
        discovery={"target_node": "TSLA.price"},
        backtest_start="2020-01-01",
        created_at="2026-06-30T00:00:00Z",
    )

    checks = {check["dimension"]: check for check in envelope["selected_gate"]["checks"]}
    assert envelope["selected_gate"]["gate_id"] == "generated:daily-balanced-controlled-dd-v1"
    assert envelope["user_request"]["defaulted"] is False
    assert checks["max_dd"]["threshold"] == -0.15
    assert checks["sharpe"]["threshold"] == 1.0
    assert checks["search_width"]["operator"] == "recorded"


def test_ordinary_request_can_generate_lite_like_envelope_shape():
    envelope = build_gate_envelope(
        ticker="AAPL",
        mode="standard",
        objective_text=(
            "I am new to investing. Find a simple AAPL strategy and show me "
            "return and drawdown first."
        ),
        discovery={"target_node": "AAPL.price"},
        backtest_start="2020-01-01",
        created_at="2026-06-30T00:00:00Z",
    )

    assert envelope["source"]["mode"] == "standard"
    assert envelope["source"]["request_source"] == "cli_objective"
    assert envelope["user_request"]["raw_prompt"]["source"]["kind"] == "cli_objective"
    assert envelope["user_request"]["preferences"]["gate_envelope_shape"] == "lite_like"
    assert envelope["compatibility"]["gate_envelope_shape"] == "lite_like"
    assert envelope["selected_gate"]["gate_id"] == "generated:beginner-simple-current-gate-v1"
    dimensions = {check["dimension"] for check in envelope["selected_gate"]["checks"]}
    assert {
        "total_return",
        "max_dd",
        "position_bounds",
        "edge_required_gates",
        "search_width",
    } == dimensions


def test_gate_hash_excludes_volatile_fields_and_includes_semantics():
    first = build_gate_envelope(
        ticker="TSLA",
        mode="standard",
        objective_text="Find a robust daily TSLA strategy with controlled drawdown.",
        discovery={"target_node": "TSLA.price"},
        backtest_start="2020-01-01",
        created_at="2026-06-30T00:00:00Z",
    )
    second = build_gate_envelope(
        ticker="TSLA",
        mode="standard",
        objective_text="Find a robust daily TSLA strategy with controlled drawdown.",
        discovery={"target_node": "TSLA.price"},
        backtest_start="2020-01-01",
        created_at="2026-07-01T00:00:00Z",
    )
    changed = json.loads(json.dumps(first))
    changed["selected_gate"]["checks"][1]["threshold"] = -0.10

    assert first["gate_hash"] == second["gate_hash"]
    assert compute_gate_identity(changed) != first["gate_hash"]


def test_gate_decision_trace_cites_only_generation_inputs(tmp_path):
    envelope = build_gate_envelope(
        ticker="TSLA",
        mode="standard",
        objective_text="Find a robust daily TSLA strategy with controlled drawdown.",
        discovery={"target_node": "TSLA.price"},
        backtest_start="2020-01-01",
        created_at="2026-06-30T00:00:00Z",
    )

    trace = build_gate_decision_trace(envelope)
    written = write_gate_decision_trace(tmp_path, envelope)

    assert trace == written
    assert (tmp_path / GATE_DECISION_TRACE_FILENAME).exists()
    assert trace["created_before_exploration"] is True
    assert trace["gate_hash"] == envelope["gate_hash"]
    assert trace["user_request_snapshot"]["ssot"] == "session_state.gate_envelope.user_request"
    assert "normalized" not in trace["user_request_snapshot"]
    assert "normalized_user_request" in trace["user_request_snapshot"]
    assert trace["generation"]["generated_gate_id"] == envelope["selected_gate"]["gate_id"]
    assert trace["generation"]["inputs"] == ["user_request", "edge_vocabulary_context"]
    assert trace["edge_vocabulary_snapshot"]["snapshot_scope"] == "cited_dimensions_only"
    trace_json = json.dumps(trace)
    assert "candidate_metrics" not in trace_json
    assert "verdict" not in trace_json


def test_render_gate_envelope_summary_is_factual():
    envelope = build_gate_envelope(
        ticker="TSLA",
        mode="standard",
        objective_text="Find a robust daily TSLA strategy with controlled drawdown.",
        discovery={"target_node": "TSLA.price"},
        backtest_start="2020-01-01",
        created_at="2026-06-30T00:00:00Z",
    )

    rendered = render_gate_envelope_summary(envelope)

    assert "## Gate Envelope" in rendered
    assert envelope["selected_gate"]["gate_id"] in rendered
    assert envelope["gate_hash"] in rendered
    assert "route_prescription: `forbidden`" in rendered
    assert "try next" not in rendered.lower()


def test_empty_edge_vocabulary_fails_before_gate_generation():
    vocabulary = {
        "schema": "abel-edge.gate-vocabulary/v1",
        "edge_version": "test",
        "vocabulary_hash": "sha256:test",
        "dimensions": [],
    }

    with pytest.raises(RuntimeError, match="empty gate vocabulary"):
        build_gate_envelope(
            ticker="MSFT",
            mode="standard",
            objective_text="",
            discovery={"target_node": "MSFT.price"},
            backtest_start="2020-01-01",
            vocabulary=vocabulary,
        )


def test_missing_required_edge_dimension_fails_actionably():
    vocabulary = {
        "schema": "abel-edge.gate-vocabulary/v1",
        "edge_version": "test",
        "vocabulary_hash": "sha256:test",
        "dimensions": [{"id": "sharpe", "numeric_meaning": "test"}],
    }

    with pytest.raises(RuntimeError, match="missing required dimension: edge_required_gates"):
        build_gate_envelope(
            ticker="MSFT",
            mode="standard",
            objective_text="",
            discovery={"target_node": "MSFT.price"},
            backtest_start="2020-01-01",
            vocabulary=vocabulary,
        )
