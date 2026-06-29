"""Shared runtime probes for the installed Abel-edge environment."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from abel_invest.workspace_core.workspace import load_workspace_manifest, resolve_workspace_paths


def common_python_root() -> Path:
    return Path(__file__).resolve().parents[3] / "abel-common" / "python"


def collection_auth_anchor() -> Path:
    return common_python_root().parent.parent / "abel-auth" / ".env.skill"


resolved_common_python_root = common_python_root()
if str(resolved_common_python_root) not in sys.path:
    sys.path.insert(0, str(resolved_common_python_root))

from abel_common.cap.auth import has_auth_token, read_env_file_values, resolve_auth_env_file


def _is_abel_runtime_env_key(key: str) -> bool:
    return key.startswith(("ABEL_", "CAP_"))


SECRET_ENV_KEYS = {"ABEL_API_KEY", "CAP_API_KEY"}
AUTH_ENV_FILE_KEY = "ABEL_AUTH_ENV_FILE"
DEFAULT_CAP_BASE_URL = "https://cap.abel.ai/api"
DEFAULT_AUTH_BASE_URL = "https://api.abel.ai/echo"


def _is_secret_env_key(key: str) -> bool:
    return key in SECRET_ENV_KEYS


def _non_secret_runtime_values(values: Mapping[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in values.items()
        if key
        and value
        and _is_abel_runtime_env_key(key)
        and not _is_secret_env_key(key)
        and key != AUTH_ENV_FILE_KEY
    }


def load_workspace_env_values(workspace_root: Path) -> dict[str, str]:
    """Load Abel runtime variables from the workspace-local ``.env`` file."""
    workspace_env = (workspace_root / ".env").resolve()
    return {
        key: value
        for key, value in read_env_file_values(workspace_env).items()
        if key and value and _is_abel_runtime_env_key(key)
    }


def resolve_auth_env_value(value: str, *, workspace_root: Path) -> Path:
    """Resolve an auth env file value to an absolute path."""
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (workspace_root / path).resolve()


def load_shared_auth_env_values(workspace_root: Path, base: Mapping[str, str] | None = None) -> tuple[Path | None, dict[str, str]]:
    """Load the active shared Abel auth/profile env file, if one is available."""
    base_values = os.environ if base is None else base
    explicit_auth_file = str(base_values.get(AUTH_ENV_FILE_KEY) or "").strip()
    if explicit_auth_file:
        auth_path = resolve_auth_env_value(explicit_auth_file, workspace_root=workspace_root)
        return auth_path, {
            key: value
            for key, value in read_env_file_values(auth_path).items()
            if key and value and _is_abel_runtime_env_key(key)
        }

    shared_auth = resolve_auth_env_file(collection_auth_anchor())
    if shared_auth is None and collection_auth_anchor().exists():
        shared_auth = collection_auth_anchor().resolve()
    if shared_auth is None:
        return None, {}
    return shared_auth, {
        key: value
        for key, value in read_env_file_values(shared_auth).items()
        if key and value and _is_abel_runtime_env_key(key)
    }


def apply_workspace_env(
    workspace_root: Path,
    *,
    environ: dict[str, str] | None = None,
    override: bool = False,
) -> dict[str, str]:
    """Apply only workspace ``.env`` Abel variables to an environment mapping.

    This is retained for compatibility with callers that explicitly need the
    raw workspace override layer. Normal Abel Invest runtime paths should use
    ``apply_effective_abel_env`` or ``build_workspace_runtime_env`` so shared
    ``abel-auth/.env.skill`` values participate in the effective environment.

    The default mirrors common dotenv behavior: workspace values fill missing
    variables while explicit process values keep precedence.
    """
    target = os.environ if environ is None else environ
    applied: dict[str, str] = {}
    for key, value in load_workspace_env_values(workspace_root).items():
        if override or not target.get(key):
            target[key] = value
            applied[key] = value
    return applied


def build_effective_abel_env(
    workspace_root: Path,
    *,
    base: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the effective Abel runtime env for this workspace.

    Precedence is explicit process/base env, then workspace-local overrides,
    then shared ``abel-auth/.env.skill`` profile defaults. Shared API keys are
    not expanded into the process env; they remain available through
    ``ABEL_AUTH_ENV_FILE``.
    """
    env = dict(os.environ if base is None else base)
    initial_keys = {
        key for key, value in env.items() if value and _is_abel_runtime_env_key(key)
    }
    workspace_values = load_workspace_env_values(workspace_root)

    shared_base = dict(env)
    if AUTH_ENV_FILE_KEY not in initial_keys and workspace_values.get(AUTH_ENV_FILE_KEY):
        shared_base[AUTH_ENV_FILE_KEY] = workspace_values[AUTH_ENV_FILE_KEY]
    shared_auth_path, shared_values = load_shared_auth_env_values(workspace_root, shared_base)
    for key, value in _non_secret_runtime_values(shared_values).items():
        if key not in initial_keys and not env.get(key):
            env[key] = value

    for key, value in workspace_values.items():
        if key in initial_keys:
            continue
        if key == AUTH_ENV_FILE_KEY:
            env[key] = str(resolve_auth_env_value(value, workspace_root=workspace_root))
        else:
            env[key] = value

    workspace_env = (workspace_root / ".env").resolve()
    if not env.get(AUTH_ENV_FILE_KEY):
        if has_auth_token(workspace_env):
            env[AUTH_ENV_FILE_KEY] = str(workspace_env)
        elif shared_auth_path is not None and has_auth_token(shared_auth_path):
            env[AUTH_ENV_FILE_KEY] = str(shared_auth_path)
        elif workspace_env.exists():
            env[AUTH_ENV_FILE_KEY] = str(workspace_env)
    return env


