#!/usr/bin/env python3
"""Stdlib-only first-run bootstrap for an Abel strategy discovery workspace."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from shutil import which


MANIFEST_NAME = "alpha.workspace.yaml"
DEFAULT_WORKSPACE_NAME = "abel-invest-workspace"
WORKSPACE_AGENTS_GUIDE_SCHEMA = "abel-invest.workspace-agents/v1"
WORKSPACE_README_SCHEMA = "abel-invest.workspace-readme/v1"
WORKSPACE_ENV_EXAMPLE_SCHEMA = "abel-invest.workspace-env-example/v1"
WORKSPACE_GITIGNORE_SCHEMA = "abel-invest.workspace-gitignore/v1"
BOOTSTRAP_CONTRACT_ID = "abel-invest.bootstrap-reconcile/v1"


def main() -> int:
    args = build_parser().parse_args()
    skill_root = resolve_skill_root(args.alpha_source)
    target_root = Path(args.path).expanduser().resolve()
    root = ensure_workspace_scaffold(target_root, args.name, skill_root=skill_root)
    python_path = ensure_workspace_runtime(
        root=root,
        skill_root=skill_root,
        base_python=args.base_python,
        runtime_python=args.runtime_python,
        editable=not args.no_editable,
    )
    refresh_workspace_guidance(python_path=python_path, root=root, name=args.name)
    print(f"Running bootstrap runtime doctor with {python_path}")
    doctor_payload = run_bootstrap_runtime_doctor(
        python_path=python_path,
        root=root,
        skill_root=skill_root,
        verify_source_root=not args.no_editable,
    )
    doctor_result = doctor_payload.get("doctor", {})
    print(render_runtime_doctor_report(doctor_result))
    cli_path = runtime_cli_path(python_path)
    print("")
    print("From here:")
    if int(doctor_payload.get("exit_code", 1)) == 0:
        print(f"  cd {root}")
        print(f"  {default_activate_command()}")
        print(f"  {cli_path} init-session --ticker <TICKER> --exp-id <session-id>")
    else:
        print(f"  cd {root}")
        print("  resolve the blocker above, then rerun this active skill bootstrap command")
    return int(doctor_payload.get("exit_code", 1))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap an Abel strategy discovery workspace when only the skill "
            "files and python3 are available."
        )
    )
    parser.add_argument("--path", required=True, help="Workspace directory path")
    parser.add_argument(
        "--name",
        default=DEFAULT_WORKSPACE_NAME,
        help=f"Workspace name recorded in the manifest (defaults to {DEFAULT_WORKSPACE_NAME})",
    )
    parser.add_argument(
        "--python",
        dest="base_python",
        default=None,
        help="Base interpreter used to create the workspace venv",
    )
    parser.add_argument(
        "--runtime-python",
        default=None,
        help="Use an existing interpreter instead of creating the workspace venv",
    )
    parser.add_argument(
        "--alpha-source",
        default=None,
        help="Optional Abel Invest source tree override",
    )
    parser.add_argument(
        "--no-editable",
        action="store_true",
        help="Install Abel Invest in regular mode instead of editable mode",
    )
    return parser


def resolve_skill_root(explicit: str | None) -> Path:
    if explicit:
        root = Path(explicit).expanduser().resolve()
    else:
        root = Path(__file__).resolve().parents[1]
    if not (root / "pyproject.toml").exists():
        raise SystemExit(f"Abel Invest source tree is missing pyproject.toml: {root}")
    return root


def ensure_workspace_scaffold(target_root: Path, name: str, *, skill_root: Path) -> Path:
    target_state, related_root = inspect_workspace_bootstrap_target(target_root)
    if target_state == "nested_workspace" and related_root is not None:
        raise SystemExit(
            "Refusing to bootstrap a nested Abel strategy discovery workspace at "
            f"{target_root}\nExisting workspace root for this area: {related_root}"
        )
    if target_state == "launch_root_child_workspace" and related_root is not None:
        raise SystemExit(
            f"Workspace already exists at the default child path: {related_root}\n"
            "Reuse it instead of bootstrapping another workspace for the same area."
        )

    if target_root.exists():
        if not target_root.is_dir():
            raise SystemExit(f"Path exists and is not a directory: {target_root}")
        if (target_root / MANIFEST_NAME).exists():
            print(f"Reusing Abel strategy discovery workspace at {target_root}")
            return target_root
        if any(target_root.iterdir()):
            raise SystemExit(
                "Cannot bootstrap into an existing non-workspace directory: "
                f"{target_root}"
            )
    else:
        target_root.mkdir(parents=True)

    for rel in ("docs", "research", "cache/market_data", "logs"):
        (target_root / rel).mkdir(parents=True, exist_ok=True)
    write_text(target_root / MANIFEST_NAME, render_manifest(name))
    write_text(target_root / ".gitignore", render_gitignore())
    write_text(target_root / ".env.example", render_env_example())
    write_text(target_root / ".env", "")
    write_text(target_root / "README.md", render_readme(name))
    write_text(target_root / "AGENTS.md", render_agents(skill_root))
    print(f"Created Abel strategy discovery workspace at {target_root}")
    return target_root


def ensure_workspace_runtime(
    *,
    root: Path,
    skill_root: Path,
    base_python: str | None,
    runtime_python: str | None,
    editable: bool,
) -> Path:
    if runtime_python:
        python_path = Path(runtime_python).expanduser().resolve()
        if not python_path.exists():
            raise SystemExit(f"Existing runtime python does not exist: {python_path}")
        update_manifest_value(root / MANIFEST_NAME, "  python:", f"  python: {python_path}")
    else:
        python_path = root / default_python_path()
        if not python_path.exists():
            create_workspace_venv(
                interpreter=base_python or sys.executable,
                venv_path=root / ".venv",
                cwd=root,
            )

    run_command([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], cwd=root)

    install_command = [
        str(python_path),
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--upgrade-strategy",
        "eager",
    ]
    if editable:
        install_command.extend(["-e", str(skill_root)])
    else:
        install_command.append(str(skill_root))
    run_command(install_command, cwd=root)
    return python_path


def create_workspace_venv(*, interpreter: str, venv_path: Path, cwd: Path) -> None:
    try:
        run_command([interpreter, "-m", "venv", str(venv_path)], cwd=cwd)
        return
    except SystemExit as exc:
        first_error = str(exc)
    uv_bin = which("uv")
    if not uv_bin:
        raise SystemExit(first_error)
    command = [uv_bin, "venv", "--seed", "--python", str(interpreter), str(venv_path)]
    try:
        run_command(command, cwd=cwd)
    except SystemExit as exc:
        raise SystemExit(f"{first_error}\n\nuv fallback also failed:\n{exc}") from exc


def inspect_workspace_bootstrap_target(path: Path) -> tuple[str, Path | None]:
    if (path / MANIFEST_NAME).exists():
        return "existing_workspace_root", path
    containing_root = find_containing_workspace_root(path)
    if containing_root is not None:
        return "nested_workspace", containing_root
    child = path / DEFAULT_WORKSPACE_NAME
    if child != path and (child / MANIFEST_NAME).exists():
        return "launch_root_child_workspace", child
    return "clear", None


def find_containing_workspace_root(path: Path) -> Path | None:
    search_from = path if path.exists() else path.parent
    for candidate in (search_from, *search_from.parents):
        if (candidate / MANIFEST_NAME).exists():
            return candidate
    return None


def run_command(command: list[str], *, cwd: Path) -> None:
    try:
        subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        message = f"Command failed with exit code {exc.returncode}: {' '.join(command)}"
        if details:
            message = f"{message}\n{details}"
        raise SystemExit(message) from exc


def update_manifest_value(path: Path, prefix: str, replacement: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    updated = [replacement if line.startswith(prefix) else line for line in lines]
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def refresh_workspace_guidance(*, python_path: Path, root: Path, name: str) -> None:
    code = (
        "from pathlib import Path\n"
        "from abel_invest.workspace_core.workspace import refresh_generated_workspace_files\n"
        "from abel_invest.workspace_core.workspace import load_workspace_manifest\n"
        f"root = Path({str(root)!r})\n"
        "refresh_generated_workspace_files(root, load_workspace_manifest(root))\n"
    )
    run_command([str(python_path), "-c", code], cwd=root)


def run_bootstrap_runtime_doctor(
    *,
    python_path: Path,
    root: Path,
    skill_root: Path,
    verify_source_root: bool,
) -> dict:
    command = [
        str(python_path),
        "-m",
        "abel_invest.bootstrap_runtime_doctor",
        "--workspace",
        str(root),
        "--expected-version",
        local_project_version(skill_root),
        "--expected-contract-id",
        BOOTSTRAP_CONTRACT_ID,
        "--json",
    ]
    if verify_source_root:
        command.extend(["--expected-source-root", str(skill_root)])
    completed = subprocess.run(command, cwd=root, capture_output=True, text=True)
    payload = parse_json_stdout(completed.stdout, command)
    if completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)
    if completed.returncode not in {0, 1, 2}:
        raise SystemExit(
            f"Bootstrap runtime doctor failed with exit code {completed.returncode}: {' '.join(command)}"
        )
    contract = payload.get("bootstrap_contract") if isinstance(payload, dict) else None
    mismatches = contract.get("mismatches") if isinstance(contract, dict) else None
    if mismatches:
        raise SystemExit(
            "Bootstrap runtime doctor contract mismatch: "
            + ", ".join(str(item) for item in mismatches)
        )
    return payload


def parse_json_stdout(stdout: str, command: list[str]) -> dict:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            "Bootstrap runtime doctor did not emit valid JSON: "
            + " ".join(command)
            + f"\n{stdout.strip()}"
        ) from exc


def render_runtime_doctor_report(result: object) -> str:
    if not isinstance(result, dict):
        return "Status: unknown\nSummary: runtime doctor returned an invalid payload"
    lines = [
        f"Status: {result.get('status', 'unknown')}",
        f"Summary: {result.get('summary', '')}",
    ]
    for key in ("workspace_root", "python_path", "cli_path", "command_prefix"):
        value = result.get(key)
        if value:
            label = key.replace("_", " ").title()
            lines.append(f"{label}: {value}")
    auth = result.get("auth")
    if isinstance(auth, dict):
        source = auth.get("source", "unknown")
        path = auth.get("path")
        lines.append(f"Auth source: {source}" + (f" ({path})" if path else ""))
    effective_env = result.get("effective_env")
    if isinstance(effective_env, dict):
        profile = effective_env.get("effectiveProfile") or "<unset>"
        profile_source = effective_env.get("profileSource") or "unknown"
        cap_url = effective_env.get("effectiveCapBaseUrl")
        lines.append(f"Effective profile: {profile} ({profile_source})")
        if cap_url:
            lines.append(f"Effective CAP base URL: {cap_url}")
        overrides = effective_env.get("workspaceOverrideKeys")
        if isinstance(overrides, list) and overrides:
            lines.append(
                "Workspace env overrides: "
                + ", ".join(str(item) for item in overrides)
            )
        conflicts = effective_env.get("envConflictKeys")
        if isinstance(conflicts, list) and conflicts:
            lines.append(
                "Workspace/shared env conflicts: "
                + ", ".join(str(item) for item in conflicts)
            )
    next_step = result.get("next_step")
    if next_step:
        lines.append(f"Next step: {next_step}")
    return "\n".join(lines)


def render_manifest(name: str) -> str:
    return f"""version: 1
