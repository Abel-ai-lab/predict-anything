# Workspace Bootstrap

`abel-invest` is workspace-first. Do not start strategy search until the active
skill bootstrap shim has reconciled the workspace.

## Bootstrap Entry

The bootstrap shim is the only setup and repair entrypoint. It is intentionally
stdlib-only until it creates or reuses the workspace runtime:

```bash
python3 <abel-invest-skill-root>/scripts/bootstrap_workspace.py --path abel-invest-workspace
```

The shim creates or reuses the workspace, refreshes skill-owned generated files
(`README.md`, `AGENTS.md`, `.env.example`, and `.gitignore`), prepares `.venv`,
installs `abel-invest`, then runs an internal runtime doctor from the workspace
environment. Do not call workspace-local lifecycle commands to repair setup.

## Preflight

From the user's current directory:

1. If `alpha.workspace.yaml` exists here, this directory is the workspace root.
2. Else if `abel-invest-workspace/alpha.workspace.yaml` exists here, reuse that
   child workspace.
3. Else choose `abel-invest-workspace` under the current directory as the
   default workspace path.
4. Run the active skill bootstrap shim against that workspace path.

Only move into session or branch work when bootstrap readiness is `ready`.

If bootstrap reports `scaffold_stale`, `runtime_stale`, `env_missing`,
`edge_missing`, or `edge_contract_missing`, fix the stated blocker and rerun the
same active bootstrap shim. If the local machine cannot create a venv, rerun
the shim with `--runtime-python /path/to/python` only when the user intentionally
provides an existing interpreter.

## Auth

Reuse existing Abel auth first. If bootstrap reports `auth_missing`, do not
start live discovery yet. Use `abel-auth`, then rerun the active bootstrap shim.

Do not invent a separate auth flow from this skill. `abel-auth` owns explicit
auth handoff and credential setup.

Abel Invest assembles one effective runtime env before calling Abel-edge:

```text
explicit process env
> workspace .env overrides
> abel-auth/.env.skill shared auth/profile
> runtime defaults
```

The shared `abel-auth/.env.skill` file is the canonical auth/profile source for
normal use. The workspace `.env` file is only a per-workspace override. Do not
copy API keys into workspace `.env` unless the user intentionally wants this one
workspace to use different credentials. Bootstrap reports the effective profile,
CAP base URL, workspace overrides, and any workspace/shared env conflicts.

If the user explicitly asks for offline inspection, you may inspect existing
artifacts without auth, but mark live discovery/evaluation as blocked until
bootstrap readiness is `ready`.

## Workspace Rules

- Keep session and branch artifacts under the workspace `research/` directory.
- Do not create a nested workspace when `alpha.workspace.yaml` already exists.
- Do not create a standalone `abel-edge init` sidecar for this flow.
- Use the command prefix printed by bootstrap, or the workspace-local
  `./.venv/bin/abel-invest`, for strategy commands.
- Create sessions only after bootstrap readiness is confirmed. Avoid `--root`
  unless intentionally creating a legacy/offline session outside a workspace;
  then pass `--allow-outside-workspace`.
- Bootstrap creates the workspace and runtime base; branch-specific market data
  is resolved later by `prepare-branch`.

## Common Strategy Commands

```bash
./.venv/bin/abel-invest init-session --ticker <TICKER> --exp-id <exp-id>
./.venv/bin/abel-invest frontier status --session research/<ticker>/<exp_id>
./.venv/bin/abel-invest init-branch --session research/<ticker>/<exp_id> --branch-id <branch-id>
./.venv/bin/abel-invest prepare-branch --branch research/<ticker>/<exp_id>/branches/<branch-id>
./.venv/bin/abel-invest run-branch --branch research/<ticker>/<exp_id>/branches/<branch-id> -d "candidate search result"
```