def apply_effective_abel_env(
    workspace_root: Path,
    *,
    environ: dict[str, str] | None = None,
) -> dict[str, str]:
    """Apply effective Abel runtime variables to the current or supplied env."""
    target = os.environ if environ is None else environ
    effective = build_effective_abel_env(workspace_root, base=target)
    applied: dict[str, str] = {}
    for key, value in effective.items():
        if not _is_abel_runtime_env_key(key):
            continue
        if target.get(key) == value:
            continue
        target[key] = value
        applied[key] = value
    return applied


def describe_effective_abel_env(
    workspace_root: Path,
    *,
    base: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Return non-secret metadata for the effective Abel runtime env."""
    base_values = os.environ if base is None else base
    process_keys = {
        key for key, value in base_values.items() if value and _is_abel_runtime_env_key(key)
    }
    workspace_values = load_workspace_env_values(workspace_root)
    shared_base = dict(base_values)
    if AUTH_ENV_FILE_KEY not in process_keys and workspace_values.get(AUTH_ENV_FILE_KEY):
        shared_base[AUTH_ENV_FILE_KEY] = workspace_values[AUTH_ENV_FILE_KEY]
    shared_auth_path, shared_values = load_shared_auth_env_values(workspace_root, shared_base)
    effective = build_effective_abel_env(workspace_root, base=base_values)
    workspace_env = (workspace_root / ".env").resolve()

    process_token = any((base_values.get(key) or "").strip() for key in SECRET_ENV_KEYS)
    workspace_token = any((workspace_values.get(key) or "").strip() for key in SECRET_ENV_KEYS)
    auth_path_value = str(effective.get(AUTH_ENV_FILE_KEY) or "").strip()
    auth_path = resolve_auth_env_value(auth_path_value, workspace_root=workspace_root) if auth_path_value else None

    if process_token:
        auth_source = "env_var"
        auth_path_text = None
        auth_ok = True
    elif workspace_token:
        auth_source = "workspace_env"
        auth_path_text = str(workspace_env)
        auth_ok = True
    elif auth_path is not None and has_auth_token(auth_path):
        auth_source = "workspace_env" if auth_path == workspace_env else "shared_auth_file"
        auth_path_text = str(auth_path)
        auth_ok = True
    else:
        auth_source = "missing"
        auth_path_text = str(auth_path) if auth_path is not None else None
        auth_ok = False

    key_sources: dict[str, str] = {}
    for key in process_keys:
        key_sources[key] = "env_var"
    for key in _non_secret_runtime_values(shared_values):
        key_sources.setdefault(key, "shared_auth_file")
    for key in workspace_values:
        if key not in process_keys:
            key_sources[key] = "workspace_env"

    conflict_keys = sorted(
        key
        for key, workspace_value in workspace_values.items()
        if key in shared_values and shared_values[key] != workspace_value
    )
    effective_profile = str(effective.get("ABEL_PROFILE") or "").strip()
    effective_cap = str(effective.get("ABEL_CAP_BASE_URL") or DEFAULT_CAP_BASE_URL).strip()
    effective_auth = str(effective.get("ABEL_AUTH_BASE_URL") or DEFAULT_AUTH_BASE_URL).strip()
    profile_source = key_sources.get("ABEL_PROFILE") or key_sources.get("ABEL_CAP_BASE_URL") or "default"

    return {
        "auth": {
            "ok": auth_ok,
            "source": auth_source,
            "path": auth_path_text,
        },
        "authEnvFile": str(auth_path) if auth_path is not None else None,
        "sharedAuthFile": str(shared_auth_path) if shared_auth_path is not None else None,
        "workspaceEnvFile": str(workspace_env),
        "profileSource": profile_source,
        "effectiveProfile": effective_profile,
        "effectiveCapBaseUrl": effective_cap.rstrip("/"),
        "effectiveAuthBaseUrl": effective_auth.rstrip("/"),
        "workspaceOverrideKeys": sorted(workspace_values),
        "envConflictKeys": conflict_keys,
        "keySources": key_sources,
    }


def resolve_runtime_auth_env_file(workspace_root: Path) -> Path | None:
    """Return the auth env file selected by the effective Abel env."""
    auth_value = str(build_effective_abel_env(workspace_root).get(AUTH_ENV_FILE_KEY) or "").strip()
    if auth_value:
        return resolve_auth_env_value(auth_value, workspace_root=workspace_root)
    workspace_env = (workspace_root / ".env").resolve()
    if workspace_env.exists():
        return workspace_env
    return None

def run_python_json(
    python_path: Path | str,
    cwd: Path,
    script: str,
    *,
    env: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Run an inline Python script and parse a JSON payload from stdout."""
    completed = subprocess.run(
        [str(python_path), "-c", script],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=None if env is None else dict(env),
    )
    if completed.returncode != 0:
        return {
            "ok": False,
            "error": completed.stderr.strip() or completed.stdout.strip() or "command failed",
        }
    payload = completed.stdout.strip()
    if not payload:
        return {"ok": False, "error": "no output"}
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"invalid JSON output: {exc}", "stdout": payload}


