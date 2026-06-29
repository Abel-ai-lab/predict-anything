from __future__ import annotations

from pathlib import Path

from abel_invest import __version__
from abel_invest import bootstrap_runtime_doctor


def test_runtime_doctor_reports_contract_handshake(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        bootstrap_runtime_doctor.doctor,
        "run_doctor",
        lambda _workspace: {"status": "ready"},
    )
    monkeypatch.setattr(
        bootstrap_runtime_doctor.doctor,
        "doctor_exit_code",
        lambda _result: 0,
    )

    payload = bootstrap_runtime_doctor.run_bootstrap_runtime_doctor(
        workspace=tmp_path,
        expected_version=__version__,
        expected_contract_id=bootstrap_runtime_doctor.BOOTSTRAP_CONTRACT_ID,
    )

    assert payload["schema"] == "abel-invest.bootstrap-runtime-doctor/v1"
    assert payload["exit_code"] == 0
    assert payload["bootstrap_contract"]["skill_version"] == __version__
    assert payload["bootstrap_contract"]["mismatches"] == []


def test_runtime_doctor_rejects_contract_mismatch(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        bootstrap_runtime_doctor.doctor,
        "run_doctor",
        lambda _workspace: {"status": "ready"},
    )
    monkeypatch.setattr(
        bootstrap_runtime_doctor.doctor,
        "doctor_exit_code",
        lambda _result: 0,
    )

    payload = bootstrap_runtime_doctor.run_bootstrap_runtime_doctor(
        workspace=tmp_path,
        expected_version="0.0.0",
        expected_contract_id=bootstrap_runtime_doctor.BOOTSTRAP_CONTRACT_ID,
    )

    assert payload["exit_code"] == 2
    assert payload["bootstrap_contract"]["mismatches"] == ["skill_version"]
