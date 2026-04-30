"""Evidence classification helpers for strategy discovery."""

from __future__ import annotations

from abel_invest.branch_spec import ordered_unique_strings, ordered_unique_upper
from abel_invest.constants import (
    BROAD_CHANGED_DIMENSIONS,
    CHANGED_DIMENSIONS,
    LOCAL_CHANGED_DIMENSIONS,
)
from abel_invest.frontier import branch_family_key, exploration_neighborhood_key


def build_input_realization(
    *,
    declaration: dict[str, object],
    runtime: dict[str, object],
) -> dict[str, object]:
    declared_claim = str(declaration.get("input_claim") or "unspecified")
    declared_inputs = ordered_unique_upper(declaration.get("selected_inputs") or [])
    prepared_inputs = ordered_unique_upper(runtime.get("prepared_selected_inputs") or declared_inputs)
    actual_reads = ordered_unique_upper(runtime.get("auxiliary_reads") or [])
    prepared_set = set(prepared_inputs or declared_inputs)
    actual_set = set(actual_reads)
    selected_graph_reads = sorted(prepared_set.intersection(actual_set))

    if not actual_reads:
        realized_claim = "target_only"
    elif declared_claim == "graph_supported" and selected_graph_reads:
        realized_claim = "graph_supported"
    elif declared_claim in {"supplement", "mixed"}:
        realized_claim = declared_claim
    else:
        realized_claim = "supplemental"

    graph_input_read_gap = (
        declared_claim == "graph_supported"
        and bool(prepared_set)
        and not selected_graph_reads
    )
    return {
        "declared_input_claim": declared_claim,
        "prepared_auxiliary_inputs": prepared_inputs,
        "actual_auxiliary_reads": actual_reads,
        "realized_input_claim": realized_claim,
        "selected_graph_reads": selected_graph_reads,
        "graph_input_read_gap": graph_input_read_gap,
    }


def parse_changed_dimensions(value: object) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        text = str(value or "").strip()
        if not text or text == "none":
            return []
        raw_items = text.replace(";", ",").split(",")
    return [
        item
        for item in ordered_unique_strings(str(raw).strip().lower() for raw in raw_items)
        if item in CHANGED_DIMENSIONS
    ]


def normalize_optional_note(value: object) -> str:
    text = str(value or "").strip()
    return "" if text in {"", "not recorded", "none"} else text


def derive_exploration_class(
    *,
    run_type: str,
    declared_mode: str,
    evidence_label: str,
    declaration: dict[str, object],
    changed_dimensions: list[str],
) -> str:
    role = str(declaration.get("exploration_role") or "unspecified")
    input_claim = str(declaration.get("input_claim") or "")
    intent = str(declaration.get("evidence_intent") or "")
    if run_type == "debug" or evidence_label in {"diagnostic_only", "workflow_blocker", "runtime_invalid"}:
        return "diagnostic"
    if role == "diagnostic" or intent == "diagnostic":
        return "diagnostic"
    if role in {"control", "ablation"} or intent == "control" or input_claim == "target_only":
        return "control"
    if role == "expansion_probe" or any(item in BROAD_CHANGED_DIMENSIONS for item in changed_dimensions):
        return "broad_explore"
    if role == "refinement" or any(item in LOCAL_CHANGED_DIMENSIONS for item in changed_dimensions):
        return "local_refinement"
    if declared_mode == "exploit":
        return "local_refinement"
    return "broad_explore"


