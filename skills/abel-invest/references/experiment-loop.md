# Experiment Loop

Use this reference after workspace preflight is complete and doctor is ready.
Commands below use the workspace `command_prefix` returned by
`workspace context --json` or doctor.

Before creating a new session, confirm the workspace context:

```bash
<command_prefix> workspace context --path . --json
```

Use the resolved workspace `research_root`. Do not pass `--root` unless this
is an intentional legacy/offline session outside a workspace; in that case pass
`--allow-outside-workspace` too.

## Standard Path

Examples assume the current directory is `<workspace_root>` and session paths are
relative to that root.

Run:

```bash
<command_prefix> init-session --ticker <TICKER> --exp-id <exp-id>
<command_prefix> frontier status --session research/<ticker>/<exp_id>
```

Live graph discovery should run by default when available. Its output is the
default high-value expanded candidate universe, not a mandatory first branch and
not a requirement to run the whole depth-1 frontier as one basket.

Then choose a candidate path from the user's objective and the data context:

- existing validated baselines or catalog strategies
- target-only features as baseline and competing candidates
- graph-derived feeds and causal nodes as the default expanded feature universe
- available sector, cross-asset, volume, liquidity, and regime features
- proven empirical patterns and feature-factory ideas
- user constraints such as Sharpe, drawdown, return, grandma mode, or no leverage

Create one or more branches for selected candidates:

```bash
<command_prefix> init-branch --session research/<ticker>/<exp_id> --branch-id <candidate-branch>
```

Then prepare, debug, and record the agent-chosen candidate:

```bash
<command_prefix> prepare-branch --branch research/<ticker>/<exp_id>/branches/<candidate-branch>
<command_prefix> debug-branch --branch research/<ticker>/<exp_id>/branches/<candidate-branch>
<command_prefix> run-branch --branch research/<ticker>/<exp_id>/branches/<candidate-branch> -d "candidate search result"
```

If the recorded candidate was selected from a local parameter, model, factor, or
node-subset search, pass `--selection-trials N`, where `N` is this round's
effective search width only.

After the recorded round, keep `research/<ticker>/<exp_id>/exploration_path.md`
covered with ledger ref, chosen path, compact reason, Edge feedback, and artifact
refs before another recorded round.

Only after the user asks to publish the paper-ready session, or agrees after a
PASS:

```bash
<command_prefix> visualize-session --session research/<ticker>/<exp_id> --with-strategy-artifact
```

## Research Loop

Each round should advance the search toward the user objective.

1. Read `agent_context.md` when resuming.
2. Use `frontier.md` for factual context: available graph nodes, runtime reads,
   input realization, search concentration, metric failures, and path coverage.
3. Use `exploration_path.md` as the concise round log. It protects visualization
   and replay completeness; entries should stay short.
4. Generate candidates from the target/baseline context and the graph-enriched
   candidate universe.
5. Prefer empirical screening when it can cheaply test parameter choices, model
   families, lags, signs, transformations, graph-node subsets, or feature
   factories without leaking future information.
6. Compare graph-enriched candidates against target/baseline candidates to
   measure marginal graph contribution instead of assuming it.
7. Declare enough branch metadata for runtime and audit: objective, input
   universe, evaluation window, search width, and validation scope. Mechanism
   and graph-attribution notes can stay lightweight until evidence is strong.
8. Run `prepare-branch` before trusting branch inputs.
9. Run `debug-branch` before recording evidence.
10. Run `run-branch` only when declaration and debug facts are ready enough for
    the evidence label you want.
11. Re-read `evidence_ledger.json`, `frontier.md`, and the latest Edge result.
12. Let metric failures choose the next route: refine, re-search, change model
    family, change graph subset, add target/baseline contrast, or stop.
13. Ensure `exploration_path.md` has the recorded round before starting another
    recorded round.

Optimization is not a deviation. The failure mode is reporting an unvalidated
raw winner, not searching. Use honest K/search-width accounting and final
validation before claiming success.

## Layer Ownership

- session: graph frontier, candidate-universe context, expansion provenance, and readiness
- branch: branch declaration and `compute_decisions(self, ctx)`
- edge cache: market data reuse
- prepare step: branch input resolution and runtime contract materialization
- debug step: semantic preflight
- run step: evaluation, DSR trial-count declaration, and evidence recording