workspace:
  name: {name}
  kind: abel-invest
paths:
  research_root: research
  docs_root: docs
  cache_root: cache/market_data
  logs_root: logs
  venv: .venv
runtime:
  python: {default_python_path()}
  auth_strategy: reuse_abel_auth_first
defaults:
  backtest_start: '2020-01-01'
  discovery_limit: 10
"""


def render_readme(name: str) -> str:
    return f"""<!-- {WORKSPACE_README_SCHEMA} version={local_project_version(Path(__file__).resolve().parents[1])} -->
# {name}

This is an Abel Invest alpha-search workspace.

From this workspace root, use `./.venv/bin/abel-invest` as the command prefix,
or activate `.venv` first and then use `abel-invest`.

Run the active skill bootstrap shim before creating or continuing sessions. The
shim owns workspace reconciliation; the workspace CLI owns exploration commands
after bootstrap reports ready.
"""


def render_agents(skill_root: Path) -> str:
    version = local_project_version(skill_root)
    return f"""<!-- {WORKSPACE_AGENTS_GUIDE_SCHEMA} version={version} -->
# AGENTS.md - Abel strategy discovery Workspace

Use this directory as the workspace root. If `alpha.workspace.yaml` is present,
do not create a child `abel-invest-workspace` here. Run the active Abel Invest
skill bootstrap shim before creating a new session.