def annotate_exploration_protocol(rows: list[dict[str, object]]) -> None:
    round_rows = [row for row in rows if row.get("run_type") == "round"]
    family_keys = {
        branch_family_key(row)
        for row in round_rows
        if branch_family_key(row)
    }
    branch_seen: dict[str, int] = {}
    neighborhood_fail_seen: dict[str, int] = {}

    for row in rows:
        neighborhood = exploration_neighborhood_key(row)
        row["exploration_neighborhood_key"] = neighborhood
        row["branch_family_key"] = branch_family_key(row)
        row["branch_family_count"] = len(family_keys)
        if row.get("run_type") != "round":
            row["same_branch_round_index"] = 0
            row["same_neighborhood_failed_rows"] = 0
            continue
        branch_id = str(row.get("branch_id") or "unknown")
        branch_seen[branch_id] = branch_seen.get(branch_id, 0) + 1
        same_branch_rounds = branch_seen[branch_id]
        failed_before = neighborhood_fail_seen.get(neighborhood, 0)
        if (
            row.get("derived_exploration_class") == "broad_explore"
            and same_branch_rounds > 1
            and not row.get("changed_dimensions")
        ):
            row["derived_exploration_class"] = "local_refinement"
        row["same_branch_round_index"] = same_branch_rounds
        row["same_neighborhood_failed_rows"] = failed_before
        if row.get("comparable") and row.get("verdict") == "FAIL":
            neighborhood_fail_seen[neighborhood] = failed_before + 1


def metric_string(result: dict, key: str) -> str:
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    value = metrics.get(key)
    if value is None:
        return ""
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def evidence_runtime_facts(result: dict) -> dict[str, object]:
    runtime_facts = result.get("runtime_facts") if isinstance(result.get("runtime_facts"), dict) else {}
    read_summary = runtime_facts.get("read_summary") if isinstance(runtime_facts.get("read_summary"), dict) else {}
    prepared_summary = runtime_facts.get("prepared_inputs") if isinstance(runtime_facts.get("prepared_inputs"), dict) else {}
    temporal_visibility = (
        runtime_facts.get("temporal_visibility")
        if isinstance(runtime_facts.get("temporal_visibility"), dict)
        else {}
    )
    if runtime_facts:
        auxiliary_reads = sorted(
            {
                str(item).strip().upper()
                for item in (read_summary.get("auxiliary_reads") or prepared_summary.get("traced_inputs") or [])
                if str(item).strip()
            }
        )
        prepared_selected = ordered_unique_upper(prepared_summary.get("selected_inputs") or [])
        prepared_traced = ordered_unique_upper(prepared_summary.get("traced_inputs") or auxiliary_reads)
        metric_failures = [
            item
            for item in (runtime_facts.get("metric_failures") or [])
            if isinstance(item, dict)
        ]
        return {
            "verdict": str(runtime_facts.get("verdict") or "missing").upper(),
            "semantic_verdict": str(runtime_facts.get("semantic_verdict") or "missing").upper(),
            "runtime_stage": str(runtime_facts.get("runtime_stage") or "missing"),
            "workflow_status": str(runtime_facts.get("workflow_status") or "not_completed"),
            "failure_signature": str(runtime_facts.get("failure_signature") or "missing"),
            "read_count": int(read_summary.get("read_count") or 0),
            "auxiliary_reads": auxiliary_reads,
            "prepared_selected_inputs": prepared_selected,
            "prepared_traced_inputs": prepared_traced,
            "metric_failures": metric_failures,
            "metric_failure_metrics": ordered_unique_strings(
                str(item.get("metric") or "").strip()
                for item in metric_failures
                if str(item.get("metric") or "").strip()
            ),
            "prepared_issue_kinds": [
                str(item).strip()
                for item in (temporal_visibility.get("issue_kinds") or [])
                if str(item).strip()
            ],
            "has_prepared_error": bool(temporal_visibility.get("has_error", False)),
        }
    diagnostics = result.get("diagnostics") if isinstance(result.get("diagnostics"), dict) else {}
    semantic = result.get("semantic") if isinstance(result.get("semantic"), dict) else {}
    prepared = semantic.get("prepared_inputs") if isinstance(semantic.get("prepared_inputs"), dict) else {}
    auxiliary_reads = [
        str(item).strip().upper()
        for item in (prepared.get("traced_inputs") or [])
        if str(item).strip()
    ]
    issues = [
        item
        for item in (prepared.get("issues") or [])
        if isinstance(item, dict)
    ]
    verdict = str(result.get("verdict") or "missing").upper()
    runtime_stage = str(diagnostics.get("runtime_stage") or "missing")
    validation_completed = runtime_stage == "validation" and verdict in {"PASS", "FAIL"}
    metric_failures = [
        item
        for item in (result.get("metric_failures") or diagnostics.get("metric_failures") or [])
        if isinstance(item, dict)
    ]
    return {
        "verdict": verdict,
        "semantic_verdict": str(semantic.get("verdict") or "missing").upper(),
        "runtime_stage": runtime_stage,
        "workflow_status": "evaluation_completed" if validation_completed else "not_completed",
        "failure_signature": str(diagnostics.get("failure_signature") or "missing"),
        "read_count": int(semantic.get("read_count") or 0),
        "auxiliary_reads": sorted(set(auxiliary_reads)),
        "prepared_selected_inputs": ordered_unique_upper(prepared.get("selected_inputs") or []),
        "prepared_traced_inputs": ordered_unique_upper(prepared.get("traced_inputs") or auxiliary_reads),
        "metric_failures": metric_failures,
        "metric_failure_metrics": ordered_unique_strings(
            str(item.get("metric") or "").strip()
            for item in metric_failures
            if str(item.get("metric") or "").strip()
        ),
        "prepared_issue_kinds": [
            str(item.get("kind") or "").strip()
            for item in issues
            if str(item.get("kind") or "").strip()
        ],
        "has_prepared_error": any(str(item.get("severity") or "").lower() == "error" for item in issues),
    }


