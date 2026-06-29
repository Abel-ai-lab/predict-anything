from __future__ import annotations

from pathlib import Path

import pytest

from abel_invest import __version__ as ABEL_INVEST_VERSION
from abel_invest.narrative_core.session_lifecycle import resolve_workspace_arg_path
from abel_invest.workspace_core.workspace import (
    WORKSPACE_AGENTS_GUIDE_SCHEMA,
    build_default_manifest,
    refresh_generated_workspace_files,
    render_workspace_status,
    scaffold_workspace,
    workspace_generated_files_status,
)


def test_scaffold_workspace_writes_alpha_owned_boundary_guidance(tmp_path: Path) -> None:
    root = scaffold_workspace("trial-lab", target_root=tmp_path / "trial-lab")

    readme = (root / "README.md").read_text(encoding="utf-8")
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    readme_flat = readme.replace("\n", " ")
    agents_flat = agents.replace("\n", " ")

    assert agents.startswith(
        f"<!-- {WORKSPACE_AGENTS_GUIDE_SCHEMA} version={ABEL_INVEST_VERSION} -->"
    )
    assert workspace_generated_files_status(root)["files"]["AGENTS.md"]["status"] == "current"
    assert "This workspace is for alpha-managed strategy search." in readme
    assert "Do not run `abel-edge init` inside this workspace." in readme
    assert "Do not bootstrap `./abel-invest-workspace` inside it." in readme
    assert "evidence_ledger.json" in readme
    assert "frontier.md" in readme
    assert "exploration_path.md" in readme
    assert "research_journal.md" not in readme
    assert "best-strategy --session research/tsla/tsla-v1 --json" in readme
    assert "without exporting, uploading, or promoting artifacts" in readme_flat
    assert "visualize-session" in readme
    assert "creates an online session view" in readme
    assert "When exploration enters Completed" in readme
    assert "abel-auth" in readme
    assert "standalone `abel-edge init` project inside it" in agents
    assert "Do not create `./abel-invest-workspace` inside it." in agents
    assert "`best-strategy --session <session> --json`" in agents
    assert "does not export, upload, or promote artifacts" in agents_flat
    assert "visualize-session" in agents
    assert "online session view" in agents
    assert "visualization is not a required step after every round" in agents_flat
    assert "merely to compute the best strategy" in agents
    assert "`render`, `status`, and `check` are audit actions only" in agents
    assert "exploration_path.md" in agents
    assert "research_journal.md" not in agents
    assert "abel-auth" in agents
    assert "edit research/" not in _bash_blocks(readme)
    assert "read research/" not in _bash_blocks(readme)
    assert "edit research/" not in _bash_blocks(agents)
    assert "read research/" not in _bash_blocks(agents)
    assert "Report to the user" in agents
    generated = workspace_generated_files_status(root)
    assert generated["status"] == "current"
    assert generated["files"]["README.md"]["status"] == "current"
    assert generated["files"]["AGENTS.md"]["status"] == "current"
    assert generated["files"][".env.example"]["status"] == "current"
    assert generated["files"][".gitignore"]["status"] == "current"
    assert generated["files"][".env.example"]["foundVersion"] == ABEL_INVEST_VERSION
    assert generated["files"][".gitignore"]["foundVersion"] == ABEL_INVEST_VERSION


def test_refresh_generated_workspace_files_overwrites_readme_and_agents(tmp_path: Path) -> None:
    root = scaffold_workspace("trial-lab", target_root=tmp_path / "trial-lab")
    (root / "README.md").write_text("old readme with upload-dashboard-bundle\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("old agents with upload-dashboard-bundle\n", encoding="utf-8")

    before = workspace_generated_files_status(root)
    refreshed = refresh_generated_workspace_files(root)

    assert before["status"] == "stale"
    assert refreshed["status"] == "current"
    assert "upload-dashboard-bundle" not in (root / "README.md").read_text(encoding="utf-8")
    assert "upload-dashboard-bundle" not in (root / "AGENTS.md").read_text(encoding="utf-8")


def _bash_blocks(text: str) -> str:
    blocks: list[str] = []
    inside = False
    current: list[str] = []
    for line in text.splitlines():
        if line.strip() == "```bash":
            inside = True
            current = []
            continue
        if inside and line.strip() == "```":
            inside = False
            blocks.append("\n".join(current))
            continue
        if inside:
            current.append(line)
    return "\n".join(blocks)


def test_scaffold_workspace_rejects_nested_workspace_under_existing_root(tmp_path: Path) -> None:
    root = scaffold_workspace("trial-lab", target_root=tmp_path / "trial-lab")

    with pytest.raises(RuntimeError, match="Refusing to create a nested Abel strategy discovery workspace"):
        scaffold_workspace("nested", target_root=root / "abel-invest-workspace")


def test_render_workspace_status_reports_alpha_managed_mode(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()

    status = render_workspace_status(root, build_default_manifest("workspace"))

    assert "Workspace mode: alpha-managed strategy search" in status
    assert f"Research root: {root / 'research'}" in status


def test_workspace_arg_path_accepts_existing_launch_root_relative_session(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = scaffold_workspace(
        "abel-invest-workspace",
        target_root=tmp_path / "abel-invest-workspace",
    )
    session = workspace / "research" / "spy" / "resume-probe"
    session.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    resolved = resolve_workspace_arg_path(
        "abel-invest-workspace/research/spy/resume-probe"
    )

    assert resolved == session


def test_workspace_arg_path_keeps_workspace_relative_session_from_launch_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = scaffold_workspace(
        "abel-invest-workspace",
        target_root=tmp_path / "abel-invest-workspace",
    )
    monkeypatch.chdir(tmp_path)

    resolved = resolve_workspace_arg_path("research/spy/resume-probe")

    assert resolved == workspace / "research" / "spy" / "resume-probe"
