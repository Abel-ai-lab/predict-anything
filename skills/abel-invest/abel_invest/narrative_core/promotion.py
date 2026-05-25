"""Strategy promotion helpers for paper-ready runtime state boundaries."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any, Callable

from abel_edge.research.promotion_gate import build_promotion_gate_report


LOCAL_RUNTIME_STATE_DIR = Path(".abel-runtime") / "state"
PROMOTION_MODE_ZERO_CHANGE = "zero_change"
PROMOTION_MODE_NEEDS_AGENT_REFACTOR = "needs_agent_refactor"
PROMOTION_MODE_AGENT_REFACTOR = "agent_refactor"
PROMOTION_GATE_FILENAME = "promotion-gate.json"
PROMOTION_PATCH_FILENAME = "promotion.patch"
PROMOTION_REFACTOR_REPORT_FILENAME = "refactor-report.json"
PROMOTION_REFACTOR_REQUEST_FILENAME = "refactor-request.json"
PROMOTION_DEPENDENCY_SCAN_FILENAME = "dependency-scan.json"
PROMOTION_PACKAGING_PLAN_FILENAME = "packaging-plan.json"
PROMOTION_AGENT_REPORT_SCHEMA = "abel-invest.agent-refactor-report/v1"
PROMOTION_AGENT_REQUEST_SCHEMA = "abel-invest.agent-refactor-request/v1"
PROMOTION_HOSTED_REWRITE_SCOPE = "hosted_paper_rewrite"
STATE_SELF_CHECK_FILE_SUFFIXES = {
    ".joblib",
    ".npy",
    ".npz",
    ".onnx",
    ".pkl",
    ".pickle",
    ".pt",
    ".pth",
    ".safetensors",
}
STATE_SELF_CHECK_DIRECTORY_PARTS = {
    "cache",
    "caches",
    "checkpoint",
    "checkpoints",
    "model",
    "models",
    "registry",
    "registries",
    "scaler",
    "scalers",
    "state",
    "states",
}
STATE_SELF_CHECK_DIRECTORY_SUFFIXES = STATE_SELF_CHECK_FILE_SUFFIXES | {
    ".json",
    ".yaml",
    ".yml",
}
STATE_SELF_CHECK_SOURCE_KEYWORDS = (
    "cache",
    "checkpoint",
    "joblib",
    "model",
    "pickle",
    "registry",
    "scaler",
    "state",
)
STATE_SELF_CHECK_SOURCE_PATH_PARTS = {
    "checkpoint",
    "checkpoints",
    "model",
    "models",
    "registry",
    "registries",
    "scaler",
    "scalers",
}
PROMOTION_ALLOWED_RUNTIME_IMPORTS = {
    "abel_edge",
    "numpy",
    "pandas",
}
PROMOTION_FILE_READ_FUNCTIONS = {
    "open",
    "pd.read_csv",
    "pd.read_json",
    "pd.read_parquet",
    "pd.read_pickle",
    "pandas.read_csv",
    "pandas.read_json",
    "pandas.read_parquet",
    "pandas.read_pickle",
    "np.load",
    "numpy.load",
    "joblib.load",
    "pickle.load",
}
PROMOTION_FILE_WRITE_FUNCTIONS = {
    "Path.write_text",
    "Path.write_bytes",
    "np.save",
    "numpy.save",
    "joblib.dump",
    "pickle.dump",
}
PROMOTION_BRANCH_FILE_SUFFIXES = {
    ".csv",
    ".json",
    ".joblib",
    ".npy",
    ".npz",
    ".pkl",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class PromotionPackagedFile:
    artifact_path: str
    source_path: Path
    purpose: str
    role: str

    @property
    def path(self) -> str:
        if self.artifact_path.startswith("runtime/initial-state/"):
            return self.artifact_path.removeprefix("runtime/initial-state/")
        if self.artifact_path.startswith("strategy/"):
            return self.artifact_path.removeprefix("strategy/")
        return self.artifact_path


@dataclass(frozen=True)
class PromotionResult:
    mode: str
    strategy_source_path: Path
    packaged_files: tuple[PromotionPackagedFile, ...]
    extra_source_map: dict[str, Path]
    patch_path: Path | None
    gate_path: Path
    refactor_report_path: Path | None
    report: dict[str, Any]

    @property
    def adapted(self) -> bool:
        return self.mode == PROMOTION_MODE_AGENT_REFACTOR


class PromotionNeedsAgentRefactor(RuntimeError):
    """Raised when promotion needs agent-assisted refactor before publishing."""


def prepare_promotion(
    candidate: Any,
    *,
    destination: Path,
    strategy_entrypoint: str,
    is_denylisted_source: Callable[[Path], bool],
    sha256_file: Callable[[Path], str],
    verify_promotion: Callable[..., dict[str, Any]] | None = None,
) -> PromotionResult:
    promoted_dir = destination / "promoted"
    promoted_dir.mkdir(parents=True, exist_ok=True)
    promoted_source = promoted_dir / "engine.py"
    existing_refactor_report = promoted_dir / PROMOTION_REFACTOR_REPORT_FILENAME
    original_text = candidate.strategy_source_path.read_text(encoding="utf-8")
    agent_refactor_ready = promoted_source.is_file() and existing_refactor_report.is_file()
    dependency_scan = _collect_hosted_paper_dependency_scan(
        candidate.branch,
        strategy_source_path=candidate.strategy_source_path,
        is_denylisted_source=is_denylisted_source,
    )
    dependency_scan_path = None
    packaging_plan_path = None

    hosted_rewrite_signals = _hosted_paper_rewrite_signals(dependency_scan)
    if hosted_rewrite_signals and not agent_refactor_ready:
        promoted_source.write_text(original_text, encoding="utf-8")
        dependency_scan_path = _write_dependency_scan(promoted_dir, dependency_scan)
        request_path = _write_hosted_paper_rewrite_request(
            promoted_dir,
            branch=candidate.branch,
            source_path=promoted_source,
            dependency_scan=dependency_scan,
            scan_path=dependency_scan_path,
            signals=hosted_rewrite_signals,
        )
        raise PromotionNeedsAgentRefactor(
            "hosted paper rewrite required before promotion; "
            f"{len(hosted_rewrite_signals)} hosted-paper risk signal(s) found; "
            f"request written to {request_path}"
        )

    strategy_source_path = candidate.strategy_source_path
    patch_path = None
    refactor_report_path = None
    mode = PROMOTION_MODE_ZERO_CHANGE
    refactor_replacements: list[dict[str, str]] = []
    refactor_summary = ""
    packaged_files: tuple[PromotionPackagedFile, ...] = ()
    refactor_report: dict[str, Any] | None = None
    promoted_text = original_text

    if agent_refactor_ready:
        promoted_text = promoted_source.read_text(encoding="utf-8")
        refactor_report = _load_agent_refactor_report(existing_refactor_report)
        refactor_replacements = _report_replacements(refactor_report)
        if not _report_has_hosted_rewrite_contract(refactor_report):
            raise PromotionNeedsAgentRefactor(
                "agent refactor report must use hosted_paper_rewrite scope"
            )
        refactor_summary = _clean(refactor_report.get("summary")) or (
            "Agent refactored the promoted strategy for hosted paper."
        )
        packaged_files = tuple(
            _report_packaged_files(
                refactor_report,
                branch=candidate.branch,
                is_denylisted_source=is_denylisted_source,
            )
        )
        artifact_refactor_report_path = _write_artifact_refactor_report(
            promoted_dir,
            refactor_report,
        )
        _validate_agent_paper_signal_contract(
            refactor_report,
            promoted_text,
            require_paper_signal=True,
        )
        mode = PROMOTION_MODE_AGENT_REFACTOR
        strategy_source_path = promoted_source
        refactor_report_path = artifact_refactor_report_path

    replacements = refactor_replacements
    if mode == PROMOTION_MODE_AGENT_REFACTOR:
        dependency_scan_path = _write_dependency_scan(
            promoted_dir,
            _collect_hosted_paper_dependency_scan(
                candidate.branch,
                strategy_source_path=strategy_source_path,
                is_denylisted_source=is_denylisted_source,
            ),
        )
        packaging_plan_path = _write_packaging_plan(
            promoted_dir,
            packaged_files=packaged_files,
            refactor_report=refactor_report,
        )
        patch_path = promoted_dir / PROMOTION_PATCH_FILENAME
        patch_path.write_text(
            _simple_patch_summary(
                candidate.strategy_source_path,
                replacements,
                scope=_clean(refactor_report.get("scope"))
                if refactor_report is not None
                else "agent_refactor",
            ),
            encoding="utf-8",
        )
    _validate_promoted_source_static(strategy_source_path)

    original_sha = sha256_file(candidate.strategy_source_path)
    promoted_sha = sha256_file(strategy_source_path)
    refactor_payload = (
        {
            "kind": PROMOTION_HOSTED_REWRITE_SCOPE,
            "summary": refactor_summary,
            "patchPath": f"edge/{PROMOTION_PATCH_FILENAME}",
            "reportPath": f"edge/{PROMOTION_REFACTOR_REPORT_FILENAME}",
        }
        if mode == PROMOTION_MODE_AGENT_REFACTOR
        else None
    )
    behavior_equivalence = _default_behavior_equivalence(
        mode=mode,
        replacements=replacements,
    )
    paper_dry_run = {
        "status": "passed",
        "method": "source_round_edge_result",
    }
    if verify_promotion is not None:
        verification = verify_promotion(
            candidate=candidate,
            promotion_mode=mode,
            promoted_source_path=strategy_source_path,
            replacements=replacements,
            packaged_files=packaged_files,
            destination=destination,
        )
        if isinstance(verification.get("behavior_equivalence"), dict):
            behavior_equivalence = verification["behavior_equivalence"]
        if isinstance(verification.get("paper_dry_run"), dict):
            paper_dry_run = verification["paper_dry_run"]
    gate_path = destination / PROMOTION_GATE_FILENAME
    gate_report = build_promotion_gate_report(
        promotion_mode=mode,
        original_source_sha256=original_sha,
        promoted_source_sha256=promoted_sha,
        patch_sha256=sha256_file(patch_path) if patch_path is not None else None,
        refactor=refactor_payload,
        state_entries=packaged_files,
        behavior_equivalence=behavior_equivalence,
        paper_dry_run=paper_dry_run,
    )
    gate_path.write_text(
        json.dumps(gate_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if gate_report.get("status") != "passed":
        raise PromotionNeedsAgentRefactor(
            f"promotion gate did not pass: {gate_report.get('status')}"
        )

    extra_source_map = {strategy_entrypoint: strategy_source_path}
    for item in packaged_files:
        extra_source_map[item.artifact_path] = item.source_path
    extra_source_map[f"edge/{PROMOTION_GATE_FILENAME}"] = gate_path
    if patch_path is not None:
        extra_source_map[f"edge/{PROMOTION_PATCH_FILENAME}"] = patch_path
    if dependency_scan_path is not None:
        extra_source_map[f"edge/{PROMOTION_DEPENDENCY_SCAN_FILENAME}"] = dependency_scan_path
    if packaging_plan_path is not None:
        extra_source_map[f"edge/{PROMOTION_PACKAGING_PLAN_FILENAME}"] = packaging_plan_path
    if mode == PROMOTION_MODE_AGENT_REFACTOR:
        assert refactor_report_path is not None
        extra_source_map[f"edge/{PROMOTION_REFACTOR_REPORT_FILENAME}"] = refactor_report_path

    return PromotionResult(
        mode=mode,
        strategy_source_path=strategy_source_path,
        packaged_files=packaged_files,
        extra_source_map=extra_source_map,
        patch_path=patch_path,
        gate_path=gate_path,
        refactor_report_path=refactor_report_path,
        report={
            "mode": mode,
            "initialStateFileCount": len(
                [
                    item
                    for item in packaged_files
                    if item.role == "initial_state"
                    or item.artifact_path.startswith("runtime/initial-state/")
                ]
            ),
            "packagedFileCount": len(packaged_files),
            "replacementCount": len(replacements),
            "refactorReplacementCount": len(refactor_replacements),
            "refactorSummary": refactor_summary,
            "patchPath": str(patch_path) if patch_path is not None else "",
            "refactorReportPath": str(refactor_report_path)
            if refactor_report_path is not None
            else "",
            "gatePath": str(gate_path),
            "dependencyScanPath": str(dependency_scan_path)
            if dependency_scan_path is not None
            else "",
            "packagingPlanPath": str(packaging_plan_path)
            if packaging_plan_path is not None
            else "",
        },
    )


def _collect_hosted_paper_dependency_scan(
    branch: Path,
    *,
    strategy_source_path: Path,
    is_denylisted_source: Callable[[Path], bool],
) -> dict[str, Any]:
    source = strategy_source_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None
    imports = _source_import_facts(tree)
    file_accesses = _source_file_access_facts(tree)
    absolute_literals = [
        {"value": literal, "reason": "developer_local_absolute_path"}
        for literal in _source_string_literals(source)
        if _is_local_absolute_path(literal)
    ]
    branch_files = []
    state_dependency_signals = _state_dependency_signals(
        branch,
        strategy_source_path=strategy_source_path,
        is_denylisted_source=is_denylisted_source,
    )
    for path in sorted(branch.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(branch)
        if relative.name == "engine.py" or is_denylisted_source(relative):
            continue
        if relative.suffix.lower() not in PROMOTION_BRANCH_FILE_SUFFIXES:
            continue
        branch_files.append(
            {
                "path": relative.as_posix(),
                "suffix": relative.suffix.lower(),
                "bytes": path.stat().st_size,
            }
        )
    return {
        "schema": "abel-invest.hosted-paper-dependency-scan/v1",
        "sourcePath": _display_source_path(branch, strategy_source_path),
        "paperSignal": {
            "implemented": _source_overrides_get_paper_signal(source),
        },
        "absolutePathLiterals": absolute_literals,
        "fileAccesses": file_accesses,
        "imports": imports,
        "branchFiles": branch_files[:200],
        "stateDependencies": state_dependency_signals,
    }


def _hosted_paper_rewrite_signals(scan: dict[str, Any]) -> list[dict[str, str]]:
    signals: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    paper_signal = scan.get("paperSignal")
    if not isinstance(paper_signal, dict) or paper_signal.get("implemented") is not True:
        _append_hosted_rewrite_signal(
            signals,
            seen,
            kind="missing_paper_signal",
            value="get_paper_signal",
            reason="promoted strategy must implement hosted paper fast path",
        )
    for item in scan.get("absolutePathLiterals") or []:
        if not isinstance(item, dict):
            continue
        _append_hosted_rewrite_signal(
            signals,
            seen,
            kind="developer_local_absolute_path",
            value=_clean(item.get("value")),
            reason="promoted strategy must not depend on developer-local absolute paths",
        )
    for item in scan.get("fileAccesses") or []:
        if not isinstance(item, dict):
            continue
        value = _clean(item.get("path"))
        if not _is_local_absolute_path(value):
            continue
        _append_hosted_rewrite_signal(
            signals,
            seen,
            kind="developer_local_file_access",
            value=value,
            reason="file dependency must be packaged and read through runtime paths",
        )
    for item in scan.get("imports") or []:
        if not isinstance(item, dict):
            continue
        if item.get("classification") in {"stdlib", "allowed_runtime"}:
            continue
        _append_hosted_rewrite_signal(
            signals,
            seen,
            kind="nonstandard_import",
            value=_clean(item.get("module")),
            reason="non-standard imports must be confirmed for hosted paper runtime",
        )
    for item in scan.get("stateDependencies") or []:
        if not isinstance(item, dict):
            continue
        _append_hosted_rewrite_signal(
            signals,
            seen,
            kind=_clean(item.get("kind")) or "state_dependency",
            value=_clean(item.get("value")),
            reason=_clean(item.get("reason"))
            or "state-like dependency must be classified by hosted rewrite",
        )
    return signals


def _append_hosted_rewrite_signal(
    signals: list[dict[str, str]],
    seen: set[tuple[str, str]],
    *,
    kind: str,
    value: str,
    reason: str,
) -> None:
    if not value:
        return
    key = (kind, value)
    if key in seen:
        return
    seen.add(key)
    signals.append({"kind": kind, "value": value, "reason": reason})


def _write_dependency_scan(promoted_dir: Path, scan: dict[str, Any]) -> Path:
    path = promoted_dir / PROMOTION_DEPENDENCY_SCAN_FILENAME
    path.write_text(
        json.dumps(scan, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def _write_packaging_plan(
    promoted_dir: Path,
    *,
    packaged_files: tuple[PromotionPackagedFile, ...],
    refactor_report: dict[str, Any] | None,
) -> Path:
    path = promoted_dir / PROMOTION_PACKAGING_PLAN_FILENAME
    payload = {
        "schema": "abel-invest.promotion-packaging-plan/v1",
        "source": {
            "refactorReportSummary": _clean((refactor_report or {}).get("summary")),
        },
        "files": [
            {
                "artifactPath": item.artifact_path,
                "sourceRef": item.source_path.name,
                "purpose": item.purpose,
                "role": item.role,
            }
            for item in packaged_files
        ],
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def _write_artifact_refactor_report(
    promoted_dir: Path,
    report: dict[str, Any],
) -> Path:
    path = promoted_dir / "refactor-report.artifact.json"
    payload = json.loads(json.dumps(report))
    paths = payload.get("paths")
    if isinstance(paths, dict):
        paths["packagedFiles"] = [
            _sanitized_packaged_file_entry(item)
            for item in paths.get("packagedFiles") or []
            if isinstance(item, dict)
        ]
        paths["initialStateFiles"] = [
            _sanitized_packaged_file_entry(item)
            for item in paths.get("initialStateFiles") or []
            if isinstance(item, dict)
        ]
    if isinstance(payload.get("packagedFiles"), list):
        payload["packagedFiles"] = [
            _sanitized_packaged_file_entry(item)
            for item in payload.get("packagedFiles") or []
            if isinstance(item, dict)
        ]
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def _sanitized_packaged_file_entry(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in item.items()
        if key not in {"source", "sourcePath", "localSourcePath"}
    }


def _write_hosted_paper_rewrite_request(
    promoted_dir: Path,
    *,
    branch: Path,
    source_path: Path,
    dependency_scan: dict[str, Any],
    scan_path: Path,
    signals: list[dict[str, str]],
) -> Path:
    request_path = promoted_dir / PROMOTION_REFACTOR_REQUEST_FILENAME
    request_path.write_text(
        json.dumps(
            {
                "schema": PROMOTION_AGENT_REQUEST_SCHEMA,
                "kind": "hosted_paper_rewrite",
                "sourcePath": str(source_path),
                "scope": PROMOTION_HOSTED_REWRITE_SCOPE,
                "dependencyScanPath": str(scan_path),
                "signals": signals,
                "facts": dependency_scan,
                "runtimeContract": {
                    "baseAssets": "read immutable files through ctx.paths.base_strategy",
                    "runtimeConfig": "read immutable runtime config through ctx.paths.runtime",
                    "strategyState": (
                        "read/write mutable strategy state under "
                        "ctx.state_dir / 'strategy'"
                    ),
                    "paperCursor": (
                        "use runtime paper cursor helpers or paper-log.csv semantics; "
                        "do not use paper-log.csv as private strategy state"
                    ),
                },
                "requiredReportTemplate": {
                    "schema": PROMOTION_AGENT_REPORT_SCHEMA,
                    "kind": PROMOTION_HOSTED_REWRITE_SCOPE,
                    "summary": "<brief hosted paper rewrite summary>",
                    "scope": PROMOTION_HOSTED_REWRITE_SCOPE,
                    "paths": {
                        "packagedFiles": [
                            {
                                "artifactPath": "strategy/assets/<file>",
                                "sourcePath": "<absolute or branch-relative source file>",
                                "purpose": "<why the promoted strategy needs this read-only asset>",
                            }
                        ],
                        "initialStateFiles": [
                            {
                                "artifactPath": "runtime/initial-state/strategy/<file>",
                                "sourcePath": "<absolute or branch-relative source file>",
                                "purpose": "<why paper startup needs this mutable state seed>",
                            }
                        ],
                    },
                    "paperSignal": {
                        "implemented": True,
                        "incrementalReady": True,
                        "notes": "uses runtime cursor plus strategy-owned state",
                    },
                    "limitations": [],
                    "replacements": [],
                },
                "instructions": (
                    "Refactor only the promoted copy. Remove developer-local paths, "
                    "package required external read-only files through paths.packagedFiles, "
                    "package required mutable startup state through paths.initialStateFiles, "
                    "read immutable assets through ctx.paths.base_strategy, write mutable "
                    "strategy state only under ctx.state_dir / 'strategy', and implement "
                    "get_paper_signal(as_of=...) when the strategy can produce hosted "
                    "paper signals. Then write refactor-report.json beside this request "
                    "and rerun the same publish or promote command. If the candidate "
                    "cannot safely produce continuing paper signals, report that as a "
                    "limitation instead of forcing promotion."
                ),
                "branchPath": str(branch),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return request_path


def _report_has_hosted_rewrite_contract(report: dict[str, Any]) -> bool:
    return (
        _clean(report.get("kind")) == PROMOTION_HOSTED_REWRITE_SCOPE
        and _clean(report.get("scope")) == PROMOTION_HOSTED_REWRITE_SCOPE
    )


def _report_packaged_files(
    report: dict[str, Any],
    *,
    branch: Path,
    is_denylisted_source: Callable[[Path], bool],
) -> list[PromotionPackagedFile]:
    paths = report.get("paths")
    packaged_groups: list[tuple[Any, str | None]] = []
    if isinstance(paths, dict):
        packaged_groups.append((paths.get("packagedFiles") or [], None))
        packaged_groups.append((paths.get("initialStateFiles") or [], "initial_state"))
    else:
        packaged_groups.append(([], None))
    if isinstance(report.get("packagedFiles"), list):
        packaged_groups.append((report.get("packagedFiles") or [], None))

    packaged: list[PromotionPackagedFile] = []
    seen: set[str] = set()
    for raw_files, forced_role in packaged_groups:
        if not isinstance(raw_files, list):
            raise PromotionNeedsAgentRefactor(
                "refactor report paths packaged file fields must be lists"
            )
        for raw in raw_files:
            if not isinstance(raw, dict):
                raise PromotionNeedsAgentRefactor("packaged file entries must be objects")
            artifact_path = _normalize_report_packaged_artifact_path(
                raw.get("artifactPath") or raw.get("path"),
                forced_role=forced_role,
            )
            if artifact_path in seen:
                raise PromotionNeedsAgentRefactor(
                    f"duplicate packaged artifact path: {artifact_path}"
                )
            seen.add(artifact_path)
            role = _packaged_file_role(artifact_path)
            _validate_packaged_artifact_path(
                artifact_path,
                role=role,
                is_denylisted_source=is_denylisted_source,
            )
            source_path = _resolve_report_source_path(raw, branch=branch, artifact_path=artifact_path)
            if not source_path.is_file():
                raise PromotionNeedsAgentRefactor(
                    f"packaged source file is missing for {artifact_path}: {source_path}"
                )
            packaged.append(
                PromotionPackagedFile(
                    artifact_path=artifact_path,
                    source_path=source_path,
                    purpose=_clean(raw.get("purpose")),
                    role=role,
                )
            )
    return packaged


def _normalize_report_packaged_artifact_path(value: Any, *, forced_role: str | None) -> str:
    text = str(value or "").replace("\\", "/").strip()
    if forced_role == "initial_state" and text and not text.startswith("runtime/initial-state/"):
        text = f"runtime/initial-state/{text.removeprefix('state/')}"
    path = Path(text)
    if not text or path.is_absolute() or ".." in path.parts:
        raise PromotionNeedsAgentRefactor(f"invalid packaged artifact path: {text!r}")
    return path.as_posix()


def _packaged_file_role(artifact_path: str) -> str:
    if artifact_path.startswith("runtime/initial-state/"):
        return "initial_state"
    if artifact_path.startswith("strategy/"):
        return "base_asset"
    raise PromotionNeedsAgentRefactor(
        "packaged files must use strategy/** or runtime/initial-state/** artifact paths: "
        f"{artifact_path}"
    )


def _validate_packaged_artifact_path(
    artifact_path: str,
    *,
    role: str,
    is_denylisted_source: Callable[[Path], bool],
) -> None:
    if role == "base_asset":
        relative = Path(artifact_path.removeprefix("strategy/"))
        if is_denylisted_source(relative):
            raise PromotionNeedsAgentRefactor(
                f"packaged artifact path is denylisted: {artifact_path}"
            )
        return
    if role == "initial_state":
        relative = Path(artifact_path.removeprefix("runtime/initial-state/"))
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise PromotionNeedsAgentRefactor(
                f"invalid runtime initial state artifact path: {artifact_path}"
            )
        if is_denylisted_source(relative):
            raise PromotionNeedsAgentRefactor(
                f"runtime initial state artifact path is denylisted: {artifact_path}"
            )


def _resolve_report_source_path(
    raw: dict[str, Any],
    *,
    branch: Path,
    artifact_path: str,
) -> Path:
    source_text = _clean(raw.get("sourcePath") or raw.get("source"))
    if source_text:
        source = Path(source_text).expanduser()
        return source if source.is_absolute() else branch / source
    if artifact_path.startswith("strategy/"):
        return branch / artifact_path.removeprefix("strategy/")
    if artifact_path.startswith("runtime/initial-state/"):
        return branch / artifact_path.removeprefix("runtime/initial-state/")
    return branch / artifact_path


def _validate_agent_paper_signal_contract(
    report: dict[str, Any],
    source: str,
    *,
    require_paper_signal: bool,
) -> None:
    paper_signal = report.get("paperSignal")
    if not isinstance(paper_signal, dict):
        if require_paper_signal:
            raise PromotionNeedsAgentRefactor(
                "hosted paper rewrite report must include paperSignal"
            )
        return
    implemented = paper_signal.get("implemented")
    incremental_ready = paper_signal.get("incrementalReady")
    if require_paper_signal and implemented is not True:
        raise PromotionNeedsAgentRefactor(
            "hosted paper rewrite must set paperSignal.implemented=true"
        )
    if require_paper_signal and incremental_ready is not True:
        raise PromotionNeedsAgentRefactor(
            "hosted paper rewrite must set paperSignal.incrementalReady=true"
        )
    if implemented is True and not _source_overrides_get_paper_signal(source):
        raise PromotionNeedsAgentRefactor(
            "paperSignal.implemented=true but promoted source does not define get_paper_signal"
        )


def _validate_promoted_source_static(source_path: Path) -> None:
    source = source_path.read_text(encoding="utf-8")
    local_literals = [
        literal for literal in _source_string_literals(source) if _is_local_absolute_path(literal)
    ]
    if local_literals:
        sample = ", ".join(sorted(local_literals)[:3])
        raise PromotionNeedsAgentRefactor(
            f"promoted source still contains developer-local absolute path(s): {sample}"
        )


def _state_dependency_signals(
    branch: Path,
    *,
    strategy_source_path: Path,
    is_denylisted_source: Callable[[Path], bool],
) -> list[dict[str, str]]:
    signals: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    runtime_state_dir = branch / LOCAL_RUNTIME_STATE_DIR
    if runtime_state_dir.is_dir():
        for path in sorted(runtime_state_dir.rglob("*")):
            if path.is_file():
                runtime_relative = path.relative_to(runtime_state_dir).as_posix()
                _append_self_check_signal(
                    signals,
                    seen,
                    kind="runtime_state_file",
                    value=(LOCAL_RUNTIME_STATE_DIR / runtime_relative).as_posix(),
                    reason="file already exists under .abel-runtime/state",
                )

    for path in sorted(branch.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(branch)
        if _skip_state_self_check_file(relative):
            continue
        if is_denylisted_source(relative):
            continue
        lower_parts = {part.lower() for part in relative.parts}
        suffix = relative.suffix.lower()
        if suffix in STATE_SELF_CHECK_FILE_SUFFIXES:
            _append_self_check_signal(
                signals,
                seen,
                kind="state_like_file",
                value=relative.as_posix(),
                reason=f"state-like file suffix {suffix}",
            )
        elif (
            lower_parts & STATE_SELF_CHECK_DIRECTORY_PARTS
            and suffix in STATE_SELF_CHECK_DIRECTORY_SUFFIXES
        ):
            _append_self_check_signal(
                signals,
                seen,
                kind="state_like_branch_file",
                value=relative.as_posix(),
                reason="file is under a model/checkpoint/cache/state directory",
            )

    if strategy_source_path.is_file():
        source = strategy_source_path.read_text(encoding="utf-8")
        for literal in _source_string_literals(source):
            signal = _source_state_reference_signal(literal)
            if signal is None:
                continue
            _append_self_check_signal(
                signals,
                seen,
                kind="source_state_reference",
                value=literal,
                reason=signal,
            )
    return signals


def _skip_state_self_check_file(relative: Path) -> bool:
    if any(
        part
        in {
            ".git",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            "__pycache__",
            "inputs",
            "outputs",
            "promotions",
            "rounds",
        }
        for part in relative.parts
    ):
        return True
    return relative.name in {
        "branch.yaml",
        "branch_state.json",
        "engine.py",
        "results.tsv",
        "state_intent.json",
    }


def _append_self_check_signal(
    signals: list[dict[str, str]],
    seen: set[tuple[str, str]],
    *,
    kind: str,
    value: str,
    reason: str,
) -> None:
    key = (kind, value)
    if key in seen:
        return
    seen.add(key)
    payload = {"kind": kind, "value": value, "reason": reason}
    signals.append(payload)


def _source_import_facts(tree: ast.AST | None) -> list[dict[str, str]]:
    if tree is None:
        return []
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = _top_level_module(alias.name)
                if module:
                    modules.add(module)
        elif isinstance(node, ast.ImportFrom):
            module = _top_level_module(node.module or "")
            if module:
                modules.add(module)
    return [
        {"module": module, "classification": _import_classification(module)}
        for module in sorted(modules)
    ]


def _top_level_module(value: str) -> str:
    return str(value or "").split(".", 1)[0].strip()


def _import_classification(module: str) -> str:
    if module == "__future__" or module in sys.stdlib_module_names:
        return "stdlib"
    if module in PROMOTION_ALLOWED_RUNTIME_IMPORTS:
        return "allowed_runtime"
    return "nonstandard"


def _source_file_access_facts(tree: ast.AST | None) -> list[dict[str, Any]]:
    if tree is None:
        return []
    constants = _string_constants(tree)
    facts: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node.func)
        access = _file_access_kind(call_name)
        if access is None:
            continue
        path_value = ""
        if node.args:
            path_value = _string_expr_value(node.args[0], constants)
        facts.append(
            {
                "function": call_name,
                "access": access,
                "path": path_value,
                "line": getattr(node, "lineno", 0),
            }
        )
    return facts


def _file_access_kind(call_name: str) -> str | None:
    if (
        call_name in PROMOTION_FILE_READ_FUNCTIONS
        or call_name in {"read_text", "read_bytes"}
        or call_name.endswith(".read_text")
        or call_name.endswith(".read_bytes")
    ):
        return "read"
    if (
        call_name in PROMOTION_FILE_WRITE_FUNCTIONS
        or call_name in {"write_text", "write_bytes"}
        or call_name.endswith(".write_text")
        or call_name.endswith(".write_bytes")
    ):
        return "write"
    return None


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _string_expr_value(node: ast.AST, constants: dict[str, str]) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id, "")
    return ""


def _display_source_path(branch: Path, source_path: Path) -> str:
    try:
        return source_path.relative_to(branch).as_posix()
    except ValueError:
        if source_path.name == "engine.py" and source_path.parent.name == "promoted":
            return "promoted/engine.py"
        return source_path.name


def _is_local_absolute_path(value: str) -> bool:
    text = str(value or "").replace("\\", "/").strip()
    if not text:
        return False
    if any(text.startswith(prefix) for prefix in ("http://", "https://", "s3://", "efs://")):
        return False
    return Path(text).is_absolute()


def _source_overrides_get_paper_signal(source: str) -> bool:
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


def _source_string_literals(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    literals: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value.strip()
            if text:
                literals.append(text)
    return literals


def _source_state_reference_signal(value: str) -> str | None:
    text = value.replace("\\", "/").strip()
    if not text:
        return None
    path = Path(text)
    parts = {part.lower() for part in path.parts}
    suffix = path.suffix.lower()
    if suffix in STATE_SELF_CHECK_FILE_SUFFIXES:
        return f"source string references state-like file suffix {suffix}"
    if parts & STATE_SELF_CHECK_SOURCE_PATH_PARTS:
        return "source string references model/checkpoint/registry/scaler path"
    lowered = text.lower()
    if any(keyword in lowered for keyword in STATE_SELF_CHECK_SOURCE_KEYWORDS) and (
        "/" in text or "." in path.name
    ):
        return "source string looks like a durable state path"
    return None


def _string_constants(tree: ast.AST) -> dict[str, str]:
    values: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                values[target.id] = node.value.value
    return values


def _default_behavior_equivalence(
    *,
    mode: str,
    replacements: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "status": "passed",
        "method": "agent_hosted_paper_rewrite_scope"
        if mode == PROMOTION_MODE_AGENT_REFACTOR
        else "source_hash_identity",
        "replacements": replacements,
    }


def _simple_patch_summary(
    source_path: Path,
    replacements: list[dict[str, str]],
    *,
    scope: str = PROMOTION_HOSTED_REWRITE_SCOPE,
) -> str:
    lines = [
        f"source: {source_path}",
        f"scope: {scope}",
        "replacements:",
    ]
    for replacement in replacements:
        reason = replacement.get("reason")
        suffix = f" ({reason})" if reason else ""
        lines.append(f"- {replacement['path']} -> {replacement['replacement']}{suffix}")
    return "\n".join(lines) + "\n"


def _load_agent_refactor_report(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{PROMOTION_REFACTOR_REPORT_FILENAME} must be an object")
    if payload.get("schema") != PROMOTION_AGENT_REPORT_SCHEMA:
        raise RuntimeError(
            f"{PROMOTION_REFACTOR_REPORT_FILENAME} has unsupported schema"
        )
    if payload.get("kind") != PROMOTION_HOSTED_REWRITE_SCOPE:
        raise RuntimeError(
            f"{PROMOTION_REFACTOR_REPORT_FILENAME} kind must be "
            f"{PROMOTION_HOSTED_REWRITE_SCOPE}"
        )
    return payload


def _report_replacements(report: dict[str, Any]) -> list[dict[str, str]]:
    raw_replacements = report.get("replacements")
    if not isinstance(raw_replacements, list):
        return []
    replacements: list[dict[str, str]] = []
    for item in raw_replacements:
        if not isinstance(item, dict):
            continue
        path = _clean(item.get("path"))
        replacement = _clean(item.get("replacement"))
        if path and replacement:
            payload = {"path": path, "replacement": replacement}
            reason = _clean(item.get("reason"))
            if reason:
                payload["reason"] = reason
            replacements.append(payload)
    return replacements


def _clean(value: Any) -> str:
    return str(value or "").strip()
