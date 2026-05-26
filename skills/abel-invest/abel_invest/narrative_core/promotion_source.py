"""Source-level observations for hosted paper promotion.

These helpers intentionally expose best-effort AST observations. They should
not be treated as complete semantic proof that a strategy is stateless or
stateful; the rewrite agent still owns source understanding.
"""

from __future__ import annotations

import ast
from typing import Any


PROMOTION_FILE_WRITE_FUNCTIONS = {
    "Path.write_text",
    "Path.write_bytes",
    "np.save",
    "numpy.save",
    "joblib.dump",
    "pickle.dump",
}

TRAINING_CALL_LEAF_NAMES = {
    "calibrate",
    "fit",
    "fit_transform",
    "partial_fit",
    "refit",
    "retrain",
    "train",
    "update_model",
}


def source_overrides_get_paper_signal(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if any(
            isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            and item.name == "get_paper_signal"
            for item in node.body
        ):
            return True
    return False


def paper_signal_design_facts(source: str) -> dict[str, Any]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _empty_design_facts()
    function = find_function(tree, "get_paper_signal")
    if function is None:
        return {
            "trainingCalls": [],
            "sourceTrainingCalls": training_call_facts(tree),
            "usesStateDir": False,
            "writesState": False,
        }
    return {
        "trainingCalls": training_call_facts(function),
        "sourceTrainingCalls": training_call_facts(tree),
        "usesStateDir": function_uses_state_dir(function),
        "writesState": function_writes_state_like_files(function, tree),
    }


def paper_signal_uses_full_runtime_compute(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != "get_paper_signal":
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            callee = call_name(child.func)
            if callee == "compute_runtime_output" or callee.endswith(
                ".compute_runtime_output"
            ):
                return True
    return False


def training_call_facts(function: ast.AST | None) -> list[str]:
    if function is None:
        return []
    calls: list[str] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        callee = call_name(node.func)
        leaf = callee.rsplit(".", 1)[-1].lower()
        if leaf in TRAINING_CALL_LEAF_NAMES and callee not in calls:
            calls.append(callee)
    return calls[:20]


def function_uses_state_dir(function: ast.AST) -> bool:
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            callee = call_name(node.func)
            if callee == "context_runtime_paths" or callee.endswith(
                ".context_runtime_paths"
            ):
                return True
        if isinstance(node, ast.Attribute) and node.attr in {"state_dir", "state"}:
            return True
        if isinstance(node, ast.Constant) and node.value == "_runtime_paths":
            return True
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "state_dir" in node.value or "/state/" in node.value:
                return True
    return False


def function_writes_state_like_files(
    function: ast.AST,
    tree: ast.AST | None = None,
    *,
    _visited: set[str] | None = None,
) -> bool:
    helper_functions: dict[str, ast.AST] = {}
    if tree is not None:
        helper_functions = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
    visited = _visited or set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        callee = call_name(node.func)
        if callee in PROMOTION_FILE_WRITE_FUNCTIONS or callee.endswith(
            (".write_text", ".write_bytes")
        ):
            return True
        lowered = callee.lower()
        if ("write" in lowered or "save" in lowered or "dump" in lowered) and (
            "state" in lowered
            or "checkpoint" in lowered
            or "model" in lowered
            or "scaler" in lowered
        ):
            return True
        helper_name = callee.rsplit(".", 1)[-1]
        helper = helper_functions.get(helper_name)
        if helper is not None and helper_name not in visited:
            visited.add(helper_name)
            if function_writes_state_like_files(helper, tree, _visited=visited):
                return True
    return False


def find_function(
    tree: ast.AST,
    name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            return node
    return None


def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return call_name(node.func)
    return ""


def _empty_design_facts() -> dict[str, Any]:
    return {
        "trainingCalls": [],
        "sourceTrainingCalls": [],
        "usesStateDir": False,
        "writesState": False,
    }
