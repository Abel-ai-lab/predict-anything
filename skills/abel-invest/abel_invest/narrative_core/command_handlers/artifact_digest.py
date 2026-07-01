"""Compact read-only artifact digests for Abel Invest sessions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from abel_invest.narrative_core.contracts.branch_spec import (
    branch_selected_graph_nodes,
    branch_selected_inputs,
    has_explicit_hypothesis,
    load_branch_spec,
)
from abel_invest.narrative_core.contracts.constants import (
    DATA_MANIFEST_FILENAME,
    DEPENDENCIES_FILENAME,
    EVIDENCE_LEDGER_FILENAME,
    EXECUTION_CONSTRAINTS_FILENAME,
    FRONTIER_JSON_FILENAME,
    PROBE_SAMPLES_FILENAME,
    RUNTIME_PROFILE_FILENAME,
)
from abel_invest.narrative_core.contracts.paths import (
    data_manifest_path,
    dependencies_path,
    execution_constraints_path,
    probe_samples_path,
    runtime_profile_path,
)
from abel_invest.narrative_core.evidence.evidence import load_json_object
from abel_invest.narrative_core.io import read_tsv_rows
from abel_invest.narrative_core.session_lifecycle import resolve_workspace_arg_path
from abel_invest.narrative_core.state import load_branches, load_discovery


SCHEMA = "abel-invest.artifact-digest/v1"
METRIC_KEYS = ("lo_adj", "ic", "omega", "sharpe", "max_dd", "pnl", "K")


def artifact_digest_command(args: argparse.Namespace) -> int:
    payload = build_artifact_digest(
        session_arg=getattr(args, "session", None),
        branch_arg=getattr(args, "branch", None),
    )
    if getattr(args, "compact", False):
        payload = build_compact_artifact_digest(payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif getattr(args, "json", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_artifact_digest(payload))
    return 0


def build_artifact_digest(*, session_arg: str | None, branch_arg: str | None) -> dict[str, Any]:
    if not session_arg and not branch_arg:
        raise RuntimeError("artifact-digest requires --session or --branch.")
    if session_arg and branch_arg:
        raise RuntimeError("artifact-digest accepts either --session or --branch, not both.")

    branch_filter: str | None = None
    if branch_arg:
        branch = resolve_workspace_arg_path(branch_arg).resolve()
        session = branch.parent.parent
        branch_filter = branch.name
    else:
        session = resolve_workspace_arg_path(str(session_arg)).resolve()

    discovery = load_discovery(session)
    branches = load_branches(session)
    if branch_filter:
        branches = [branch for branch in branches if branch["branch_id"] == branch_filter]
        if not branches:
            raise RuntimeError(f"Branch not found under session: {branch_filter}")

    branch_digests = [
        build_branch_digest(session=session, branch=branch)
        for branch in branches
    ]
    return {
        "schema": SCHEMA,
        "scope": "branch" if branch_filter else "session",
        "session": str(session),
        "ticker": str(discovery.get("ticker") or session.parent.name.upper()),
        "artifact_paths": session_artifact_paths(session),
        "session_digest": build_session_digest(session=session, branches=branch_digests),
        "branches": branch_digests,
    }


def session_artifact_paths(session: Path) -> dict[str, str]:
    return {
        "agent_context": str(session / "agent_context.md"),
        "events": str(session / "events.tsv"),
        "exploration_path": str(session / "exploration_path.md"),
        "evidence_ledger": str(session / EVIDENCE_LEDGER_FILENAME),
        "frontier": str(session / FRONTIER_JSON_FILENAME),
    }


def build_session_digest(*, session: Path, branches: list[dict[str, Any]]) -> dict[str, Any]:
    ledger = load_json_object(session / EVIDENCE_LEDGER_FILENAME)
    frontier = load_json_object(session / FRONTIER_JSON_FILENAME)
    return {
        "branch_count": len(branches),
        "round_count": sum(int(branch.get("round_count", 0)) for branch in branches),
        "evidence_label_counts": compact_mapping(
            frontier.get("evidence_label_counts")
            or _count_by_key(ledger.get("rows"), "evidence_label")
        ),
        "workflow_blockers": frontier.get("workflow_blockers", 0),
        "frontier": {
            "row_count": frontier.get("row_count", 0),
            "graph_candidates_available": bool(
                (frontier.get("candidate_universe") or {}).get("graph_candidates_available", False)
            ),
            "path_coverage_complete": bool(
                (frontier.get("path_coverage") or {}).get("path_coverage_complete", False)
            ),
            "graph_input_read_gap_count": (
                (frontier.get("input_realization") or {}).get("graph_input_read_gap_count", 0)
            ),
        },
    }


def build_branch_digest(*, session: Path, branch: dict[str, Any]) -> dict[str, Any]:
    branch_dir = Path(branch["branch_dir"])
    branch_spec = load_branch_spec(branch_dir)
    rows = list(branch.get("rows") or [])
    latest = rows[-1] if rows else {}
    result_path = _session_relative_path(session, latest.get("result_path"))
    edge_result = load_json_object(result_path)
    return {
        "branch_id": branch["branch_id"],
        "path": str(branch_dir),
        "round_count": len(rows),
        "declaration": branch_declaration_digest(branch_spec),
        "prepared_inputs": prepared_inputs_digest(branch_dir),
        "latest_round": latest_round_digest(
            session=session,
            row=latest,
            edge_result=edge_result,
            result_path=result_path,
        ),
    }


def branch_declaration_digest(branch_spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "hypothesis_present": has_explicit_hypothesis(str(branch_spec.get("hypothesis") or "")),
        "evidence_intent": str(branch_spec.get("evidence_intent") or ""),
        "input_claim": str(branch_spec.get("input_claim") or ""),
        "mechanism_family": str(branch_spec.get("mechanism_family") or ""),
        "model_family": str(branch_spec.get("model_family") or ""),
        "complexity_class": str(branch_spec.get("complexity_class") or ""),
        "exploration_role": str(branch_spec.get("exploration_role") or ""),
        "requested_start": str(branch_spec.get("requested_start") or ""),
        "selected_inputs": branch_selected_inputs(branch_spec),
        "selected_graph_nodes": branch_selected_graph_nodes(branch_spec),
    }


def prepared_inputs_digest(branch: Path) -> dict[str, Any]:
    dependencies = load_json_object(dependencies_path(branch))
    manifest = load_json_object(data_manifest_path(branch))
    samples = load_json_object(probe_samples_path(branch))
    runtime_profile = load_json_object(runtime_profile_path(branch))
    constraints = load_json_object(execution_constraints_path(branch))
    feeds = [item for item in manifest.get("feeds", []) if isinstance(item, dict)]
    cache_results = [
        item
        for item in ((dependencies.get("cache") or {}).get("results") or [])
        if isinstance(item, dict)
    ]
    return {
        "artifact_presence": {
            DEPENDENCIES_FILENAME: bool(dependencies),
            DATA_MANIFEST_FILENAME: bool(manifest),
            PROBE_SAMPLES_FILENAME: bool(samples),
            RUNTIME_PROFILE_FILENAME: bool(runtime_profile),
            EXECUTION_CONSTRAINTS_FILENAME: bool(constraints),
        },
        "selected_inputs": list(manifest.get("selected_inputs") or []),
        "selected_graph_nodes": list(manifest.get("selected_graph_nodes") or []),
        "feed_count": len(feeds),
        "feed_symbols": compact_list([str(item.get("symbol") or "") for item in feeds]),
        "cache_result_count": len(cache_results),
        "cache_ok_count": sum(1 for item in cache_results if item.get("ok") is True),
        "sample_decision_dates": compact_list(samples.get("sample_decision_dates") or []),
    }


def latest_round_digest(
    *,
    session: Path,
    row: dict[str, str],
    edge_result: dict[str, Any],
    result_path: Path | None,
) -> dict[str, Any]:
    if not row:
        return {}
    report_path = _session_relative_path(session, row.get("report_path"))
    handoff_path = _session_relative_path(session, row.get("handoff_path"))
    return {
        "round_id": row.get("round_id", ""),
        "decision": row.get("decision", ""),
        "verdict": row.get("verdict") or str(edge_result.get("verdict") or ""),
        "score": row.get("score") or str(edge_result.get("score") or ""),
        "metrics": compact_metrics(row=row, edge_result=edge_result),
        "semantic_verdict": str((edge_result.get("semantic") or {}).get("verdict") or ""),
        "failure_count": len(edge_result.get("failures") or []),
        "metric_failure_count": len(edge_result.get("metric_failures") or []),
        "failures": compact_failure_summaries(edge_result),
        "artifact_paths": {
            "result": row.get("result_path", ""),
            "report": row.get("report_path", ""),
            "handoff": row.get("handoff_path", ""),
        },
        "artifact_presence": {
            "result": bool(result_path and result_path.exists()),
            "report": bool(report_path and report_path.exists()),
            "handoff": bool(handoff_path and handoff_path.exists()),
        },
    }


def compact_metrics(*, row: dict[str, str], edge_result: dict[str, Any]) -> dict[str, Any]:
    metrics = {key: row.get(key, "") for key in METRIC_KEYS if row.get(key, "") != ""}
    result_metrics = edge_result.get("metrics") if isinstance(edge_result.get("metrics"), dict) else {}
    fallback_map = {
        "lo_adj": "lo_adjusted",
        "ic": "position_ic",
        "omega": "omega",
        "sharpe": "sharpe",
        "max_dd": "max_dd",
        "pnl": "total_return",
    }
    for output_key, result_key in fallback_map.items():
        if output_key not in metrics and result_key in result_metrics:
            metrics[output_key] = result_metrics[result_key]
    if "K" not in metrics and edge_result.get("K") is not None:
        metrics["K"] = edge_result.get("K")
    return metrics


def compact_failure_summaries(edge_result: dict[str, Any], *, limit: int = 6) -> list[str]:
    failures = edge_result.get("failures") or []
    metric_failures = edge_result.get("metric_failures") or []
    if not metric_failures:
        diagnostics = edge_result.get("diagnostics") or {}
        metric_failures = diagnostics.get("metric_failures") or []

    summaries: list[str] = []
    for failure in failures:
        if isinstance(failure, str) and failure.strip():
            summaries.append(failure.strip())
        elif isinstance(failure, dict):
            summary = str(failure.get("message") or failure.get("summary") or "").strip()
            if summary:
                summaries.append(summary)
    for failure in metric_failures:
        if not isinstance(failure, dict):
            continue
        summary = str(failure.get("message") or failure.get("summary") or "").strip()
        if summary:
            summaries.append(summary)

    unique: list[str] = []
    for summary in summaries:
        if summary not in unique:
            unique.append(summary)
    return unique[:limit]


def render_artifact_digest(payload: dict[str, Any]) -> str:
    session_digest = payload.get("session_digest") or {}
    lines = [
        f"Artifact digest: {payload.get('ticker', '')} {payload.get('scope', '')}",
        f"Session: {payload.get('session', '')}",
        (
            "Summary: "
            f"branches={session_digest.get('branch_count', 0)} "
            f"rounds={session_digest.get('round_count', 0)} "
            f"workflow_blockers={session_digest.get('workflow_blockers', 0)}"
        ),
    ]
    frontier = session_digest.get("frontier") or {}
    if frontier:
        lines.append(
            "Frontier: "
            f"rows={frontier.get('row_count', 0)} "
            f"graph_candidates_available={str(frontier.get('graph_candidates_available', False)).lower()} "
            f"path_coverage_complete={str(frontier.get('path_coverage_complete', False)).lower()} "
            f"graph_input_read_gap_count={frontier.get('graph_input_read_gap_count', 0)}"
        )
    for branch in payload.get("branches") or []:
        latest = branch.get("latest_round") or {}
        metrics = latest.get("metrics") or {}
        lines.append(
            f"- {branch.get('branch_id', '')}: "
            f"rounds={branch.get('round_count', 0)} "
            f"latest={latest.get('round_id', 'none')} "
            f"{latest.get('decision', 'pending')} "
            f"{latest.get('verdict', 'n/a')} "
            f"{latest.get('score', '?/?')} "
            f"sharpe={metrics.get('sharpe', '')} "
            f"pnl={metrics.get('pnl', '')}"
        )
        artifacts = latest.get("artifact_paths") or {}
        if artifacts:
            lines.append(f"  result: {artifacts.get('result', '')}")
            lines.append(f"  report: {artifacts.get('report', '')}")
            lines.append(f"  handoff: {artifacts.get('handoff', '')}")
    return "\n".join(lines)


def build_compact_artifact_digest(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("scope") == "branch":
        return build_compact_branch_digest(payload)
    return build_compact_session_digest(payload)


def build_compact_session_digest(payload: dict[str, Any], *, recent_limit: int = 3) -> dict[str, Any]:
    branches = [branch for branch in payload.get("branches") or [] if isinstance(branch, dict)]
    event_order = session_round_event_order(payload)
    latest_branch = latest_recorded_branch(branches, event_order=event_order)
    best_branch = best_so_far_branch(branches)
    session_digest = payload.get("session_digest") or {}
    return {
        "schema": SCHEMA,
        "mode": "compact",
        "scope": "session",
        "ticker": payload.get("ticker", ""),
        "session": payload.get("session", ""),
        "status": {
            "branch_count": session_digest.get("branch_count", len(branches)),
            "recorded_round_count": session_digest.get("round_count", 0),
            "workflow_blockers": session_digest.get("workflow_blockers", 0),
            "graph_input_read_gap_count": (
                (session_digest.get("frontier") or {}).get("graph_input_read_gap_count", 0)
            ),
        },
        "latest_round": compact_branch_round(latest_branch) if latest_branch else {},
        "best_so_far": compact_branch_round(best_branch) if best_branch else {},
        "recent_branches": [
            compact_branch_index(branch)
            for branch in sorted(
                branches,
                key=lambda branch: branch_sort_key(branch, event_order=event_order),
                reverse=True,
            )[:recent_limit]
        ],
        "paths": payload.get("artifact_paths") or {},
    }


def build_compact_branch_digest(payload: dict[str, Any]) -> dict[str, Any]:
    branches = [branch for branch in payload.get("branches") or [] if isinstance(branch, dict)]
    branch = branches[0] if branches else {}
    declaration = branch.get("declaration") or {}
    latest = branch.get("latest_round") or {}
    return {
        "schema": SCHEMA,
        "mode": "compact",
        "scope": "branch",
        "ticker": payload.get("ticker", ""),
        "session": payload.get("session", ""),
        "branch_id": branch.get("branch_id", ""),
        "path": branch.get("path", ""),
        "declaration": {
            "mechanism_family": declaration.get("mechanism_family", ""),
            "model_family": declaration.get("model_family", ""),
            "selected_inputs": declaration.get("selected_inputs") or [],
            "selected_graph_nodes": declaration.get("selected_graph_nodes") or [],
        },
        "latest_round": {
            **compact_latest_round(latest),
            "decision_facts": compact_decision_facts(branch),
            "artifact_paths": latest.get("artifact_paths") or {},
        },
    }


def compact_branch_round(branch: dict[str, Any]) -> dict[str, Any]:
    declaration = branch.get("declaration") or {}
    latest = branch.get("latest_round") or {}
    return {
        "branch_id": branch.get("branch_id", ""),
        "path": branch.get("path", ""),
        "mechanism_family": declaration.get("mechanism_family", ""),
        "model_family": declaration.get("model_family", ""),
        "selected_inputs": declaration.get("selected_inputs") or [],
        "selected_graph_nodes": declaration.get("selected_graph_nodes") or [],
        **compact_latest_round(latest),
    }


def compact_branch_index(branch: dict[str, Any]) -> dict[str, Any]:
    declaration = branch.get("declaration") or {}
    latest = branch.get("latest_round") or {}
    return {
        "branch_id": branch.get("branch_id", ""),
        "round_count": branch.get("round_count", 0),
        "mechanism_family": declaration.get("mechanism_family", ""),
        "selected_inputs": declaration.get("selected_inputs") or [],
        "latest_status": compact_latest_status(latest),
        "result_path": (latest.get("artifact_paths") or {}).get("result", ""),
    }


def compact_latest_round(latest: dict[str, Any]) -> dict[str, Any]:
    if not latest:
        return {}
    metrics = latest.get("metrics") if isinstance(latest.get("metrics"), dict) else {}
    return {
        "round_id": latest.get("round_id", ""),
        "decision": latest.get("decision", ""),
        "verdict": latest.get("verdict", ""),
        "semantic_verdict": latest.get("semantic_verdict", ""),
        "score": latest.get("score", ""),
        "metrics": {
            key: metrics[key]
            for key in ("sharpe", "lo_adj", "pnl", "max_dd", "ic", "K")
            if key in metrics
        },
        "primary_blockers": compact_list(latest.get("failures") or [], limit=4),
        "result_path": (latest.get("artifact_paths") or {}).get("result", ""),
        "report_path": (latest.get("artifact_paths") or {}).get("report", ""),
    }


def compact_decision_facts(branch: dict[str, Any]) -> dict[str, Any]:
    latest = branch.get("latest_round") or {}
    prepared = branch.get("prepared_inputs") or {}
    latest_artifacts = latest.get("artifact_presence") or {}
    return {
        "graph_inputs_realized": (
            bool((branch.get("declaration") or {}).get("selected_graph_nodes"))
            and int(prepared.get("cache_ok_count") or 0) >= int(prepared.get("feed_count") or 0)
        ),
        "semantic_ready": latest.get("semantic_verdict") == "PASS",
        "has_primary_blocker": bool(latest.get("failures")),
        "artifacts_present": all(bool(value) for value in latest_artifacts.values())
        if latest_artifacts
        else False,
    }


def compact_latest_status(latest: dict[str, Any]) -> str:
    if not latest:
        return "pending"
    return " ".join(
        part
        for part in [
            str(latest.get("round_id") or ""),
            str(latest.get("verdict") or ""),
            str(latest.get("score") or ""),
        ]
        if part
    )


def latest_recorded_branch(
    branches: list[dict[str, Any]], *, event_order: dict[tuple[str, str], int]
) -> dict[str, Any] | None:
    recorded = [branch for branch in branches if branch.get("latest_round")]
    if not recorded:
        return None
    return max(recorded, key=lambda branch: branch_sort_key(branch, event_order=event_order))


def best_so_far_branch(branches: list[dict[str, Any]]) -> dict[str, Any] | None:
    recorded = [branch for branch in branches if branch.get("latest_round")]
    if not recorded:
        return None
    return max(recorded, key=branch_quality_key)


def branch_sort_key(
    branch: dict[str, Any], *, event_order: dict[tuple[str, str], int] | None = None
) -> tuple[int, int, str, str]:
    latest = branch.get("latest_round") or {}
    round_id = str(latest.get("round_id") or "")
    branch_id = str(branch.get("branch_id") or "")
    order = (event_order or {}).get((branch_id, round_id), -1)
    return (order, int(branch.get("round_count") or 0), branch_id, round_id)


def branch_quality_key(branch: dict[str, Any]) -> tuple[int, int, float]:
    latest = branch.get("latest_round") or {}
    return (
        1 if str(latest.get("verdict") or "").upper() == "PASS" else 0,
        score_numerator(str(latest.get("score") or "")),
        metric_float((latest.get("metrics") or {}).get("sharpe")),
    )


def score_numerator(value: str) -> int:
    raw = value.split("/", 1)[0].strip()
    try:
        return int(raw)
    except ValueError:
        return 0


def metric_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def session_round_event_order(payload: dict[str, Any]) -> dict[tuple[str, str], int]:
    session = Path(str(payload.get("session") or ""))
    if not session.exists():
        return {}
    rows = read_tsv_rows(session / "events.tsv")
    order: dict[tuple[str, str], int] = {}
    for index, row in enumerate(rows):
        if row.get("event") != "round_recorded":
            continue
        branch_id = str(row.get("branch_id") or "")
        round_id = str(row.get("round_id") or "")
        if branch_id and round_id:
            order[(branch_id, round_id)] = index
    return order


def compact_list(values: list[Any], *, limit: int = 8) -> list[str]:
    cleaned = [str(item).strip() for item in values if str(item).strip()]
    return cleaned[:limit]


def compact_mapping(value: Any, *, limit: int = 12) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    items = list(value.items())[:limit]
    return {str(key): item for key, item in items}


def _count_by_key(rows: Any, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(rows, list):
        return counts
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = str(row.get(key) or "").strip()
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def _session_relative_path(session: Path, value: Any) -> Path | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_absolute() else session / path