def probe_abel_edge_import(python_path: Path | str, cwd: Path) -> dict[str, object]:
    """Probe whether the workspace runtime can import abel_edge."""
    return run_python_json(
        python_path,
        cwd,
        """
import json
try:
    import abel_edge  # noqa: F401
except Exception as exc:
    print(json.dumps({"ok": False, "error": str(exc)}))
else:
    print(json.dumps({"ok": True}))
""",
    )


def probe_abel_edge_cli(python_path: Path | str, cwd: Path) -> dict[str, object]:
    """Probe whether the abel-edge CLI entrypoint works in the runtime."""
    return run_python_json(
        python_path,
        cwd,
        """
import json
import subprocess
import sys

completed = subprocess.run(
    [sys.executable, "-m", "abel_edge.cli", "version"],
    capture_output=True,
    text=True,
)
print(json.dumps({
    "ok": completed.returncode == 0,
    "stdout": completed.stdout.strip(),
    "stderr": completed.stderr.strip(),
}))
""",
    )


def probe_edge_discovery_payload(python_path: Path | str, cwd: Path) -> bool | None:
    """Probe whether the installed edge runtime exposes structured discovery payloads."""
    completed = subprocess.run(
        [
            str(python_path),
            "-c",
            (
                "import inspect\n"
                "from abel_edge.plugins.abel.discover import discover_graph_payload\n"
                "print(callable(discover_graph_payload))\n"
            ),
        ],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() == "True"


def probe_edge_context_json(python_path: Path | str, cwd: Path) -> bool | None:
    """Probe whether the installed edge runtime supports ``context_json``."""
    completed = subprocess.run(
        [
            str(python_path),
            "-c",
            (
                "import inspect\n"
                "from abel_edge.research.evaluate import run_evaluation\n"
                "print('context_json' in inspect.signature(run_evaluation).parameters)\n"
            ),
        ],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() == "True"


def build_workspace_runtime_env(
    workspace_root: Path,
    *,
    base: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build a deterministic runtime environment for Abel-edge subprocesses."""
    env = build_effective_abel_env(workspace_root, base=base)
    manifest = load_workspace_manifest(workspace_root)
    cache_root = resolve_workspace_paths(workspace_root, manifest)["cache_root"].resolve()
    env.setdefault("ABEL_EDGE_CACHE_ROOT", str(cache_root))
    return env


def probe_abel_auth(python_path: Path | str, cwd: Path) -> dict[str, object]:
    """Probe whether Abel auth is available to the installed runtime."""
    env_description = describe_effective_abel_env(cwd)
    auth_description = env_description.get("auth")
    if isinstance(auth_description, dict) and auth_description.get("ok"):
        return {
            "ok": True,
            "source": auth_description.get("source"),
            "path": auth_description.get("path"),
        }

    runtime_env = build_workspace_runtime_env(cwd)
    auth_env_file = runtime_env.get("ABEL_AUTH_ENV_FILE")
    if auth_env_file and has_auth_token(auth_env_file):
        auth_path = Path(auth_env_file).expanduser().resolve()
        source = "workspace_env" if auth_path == (cwd / ".env").resolve() else "shared_auth_file"
        return {
            "ok": True,
            "source": source,
            "path": str(auth_path),
        }

    return run_python_json(
        python_path,
        cwd,
        """
import json
import os
from pathlib import Path

from abel_edge.plugins.abel.credentials import (
    _candidate_shared_auth_files,
    _read_env_file,
    normalize_api_key,
)

env_path = Path(".env").resolve()
env_values = _read_env_file(env_path)

env_token = normalize_api_key(
    os.getenv("ABEL_API_KEY")
    or os.getenv("CAP_API_KEY")
)
if env_token:
    print(json.dumps({
        "ok": True,
        "source": "env_var",
        "path": None,
    }))
    raise SystemExit(0)

project_token = normalize_api_key(
    env_values.get("ABEL_API_KEY")
    or env_values.get("CAP_API_KEY")
)
if project_token:
    print(json.dumps({
        "ok": True,
        "source": "workspace_env",
        "path": str(env_path),
    }))
    raise SystemExit(0)

for candidate in _candidate_shared_auth_files(env_path=env_path):
    candidate_values = _read_env_file(candidate)
    shared_token = normalize_api_key(
        candidate_values.get("ABEL_API_KEY") or candidate_values.get("CAP_API_KEY")
    )
    if shared_token:
        print(json.dumps({
            "ok": True,
            "source": "shared_auth_file",
            "path": str(candidate),
        }))
        raise SystemExit(0)

print(json.dumps({
    "ok": False,
    "source": "missing",
    "path": None,
}))
        """,
        env=runtime_env,
    )