Report to the user:
- workspace root and bootstrap readiness
- auth or runtime blockers
- current session and branch path
- the next action you will run or the one blocker that needs user input

Do not treat `branch.yaml` as evidence. Prepare and debug branch inputs before a
recorded round, and update `exploration_path.md` after every recorded round.
Graph context is a high-value alpha universe, not a required full-frontier first
strategy. Target-only is a baseline, seed, ablation, or competitor, not the
default substitute for live graph search.
"""


def render_gitignore() -> str:
    version = local_project_version(Path(__file__).resolve().parents[1])
    return f"""# {WORKSPACE_GITIGNORE_SCHEMA} version={version}
# Abel strategy discovery workspace
.venv/
.env
cache/
logs/
__pycache__/
*.pyc
"""


def render_env_example() -> str:
    version = local_project_version(Path(__file__).resolve().parents[1])
    return f"""# {WORKSPACE_ENV_EXAMPLE_SCHEMA} version={version}
# Abel Invest normally uses the shared abel-auth/.env.skill file.
# Leave workspace .env empty unless this workspace needs an explicit override.

# Optional: point this workspace at a custom shared auth/profile file.
# ABEL_AUTH_ENV_FILE=

# Optional: override only this workspace's Abel endpoints.
# ABEL_PROFILE=
# ABEL_CAP_BASE_URL=
# ABEL_AUTH_BASE_URL=
# ABEL_ROUTER_BASE_URL=
# ABEL_NARRATIVE_CAP_BASE_URL=
"""


def default_python_path() -> str:
    if os.name == "nt":
        return ".venv/Scripts/python.exe"
    return ".venv/bin/python"


def runtime_cli_path(python_path: Path) -> Path:
    cli_name = "abel-invest.exe" if os.name == "nt" else "abel-invest"
    return python_path.with_name(cli_name)


def default_activate_command() -> str:
    if os.name == "nt":
        return ".venv\\Scripts\\Activate.ps1"
    return "source .venv/bin/activate"


def local_project_version(skill_root: Path) -> str:
    pyproject = skill_root / "pyproject.toml"
    with pyproject.open("rb") as file:
        data = tomllib.load(file)
    return str(data["project"]["version"])


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
