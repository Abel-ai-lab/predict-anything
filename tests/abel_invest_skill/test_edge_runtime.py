from __future__ import annotations

from pathlib import Path

from abel_invest.workspace_core import edge_runtime


def _point_collection_auth(monkeypatch, tmp_path: Path) -> Path:
    auth_file = tmp_path / "skills" / "abel-auth" / ".env.skill"
    auth_file.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        edge_runtime,
        "__file__",
        str(tmp_path / "skills" / "abel-invest" / "abel_invest" / "workspace_core" / "edge_runtime.py"),
    )
    return auth_file


def test_build_workspace_runtime_env_prefers_collection_auth_file(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    (workspace_root / ".env").write_text("", encoding="utf-8")

    auth_file = _point_collection_auth(monkeypatch, tmp_path)
    auth_file.write_text("ABEL_API_KEY=abel-from-auth-skill\n", encoding="utf-8")

    monkeypatch.setattr(edge_runtime, "load_workspace_manifest", lambda _root: {"paths": {}})

    env = edge_runtime.build_workspace_runtime_env(workspace_root, base={})

    assert env["ABEL_AUTH_ENV_FILE"] == str(auth_file.resolve())
    assert env["ABEL_EDGE_CACHE_ROOT"] == str(
        (workspace_root / "cache" / "market_data").resolve()
    )


def test_build_workspace_runtime_env_prefers_workspace_auth_when_present(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace_env = workspace_root / ".env"
    workspace_env.write_text("ABEL_API_KEY=abel-from-workspace\n", encoding="utf-8")

    monkeypatch.setattr(edge_runtime, "load_workspace_manifest", lambda _root: {"paths": {}})

    env = edge_runtime.build_workspace_runtime_env(workspace_root, base={})

    assert env["ABEL_AUTH_ENV_FILE"] == str(workspace_env.resolve())
    assert env["ABEL_EDGE_CACHE_ROOT"] == str(
        (workspace_root / "cache" / "market_data").resolve()
    )


def test_effective_env_uses_shared_profile_without_copying_shared_token(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    (workspace_root / ".env").write_text("", encoding="utf-8")

    auth_file = _point_collection_auth(monkeypatch, tmp_path)
    auth_file.write_text(
        "\n".join(
            [
                "ABEL_PROFILE=sit",
                "ABEL_CAP_BASE_URL=https://cap-sit.abel.ai/api",
                "ABEL_AUTH_BASE_URL=https://api-sit.abel.ai/router/",
                "ABEL_ROUTER_BASE_URL=https://api-sit.abel.ai/router/",
                "ABEL_NARRATIVE_CAP_BASE_URL=https://cap-sit.abel.ai/narrative",
                "ABEL_API_KEY=abel-from-auth-skill",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(edge_runtime, "load_workspace_manifest", lambda _root: {"paths": {}})

    env = edge_runtime.build_workspace_runtime_env(workspace_root, base={})
    description = edge_runtime.describe_effective_abel_env(workspace_root, base={})

    assert env["ABEL_AUTH_ENV_FILE"] == str(auth_file.resolve())
    assert env["ABEL_PROFILE"] == "sit"
    assert env["ABEL_CAP_BASE_URL"] == "https://cap-sit.abel.ai/api"
    assert env["ABEL_ROUTER_BASE_URL"] == "https://api-sit.abel.ai/router/"
    assert "ABEL_API_KEY" not in env
    assert description["auth"] == {
        "ok": True,
        "source": "shared_auth_file",
        "path": str(auth_file.resolve()),
    }
    assert description["profileSource"] == "shared_auth_file"
    assert description["effectiveCapBaseUrl"] == "https://cap-sit.abel.ai/api"


def test_workspace_env_overrides_shared_profile(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    (workspace_root / ".env").write_text(
        "ABEL_CAP_BASE_URL=https://cap-workspace.example/api\n",
        encoding="utf-8",
    )

    auth_file = _point_collection_auth(monkeypatch, tmp_path)
    auth_file.write_text(
        "\n".join(
            [
                "ABEL_PROFILE=sit",
                "ABEL_CAP_BASE_URL=https://cap-sit.abel.ai/api",
                "ABEL_API_KEY=abel-from-auth-skill",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(edge_runtime, "load_workspace_manifest", lambda _root: {"paths": {}})

    env = edge_runtime.build_workspace_runtime_env(workspace_root, base={})
    description = edge_runtime.describe_effective_abel_env(workspace_root, base={})

    assert env["ABEL_PROFILE"] == "sit"
    assert env["ABEL_CAP_BASE_URL"] == "https://cap-workspace.example/api"
    assert description["workspaceOverrideKeys"] == ["ABEL_CAP_BASE_URL"]
    assert description["envConflictKeys"] == ["ABEL_CAP_BASE_URL"]
    assert description["keySources"]["ABEL_CAP_BASE_URL"] == "workspace_env"


def test_process_env_overrides_workspace_and_shared_profile(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    (workspace_root / ".env").write_text(
        "ABEL_CAP_BASE_URL=https://cap-workspace.example/api\n",
        encoding="utf-8",
    )

    auth_file = _point_collection_auth(monkeypatch, tmp_path)
    auth_file.write_text(
        "ABEL_CAP_BASE_URL=https://cap-sit.abel.ai/api\nABEL_API_KEY=abel-from-auth-skill\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(edge_runtime, "load_workspace_manifest", lambda _root: {"paths": {}})

    env = edge_runtime.build_workspace_runtime_env(
        workspace_root,
        base={"ABEL_CAP_BASE_URL": "https://cap-process.example/api"},
    )

    assert env["ABEL_CAP_BASE_URL"] == "https://cap-process.example/api"
    assert env["ABEL_AUTH_ENV_FILE"] == str(auth_file.resolve())


def test_workspace_auth_env_file_selects_custom_shared_profile(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    custom_auth = tmp_path / "custom-auth.env"
    custom_auth.write_text(
        "ABEL_CAP_BASE_URL=https://cap-custom.example/api\nABEL_API_KEY=custom-token\n",
        encoding="utf-8",
    )
    (workspace_root / ".env").write_text(
        f"ABEL_AUTH_ENV_FILE={custom_auth}\n",
        encoding="utf-8",
    )
    _point_collection_auth(monkeypatch, tmp_path).write_text(
        "ABEL_CAP_BASE_URL=https://cap-sit.abel.ai/api\nABEL_API_KEY=shared-token\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(edge_runtime, "load_workspace_manifest", lambda _root: {"paths": {}})

    env = edge_runtime.build_workspace_runtime_env(workspace_root, base={})
    description = edge_runtime.describe_effective_abel_env(workspace_root, base={})

    assert env["ABEL_AUTH_ENV_FILE"] == str(custom_auth.resolve())
    assert env["ABEL_CAP_BASE_URL"] == "https://cap-custom.example/api"
    assert description["auth"]["path"] == str(custom_auth.resolve())


def test_probe_abel_auth_prefers_collection_auth_file_without_runtime_probe(
    monkeypatch,
    tmp_path: Path,
) -> None:
    for key in (
        "ABEL_AUTH_ENV_FILE",
        "ABEL_API_KEY",
        "CAP_API_KEY",
        "ABEL_CAP_BASE_URL",
        "ABEL_AUTH_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    (workspace_root / ".env").write_text("", encoding="utf-8")

    auth_file = _point_collection_auth(monkeypatch, tmp_path)
    auth_file.write_text("ABEL_API_KEY=abel-from-auth-skill\n", encoding="utf-8")

    monkeypatch.setattr(edge_runtime, "load_workspace_manifest", lambda _root: {"paths": {}})

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("runtime probe should not run when shared auth is already resolvable")

    monkeypatch.setattr(edge_runtime, "run_python_json", fail_if_called)

    result = edge_runtime.probe_abel_auth("python", workspace_root)

    assert result == {
        "ok": True,
        "source": "shared_auth_file",
        "path": str(auth_file.resolve()),
    }
