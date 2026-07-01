"""Gate envelope generation for Abel Invest sessions."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from abel_invest.narrative_core.contracts.constants import GATE_DECISION_TRACE_FILENAME
from abel_invest.narrative_core.io import write_json_file

GATE_ENVELOPE_SCHEMA = "abel-invest.gate-envelope/v1"
USER_REQUEST_SCHEMA = "abel-invest.user-request/v1"
TRACE_SCHEMA = "abel-invest.gate-decision-trace/v1"
GENERATOR_VERSION = "abel-invest.gate-generator/v1"
HASH_MATERIAL_VERSION = 1


def load_edge_gate_vocabulary() -> dict[str, Any]:
    """Load the Edge-owned gate vocabulary or fail before session creation."""

    try:
        from abel_edge.validation.gate_vocabulary import list_gate_vocabulary
    except ImportError as exc:  # pragma: no cover - depends on runtime packaging
        raise RuntimeError(
            "Abel Invest cannot build a gate envelope because "
            "abel_edge.validation.gate_vocabulary is unavailable."
        ) from exc
    vocabulary = list_gate_vocabulary()
    if not isinstance(vocabulary, dict) or not vocabulary.get("dimensions"):
        raise RuntimeError("Abel Edge returned an empty gate vocabulary.")
    return vocabulary


def build_user_request(objective_text: str | None, *, source_kind: str = "cli_objective") -> dict:
    """Build the session-local user request object from raw objective text."""

    raw_text = str(objective_text or "").strip()
    defaulted = _is_unusably_vague(raw_text)
    if defaulted:
        return {
            "schema": USER_REQUEST_SCHEMA,
            "raw_text": raw_text,
            "raw_text_hash": _hash_text(raw_text),
            "source": {"kind": "default" if not raw_text else source_kind, "field": "--objective"},
            "defaulted": True,
            "default_policy": "current_gate_compat",
            "principle_ref": None,
            "objective": {
                "metric": "sharpe",
                "target": 2.0,
                "secondary": ["total_return"],
                "plain_language": (
                    "pursue high return with Sharpe > 2 and all required "
                    "Abel Edge gates passing"
                ),
            },
            "limits": {"edge_required_gates": "pass_all_current_required"},
            "preferences": {"evidence_depth": "standard"},
            "governance": {"change": "new_session_or_explicit_regenerate"},
        }

    lowered = raw_text.lower()
    objective = _normalize_objective(raw_text, lowered)
    limits = _normalize_limits(lowered)
    preferences = _normalize_preferences(lowered)
    return {
        "schema": USER_REQUEST_SCHEMA,
        "raw_text": raw_text,
        "raw_text_hash": _hash_text(raw_text),
        "source": {"kind": source_kind, "field": "--objective"},
        "defaulted": False,
        "default_policy": None,
        "principle_ref": None,
        "objective": objective,
        "limits": limits,
        "preferences": preferences,
        "governance": {"change": "new_session_or_explicit_regenerate"},
    }


def build_gate_envelope(
    *,
    ticker: str,
    mode: str,
    objective_text: str | None,
    discovery: dict | None = None,
    backtest_start: str | None = None,
    vocabulary: dict | None = None,
    created_at: str | None = None,
) -> dict:
    """Build, validate, canonicalize, and hash a session gate envelope."""

    target = str(ticker or "").strip().upper()
    user_request = build_user_request(objective_text)
    edge_vocabulary = vocabulary or load_edge_gate_vocabulary()
    selected_gate = _generate_selected_gate(user_request, edge_vocabulary)
    dimensions_used = _dimensions_used(selected_gate)
    agent_summary = _agent_summary(edge_vocabulary, dimensions_used)
    envelope = {
        "schema": GATE_ENVELOPE_SCHEMA,
        "identity": {
            "hash_algorithm": "sha256",
            "hash_material_version": HASH_MATERIAL_VERSION,
        },
        "gate_id": selected_gate["gate_id"],
        "created_at": created_at or _now(),
        "source": {
            "mode": str(mode or "standard").strip().lower() or "standard",
            "request_source": user_request["source"]["kind"],
            "vocabulary_source": "abel-edge.validation.gate_vocabulary",
            "generator_version": GENERATOR_VERSION,
        },
        "user_request": user_request,
        "edge_vocabulary": {
            "schema": edge_vocabulary.get("schema"),
            "vocabulary_hash": edge_vocabulary.get("vocabulary_hash"),
            "edge_version": edge_vocabulary.get("edge_version"),
            "dimensions_used": dimensions_used,
            "agent_summary": agent_summary,
        },
        "selected_gate": selected_gate,
        "target_binding": {
            "target": target,
            "target_node": _target_node(target, discovery),
        },
        "evaluation_binding": {
            "requested_start": backtest_start,
            "requested_end": "latest",
            "timeframe": "1d",
            "execution_delay_bars": 1,
            "return_basis": "close_to_close",
        },
        "exploration_policy": {
            "first_look_scout": "required_when_fresh",
            "search_width_accounting": "required",
            "empirical_search": "allowed",
            "route_prescription": "forbidden",
        },
        "privacy_scope": {"default": "session_private"},
        "decision_trace": {
            "path": GATE_DECISION_TRACE_FILENAME,
            "authoritative_gate_source": "session_state.gate_envelope",
        },
        "compatibility": {"legacy_mode": str(mode or "standard").strip().lower() or "standard"},
    }
    if user_request["preferences"].get("gate_envelope_shape"):
        envelope["compatibility"]["gate_envelope_shape"] = user_request["preferences"][
            "gate_envelope_shape"
        ]
    canonical = canonicalize_gate_envelope(envelope)
    gate_hash = compute_gate_identity(canonical)
    canonical["identity"]["gate_hash"] = gate_hash
    canonical["gate_hash"] = gate_hash
    return canonical


def canonicalize_gate_envelope(payload: dict) -> dict:
    """Return a deterministic deep copy of a gate envelope."""

    canonical = copy.deepcopy(payload)
    if "edge_vocabulary" in canonical:
        canonical["edge_vocabulary"]["dimensions_used"] = sorted(
            set(canonical["edge_vocabulary"].get("dimensions_used") or [])
        )
    return canonical


def compute_gate_identity(payload: dict) -> str:
    """Compute the single authoritative gate hash."""

    return _stable_hash(_hash_material(payload))


def build_gate_decision_trace(envelope: dict) -> dict:
    """Build the independent generation trace sidecar for a gate envelope."""

    env = canonicalize_gate_envelope(envelope)
    dimensions_used = list(env["edge_vocabulary"].get("dimensions_used") or [])
    trace = {
        "schema": TRACE_SCHEMA,
        "gate_hash": env["gate_hash"],
        "created_before_exploration": True,
        "user_request_snapshot": {
            "raw_text": env["user_request"].get("raw_text", ""),
            "raw_text_hash": env["user_request"].get("raw_text_hash"),
            "normalized": _request_trace_normalized(env["user_request"]),
        },
        "edge_vocabulary_snapshot": {
            "vocabulary_hash": env["edge_vocabulary"].get("vocabulary_hash"),
            "snapshot_scope": "cited_dimensions_only",
            "dimensions_used": dimensions_used,
            "numeric_meaning": env["edge_vocabulary"].get("agent_summary") or {},
        },
        "generation": {
            "generated_gate_id": env["selected_gate"]["gate_id"],
            "rationale_codes": _rationale_codes(env["selected_gate"]),
            "heuristic_inputs": ["objective", "limits", "preferences"],
        },
        "generator": {"name": "abel-invest.gate-generator", "version": 1},
    }
    trace["trace_hash"] = _stable_hash(trace)
    return trace


def write_gate_decision_trace(session: Path, envelope: dict) -> dict:
    """Write the gate decision trace beside session_state.json."""

    trace = build_gate_decision_trace(envelope)
    write_json_file(session / GATE_DECISION_TRACE_FILENAME, trace)
    return trace


def load_or_synthesize_gate_envelope(session_state: dict, discovery: dict | None = None) -> dict:
    """Return an existing envelope or a read-only legacy envelope for old sessions."""

    existing = session_state.get("gate_envelope")
    if isinstance(existing, dict) and existing.get("schema") == GATE_ENVELOPE_SCHEMA:
        return existing
    ticker = str((discovery or {}).get("ticker") or "").strip().upper() or "UNKNOWN"
    mode = str(session_state.get("mode") or "standard")
    return build_gate_envelope(
        ticker=ticker,
        mode=mode,
        objective_text="",
        discovery=discovery,
        backtest_start=None,
        created_at="legacy-read-only",
    )


def render_gate_envelope_summary(envelope: dict) -> str:
    """Render compact factual gate lines for agent_context.md."""

    checks = envelope.get("selected_gate", {}).get("checks") or []
    check_lines = []
    for check in checks:
        threshold = check.get("threshold")
        check_lines.append(
            "- check: "
            f"`{check.get('dimension')}` `{check.get('operator')}` `{json.dumps(threshold)}` "
            f"reason=`{check.get('reason_code')}`"
        )
    if not check_lines:
        check_lines.append("- check: `none`")
    numeric = envelope.get("edge_vocabulary", {}).get("agent_summary") or {}
    numeric_lines = [
        f"- numeric_meaning.{key}: {value}" for key, value in sorted(numeric.items())
    ] or ["- numeric_meaning: `none`"]
    return "\n".join(
        [
            "## Gate Envelope",
            "",
            f"- schema: `{envelope.get('schema')}`",
            f"- selected_gate: `{envelope.get('selected_gate', {}).get('gate_id')}`",
            f"- gate_hash: `{envelope.get('gate_hash')}`",
            "- edge_vocabulary: "
            f"`{envelope.get('edge_vocabulary', {}).get('schema')}` / "
            f"`{envelope.get('edge_vocabulary', {}).get('vocabulary_hash')}`",
            f"- decision_trace: `{GATE_DECISION_TRACE_FILENAME}`",
            f"- route_prescription: `{envelope.get('exploration_policy', {}).get('route_prescription')}`",
            *check_lines,
            *numeric_lines,
        ]
    )


def _generate_selected_gate(user_request: dict, vocabulary: dict) -> dict:
    dim_map = {str(item.get("id")): item for item in vocabulary.get("dimensions") or []}
    objective = user_request.get("objective") or {}
    limits = user_request.get("limits") or {}
    preferences = user_request.get("preferences") or {}
    if user_request.get("defaulted"):
        checks = [
            _check("sharpe", ">", 2.0, "current_default_quality_gate", dim_map),
            _check(
                "edge_required_gates",
                "pass_all",
                True,
                "current_default_required_gates",
                dim_map,
            ),
            _check("search_width", "recorded", True, "evidence_quality_required", dim_map),
        ]
        return _selected_gate(
            gate_id="generated:current-gate-compat-v1",
            meaning=(
                "Current Abel Invest default gate: high return, Sharpe > 2, and all "
                "required Edge gates passing."
            ),
            checks=checks,
        )
    if preferences.get("gate_envelope_shape") == "lite_like":
        checks = [
            _check("total_return", ">", 0, "return_first_positive_return", dim_map),
            _check("max_dd", ">=", -0.15, "beginner_drawdown_guardrail", dim_map),
            _check("position_bounds", "within", [0.0, 1.0], "simple_unlevered_shape", dim_map),
            _check(
                "edge_required_gates",
                "pass_all",
                True,
                "preserve_current_required_gates",
                dim_map,
            ),
            _check("search_width", "recorded", True, "record_evidence_width", dim_map),
        ]
        return _selected_gate(
            gate_id="generated:beginner-simple-current-gate-v1",
            meaning=(
                "Simple low-complexity gate generated from a beginner-friendly request "
                "while preserving current required Edge gates."
            ),
            checks=checks,
        )
    if limits.get("position_bounds") == [0.0, 1.0] and limits.get("max_drawdown") == -0.10:
        checks = [
            _check("total_return", ">", 0, "positive_return_still_required", dim_map),
            _check("max_dd", ">=", -0.10, "avoid_deep_losses_requested", dim_map),
            _check(
                "position_bounds",
                "within",
                [0.0, 1.0],
                "long_only_no_leverage_requested",
                dim_map,
            ),
            _check("search_width", "recorded", True, "evidence_quality_required", dim_map),
        ]
        return _selected_gate(
            gate_id="generated:simple-long-only-defensive-v1",
            meaning=(
                "Simple long-only defensive gate generated from the user's "
                "low-complexity loss-control request."
            ),
            checks=checks,
        )
    if objective.get("metric") == "total_return" and limits.get("max_drawdown") == -0.30:
        checks = [
            _check("total_return", ">", 0, "high_return_primary_objective", dim_map),
            _check("max_dd", ">=", -0.30, "larger_drawdown_explicitly_allowed", dim_map),
            _check("search_width", "recorded", True, "fast_exploration_still_records_width", dim_map),
        ]
        return _selected_gate(
            gate_id="generated:high-return-risk-tolerant-v1",
            meaning="High-return risk-tolerant gate generated from the user's explicit drawdown tolerance.",
            checks=checks,
        )
    checks = [
        _check("total_return", ">", 0, "positive_return_requested", dim_map),
        _check(
            "max_dd",
            ">=",
            float(limits.get("max_drawdown", -0.15)),
            "controlled_drawdown_moderate_risk",
            dim_map,
        ),
        _check("sharpe", ">", 1.0, "robust_quality_requested", dim_map),
        _check("search_width", "recorded", True, "evidence_quality_required", dim_map),
    ]
    return _selected_gate(
        gate_id="generated:daily-balanced-controlled-dd-v1",
        meaning=(
            "Session-specific daily strategy gate generated from the user's "
            "robust-return and controlled-drawdown request."
        ),
        checks=checks,
    )


def _selected_gate(*, gate_id: str, meaning: str, checks: list[dict]) -> dict:
    return {
        "type": "heuristic_generated",
        "gate_id": gate_id,
        "generator_version": GENERATOR_VERSION,
        "meaning": meaning,
        "checks": checks,
    }


def _check(
    dimension: str,
    operator: str,
    threshold: Any,
    reason_code: str,
    dim_map: dict[str, dict],
) -> dict:
    if dimension not in dim_map:
        raise RuntimeError(f"Edge gate vocabulary is missing required dimension: {dimension}")
    return {
        "dimension": dimension,
        "operator": operator,
        "threshold": threshold,
        "edge_dimension": dimension,
        "reason_code": reason_code,
    }


def _normalize_objective(raw_text: str, lowered: str) -> dict:
    if "new to investing" in lowered or "return and drawdown first" in lowered:
        return {
            "metric": "total_return",
            "target": None,
            "secondary": ["max_dd", "sharpe"],
            "plain_language": "simple beginner-friendly strategy with return and drawdown first",
        }
    if "long-only" in lowered or "avoid deep losses" in lowered:
        return {
            "metric": "max_dd",
            "target": -0.10,
            "secondary": ["total_return"],
            "plain_language": "simple long-only strategy that prioritizes avoiding deep losses",
        }
    if "high-return" in lowered or "bigger drawdowns" in lowered:
        return {
            "metric": "total_return",
            "target": None,
            "secondary": ["sharpe"],
            "plain_language": "high-return setup with explicit tolerance for larger drawdowns",
        }
    return {
        "metric": "sharpe",
        "target": None,
        "secondary": ["total_return"],
        "plain_language": _plain_language(raw_text),
    }


def _normalize_limits(lowered: str) -> dict:
    limits: dict[str, Any] = {"max_drawdown": None, "position_bounds": None, "dsr_floor": None}
    if "bigger drawdowns" in lowered or "tolerate bigger" in lowered:
        limits["max_drawdown"] = -0.30
    elif "avoid deep losses" in lowered or "defensive" in lowered:
        limits["max_drawdown"] = -0.10
    elif "controlled drawdown" in lowered or "new to investing" in lowered:
        limits["max_drawdown"] = -0.15
    if "long-only" in lowered or "no leverage" in lowered or "new to investing" in lowered:
        limits["position_bounds"] = [0.0, 1.0]
    if "no leverage" in lowered:
        limits["leverage"] = "none"
    if "new to investing" in lowered:
        limits["edge_required_gates"] = "pass_all_current_required"
    return limits


def _normalize_preferences(lowered: str) -> dict:
    preferences: dict[str, Any] = {
        "time_horizon": "daily_to_swing",
        "complexity_tolerance": "moderate",
        "evidence_depth": "standard",
    }
    if "quickly" in lowered or "fast" in lowered:
        preferences["time_horizon"] = "fast_exploration"
    if "simple" in lowered or "new to investing" in lowered or "long-only" in lowered:
        preferences["complexity_tolerance"] = "low"
    if "new to investing" in lowered:
        preferences["experience_level"] = "beginner"
        preferences["gate_envelope_shape"] = "lite_like"
    if "return and drawdown first" in lowered:
        preferences["report_style"] = "plain_return_drawdown_first"
    return preferences


def _is_unusably_vague(raw_text: str) -> bool:
    if not raw_text:
        return True
    lowered = raw_text.lower().strip()
    return lowered in {
        "find a strategy",
        "find strategy",
        "make money",
        "good strategy",
        "high return",
        "best strategy",
    }


def _plain_language(raw_text: str) -> str:
    lowered = raw_text.lower()
    if "robust" in lowered and "controlled drawdown" in lowered:
        return "robust daily strategy with controlled drawdown"
    return raw_text


def _dimensions_used(selected_gate: dict) -> list[str]:
    return sorted({str(check["dimension"]) for check in selected_gate.get("checks") or []})


def _agent_summary(vocabulary: dict, dimensions_used: list[str]) -> dict[str, str]:
    dim_map = {str(item.get("id")): item for item in vocabulary.get("dimensions") or []}
    return {
        dimension: str(dim_map[dimension].get("numeric_meaning") or "")
        for dimension in dimensions_used
        if dimension in dim_map
    }


def _rationale_codes(selected_gate: dict) -> list[str]:
    return [
        str(check.get("reason_code"))
        for check in selected_gate.get("checks") or []
        if check.get("reason_code")
    ]


def _request_trace_normalized(user_request: dict) -> dict[str, Any]:
    objective = user_request.get("objective") or {}
    limits = user_request.get("limits") or {}
    preferences = user_request.get("preferences") or {}
    return {
        "objective.metric": objective.get("metric"),
        "objective.target": objective.get("target"),
        "objective.secondary": objective.get("secondary") or [],
        "limits.max_drawdown": limits.get("max_drawdown"),
        "limits.position_bounds": limits.get("position_bounds"),
        "preferences.time_horizon": preferences.get("time_horizon"),
        "preferences.complexity_tolerance": preferences.get("complexity_tolerance"),
    }


def _target_node(ticker: str, discovery: dict | None) -> str:
    node = str((discovery or {}).get("target_node") or "").strip()
    return node or f"{ticker}.price"


def _hash_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_hash(payload: Any) -> str:
    material = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def _hash_material(payload: dict) -> dict:
    material = copy.deepcopy(payload)
    _remove_hash_fields(material)
    for key in ["created_at", "frozen_at"]:
        material.pop(key, None)
    if "decision_trace" in material:
        material["decision_trace"].pop("path", None)
    return material


def _remove_hash_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key in list(value):
            if key in {"gate_hash", "trace_hash"}:
                value.pop(key, None)
            else:
                _remove_hash_fields(value[key])
    elif isinstance(value, list):
        for item in value:
            _remove_hash_fields(item)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
