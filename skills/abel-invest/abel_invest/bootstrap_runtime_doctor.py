"""Bootstrap-owned runtime readiness checks.

This module is intentionally invoked by ``scripts/bootstrap_workspace.py`` after
the active skill has been installed into the workspace runtime. It is not a
public ``abel-invest`` CLI command.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from abel_invest import __version__
from abel_invest.workspace_core import doctor


BOOTSTRAP_CONTRACT_ID = "abel-invest.bootstrap-reconcile/v1"


def main() -> int:
    parser = argparse.ArgumentParser(description="Internal Abel Invest bootstrap runtime doctor")
    parser.add_argument("--workspace", required=True, help="Workspace root to inspect")
    parser.add_argument("--expected-source-root", default=None)
    parser.add_argument("--expected-version", default=None)
    parser.add_argument("--expected-contract-id", default=BOOTSTRAP_CONTRACT_ID)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    payload = run_bootstrap_runtime_doctor(
        workspace=Path(args.workspace).expanduser(),
        expected_source_root=args.expected_source_root,
        expected_version=args.expected_version,
        expected_contract_id=args.expected_contract_id,
    )
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(doctor.render_doctor_report(payload["doctor"]))
    return int(payload["exit_code"])


def run_bootstrap_runtime_doctor(
    *,
    workspace: Path,
    expected_source_root: str | None = None,
    expected_version: str | None = None,
    expected_contract_id: str | None = BOOTSTRAP_CONTRACT_ID,
) -> dict[str, object]:
    """Run the runtime doctor and attach the bootstrap contract handshake."""
    source_root = Path(__file__).resolve().parents[1]
    result = doctor.run_doctor(workspace)
    contract = {
        "contract_id": BOOTSTRAP_CONTRACT_ID,
        "skill_version": __version__,
        "source_root": str(source_root),
        "expected_contract_id": expected_contract_id or "",
        "expected_skill_version": expected_version or "",
        "expected_source_root": str(Path(expected_source_root).expanduser().resolve())
        if expected_source_root
        else "",
    }
    mismatches: list[str] = []
    if expected_contract_id and expected_contract_id != BOOTSTRAP_CONTRACT_ID:
        mismatches.append("contract_id")
    if expected_version and expected_version != __version__:
        mismatches.append("skill_version")
    if expected_source_root:
        expected = Path(expected_source_root).expanduser().resolve()
        if source_root.resolve() != expected:
            mismatches.append("source_root")
    contract["mismatches"] = mismatches
    return {
        "schema": "abel-invest.bootstrap-runtime-doctor/v1",
        "bootstrap_contract": contract,
        "doctor": result,
        "exit_code": 2 if mismatches else doctor.doctor_exit_code(result),
    }


if __name__ == "__main__":
    raise SystemExit(main())