Session `backtest_start` is the default exploration target. When
`branch.yaml.requested_start` is explicit, that branch start should drive
prepare/debug/run for the branch.

`run-branch` writes `validation_context.dsr_trials.count` into the Alpha context
passed to `abel-edge evaluate`. The current round defaults to `1`. If a search
selected one submitted candidate from multiple variants, pass
`--selection-trials N`, where `N` is this round's width only, never a running
campaign total. `guarded-optimization.md` owns the final-K reporting rules.

If performance scouting happened before the recorded candidate, declare the
effective search width and record what happened in `exploration_path.md`. Treat
the result as search-informed rather than pretending it was one isolated idea.

## Before Exhaustion Or No-Edge Claims

Do not write "exhausted", "ceiling", or "no edge" from a single failed
mechanism, a small round count, or a green per-candidate gauntlet. Exhaustion is
a ledger conclusion.

Before making that claim, check that the ledger shows:

1. a bounded candidate universe was actually searched or intentionally ruled out
2. graph-derived candidates were considered when live graph discovery was
   available, unless the user chose a simple/conservative lane
3. target/baseline performance was compared against graph-enriched performance
   where useful
4. materially different model families, feature constructions, or search axes
   were tried, not only one hand-written rule
5. all attempted width is K-accounted, including preflight or workflow ERROR
   variants that would otherwise be audited but skipped from future DSR

Stop conditions are a gauntlet-PASS candidate at the target or ledger-supported
exhaustion. Do not stop by round count.

## Evidence Reading

After each render, treat:

- `evidence_ledger.json` as the evidence record
- `frontier.md` / `frontier.json` as factual search-context reports
- `agent_context.md` as the compact factual resume surface
- `exploration_path.md` as the single human-facing exploration log

`path_coverage_complete=false` means at least one recorded round still needs an
`exploration_path.md` entry with the round ledger ref, selected path, compact
reason, Edge feedback, and artifact refs.

Input realization separates declaration from runtime behavior. A branch can
declare `input_claim=graph_supported`, but if the strategy does not read
prepared graph inputs, that round is summarized as a graph input read gap and
should not be used as evidence for graph-derived contribution.

The generated surfaces should show what happened, not tell you which driver,
proxy, threshold, model family, or mechanism to try next.

Abel Ask or narrative context can help form candidate features, graph expansion
anchors, and interpretation. It is scout context, not validation evidence.

## Session Visualization

Do not create an online session view automatically. When the strategy context
is mature enough to be useful to review visually, ask the user whether to
visualize the session. This can be after a strong candidate PASS, after several
informative candidate rounds, before promotion, or whenever the agent would
naturally summarize that the strategy is worth a visual review. If the user
agrees, or if the user explicitly asks to visualize the session, pass the
session folder to the command:

```bash
<command_prefix> visualize-session --session research/<ticker>/<exp_id> --with-strategy-artifact
```

The command builds the online view from local session evidence and uploads the
automatically selected best `PASS` strategy artifact when one is available. Use
narrative-only `visualize-session` only when the user explicitly asks for a
session view without strategy artifact upload. If the command reports
`needs_agent_refactor`, read the emitted `refactor-request.json` and handle it
in the current skill loop. If `kind` is `state_intent_self_check`, inspect the
selected branch source and nearby model/checkpoint/cache files, then write
`state_intent.json`: either classify every durable state file required for
paper startup, or explicitly write an empty `entries` list with a `selfCheck`
summary explaining why the detected files are not durable paper state. If
`kind` is `agent_assisted`, edit only the promoted copy named there, write
`refactor-report.json`, and rerun the same command. Do not start a separate
agent process. The agent should not hand-assemble the payload or choose a
router URL.

Default router base URL: `https://api.abel.ai/router/`.
`abel-auth` is the canonical owner for API key setup. Maintainers should update
the default URL in the skill code if this endpoint changes.

## Exploration Discipline

`discovery-protocol.md` owns graph context, CAP role interpretation, frontier
expansion, and narrative scout facts. In the round loop, preserve the core
shape:

```text
user objective -> candidate universe -> empirical screening -> recorded validation -> explanation
```

Multiple branches on one graph input set can still be a narrow search if they do
not change the useful search axis. Parameter, threshold, model, factor, and node
subset changes are legitimate search axes when they are intentional and
K-accounted.