def evidence_comparability(
    *,
    declaration: dict[str, object],
    runtime: dict[str, object],
    validation_completed: bool,
    result: dict,
) -> tuple[bool, str]:
    if not validation_completed:
        return False, "validation_not_completed"
    if not declaration["protocol_complete"]:
        return False, "declaration_protocol_incomplete"
    effective_window = result.get("effective_window") if isinstance(result.get("effective_window"), dict) else {}
    if not effective_window.get("start") or not effective_window.get("end"):
        return False, "missing_effective_window"
    if runtime.get("has_prepared_error"):
        return False, "prepared_input_error"
    return True, "comparable"


def derive_evidence_label(
    *,
    declaration: dict[str, object],
    runtime: dict[str, object],
    validation_completed: bool,
    comparable: bool,
    run_type: str,
    result_present: bool,
    engine_scaffold_status: str = "",
) -> str:
    runtime_stage = str(runtime["runtime_stage"])
    verdict = str(runtime["verdict"])
    semantic_verdict = str(runtime["semantic_verdict"])
    auxiliary_reads = list(runtime["auxiliary_reads"])

    if not result_present:
        return "workflow_blocker"
    if verdict == "ERROR" and runtime_stage in {"context_build", "data_access", "load_engine", "compute_strategy", "missing", "workflow"}:
        return "workflow_blocker"
    if semantic_verdict == "ERROR" or runtime.get("has_prepared_error"):
        return "runtime_invalid"
    if run_type == "debug":
        return "diagnostic_only"
    if engine_scaffold_status == "starter_scaffold":
        return "diagnostic_only"
    if not declaration["protocol_complete"]:
        return "protocol_incomplete"
    if declaration["evidence_intent"] == "diagnostic":
        return "diagnostic_only"
    if not validation_completed:
        return "workflow_blocker"
    if not comparable:
        return "non_comparable"
    if not auxiliary_reads:
        return "target_control_evidence"
    if declaration["input_claim"] == "graph_supported":
        selected = set(str(item).upper() for item in declaration["selected_inputs"])
        if selected and selected.intersection(auxiliary_reads):
            return "candidate_causal_evidence"
    if declaration["input_claim"] in {"supplement", "mixed"}:
        return "supplemental_evidence"
    return "supplemental_evidence"
