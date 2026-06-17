# Abel Skills

Abel Skills is the collection repository for Abel agent skills. Users should install the collection and start from `Abel`, which routes to the right internal skill for causal reads, strategy discovery, or auth recovery.

## Main Skills

- `abel`: main entrypoint
- `abel-ask`: graph-native and proxy-routed causal reads
- `abel-auth`: connect or repair Abel auth
- `abel-invest`: workspace-first strategy discovery

## Abel-Invest Capability Snapshot

The Abel Invest skill adds value in layers: first by moving beyond a vanilla
LLM-only strategy pick, then by running a repeatable target-price candidate
search, then by adding causal graph candidate generation and Abel workflow
discipline. The June 2026 benchmark suite makes those layers explicit over the
same `1,000` selected tickers.

| Baseline / arm | What changed | OK rows | Mean Sharpe | Median Sharpe | P10 Sharpe | Median max DD | Median return/DD | Mean candidates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Vanilla LLM-only no skill / no graph | No empirical candidate scoring; the LLM picks one grammar item from summary stats | `962 / 1000` | `0.2016` | `0.2205` | `-0.3199` | `-0.3184` | `0.4487` | `40.0` |
| Target-history candidates, no skill / no graph | Scores `40` target-only autoregressive price candidates and picks best Sharpe | `959 / 1000` | `0.7617` | `0.7530` | `0.4686` | `-0.2616` | `5.7652` | `40.0` |
| Graph-only target + causal candidates | Adds generic CAP graph neighbors and graph-driven candidate families without `abel-invest` | `959 / 1000` | `0.9514` | `0.9374` | `0.6461` | `-0.2527` | `9.5752` | `198.2` |
| Skill-only target candidates | Uses the Abel Invest workflow with graph disabled | `998 / 1000` | `0.8194` | `0.8088` | `0.5126` | `-0.1916` | `5.7444` | `40.0` |
| Full Abel skill + causal graph | Uses Abel Invest workflow, graph discovery/materialization, and target + graph empirical scout | `835 / 1000` | `1.0245` | `1.0099` | `0.7089` | `-0.1666` | `8.1007` | `207.0` |

The important comparison is not just "skill versus a weak prompt." The
vanilla LLM-only control averaged only `0.2016` Sharpe because it selected a
single strategy from summary statistics without scoring the candidate grid. The
stronger no-skill/no-graph control averaged `0.7617` Sharpe because it
empirically evaluated the `40` target-history candidates. Abel still improves
on that harder baseline: the skill-only arm raises mean Sharpe to `0.8194` and
materially reduces typical drawdown, while graph access raises the no-skill
candidate scout to `0.9514` mean Sharpe. Combining Abel Invest with the causal
graph produces the strongest risk-adjusted readout: `1.0245` mean Sharpe,
`1.0099` median Sharpe, the best 10th-percentile Sharpe, and the smallest
median drawdown.

A stricter four-arm factorial benchmark then isolated two capabilities over
`1,000` tickers: Abel Invest skill use and Abel causal graph access. Each arm
received the same strategy-discovery objective and differed only in the
capabilities made available to the agent:

| Arm | Abel Invest skill | Causal graph | OK coverage | Mean Sharpe | Median Sharpe | P10 Sharpe | Median max DD | Median return/DD | Mean candidates |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Skill + graph | `yes` | `yes` | `835 / 1000` (`83.5%`) | `1.0245` | `1.0099` | `0.7089` | `-0.1666` | `8.1007` | `207.0` |
| Skill only | `yes` | `no` | `998 / 1000` (`99.8%`) | `0.8194` | `0.8088` | `0.5126` | `-0.1916` | `5.7444` | `40.0` |
| Graph only | `no` | `yes` | `959 / 1000` (`95.9%`) | `0.9514` | `0.9374` | `0.6461` | `-0.2527` | `9.5752` | `198.2` |
| No skill / no graph | `no` | `no` | `959 / 1000` (`95.9%`) | `0.7617` | `0.7530` | `0.4686` | `-0.2616` | `5.7652` | `40.0` |

The strongest readout is risk-adjusted quality. The full Abel stack
(`skill + graph`) had the highest mean Sharpe, highest median Sharpe, strongest
10th-percentile Sharpe, and the smallest typical drawdown. Against the pure
control on the all-four-OK paired set (`803` tickers), the full stack won on
Sharpe for `710 / 803` tickers (`88.4%`), reduced drawdown for `583 / 803`
tickers (`72.6%`, less negative is better), and won on return/drawdown for
`533 / 795` defined pairs (`67.0%`).

The factor isolation shows what each capability contributes:

- Skill effect with graph held fixed: the skill arm beat graph-only on Sharpe
  for `526 / 803` paired tickers (`65.5%`) and reduced drawdown for
  `646 / 803` (`80.4%`).
- Skill effect without graph held fixed: skill-only beat the no-skill baseline
  on Sharpe for `548 / 959` paired tickers (`57.1%`) and reduced drawdown for
  `781 / 959` (`81.4%`).
- Graph effect with skill held fixed: adding the graph to the skill improved
  mean Sharpe by `+0.2125`; the graph-enhanced skill arm beat skill-only on
  Sharpe for `599 / 835` paired tickers, tied on `233`, and lost only `3`.
- Graph effect without skill held fixed: adding the graph to the no-skill runner
  improved mean Sharpe by `+0.1897` and won Sharpe for `724 / 959` paired
  tickers.

The `40` target-only candidates are simple target-history rules:
`16` mean-reversion z-score variants, `12` trend-strength templates, and `12`
breakout variants. They are a strong autoregressive baseline because they score
the target ticker's own close-price history, but they do not use the Abel skill
or any causal graph node. The graph arms add causal-neighbor lead/ensemble
candidate families on top of that target-history grid; the skill arms add Abel's
workspace discipline, graph materialization when enabled, strategy packaging,
and repairable session workflow.

The graph arms sometimes found larger raw total returns, but they also took
rougher paths with materially deeper typical drawdowns. The product claim is
therefore precise: Abel skills and the causal graph improve risk-adjusted
strategy discovery, drawdown control, search coverage, and candidate breadth;
they are not a promise to maximize raw return regardless of risk.

Isolation checks passed across all `100` chunks in every arm. The audit recorded
the intended capability flags only (`uses_abel_invest=True` only in skill arms,
`uses_causal_graph=True` only in graph arms), with
`abel_invest_module_leak_count=0`, `blocked_forbidden_host_count=0`, and no
failed chunks. After the benchmark, the full skill + graph strategy-artifact
repair and upload workflow made `1000 / 1000` full-stack strategies hostable in
the Abel strategy pool; the paired metric tables above preserve the original
strict comparable-run counts.

Backtests and benchmark comparisons are research artifacts, not investment advice.

## Installation

Installation differs by platform.

### Codex

Tell Codex:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/Abel-ai-causality/Abel-skills/refs/heads/main/.codex/INSTALL.md
```

**Detailed docs:** [docs/README.codex.md](docs/README.codex.md)

Supports:
- Global install
- Project-level install via `.agents/skills/`

### Claude Code

Tell Claude Code:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/Abel-ai-causality/Abel-skills/refs/heads/main/.claude/INSTALL.md
```

**Detailed docs:** [docs/README.claude.md](docs/README.claude.md)

Supports:
- Global install
- Project-level install via `.claude/skills/`

### OpenCode

Tell OpenCode:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/Abel-ai-causality/Abel-skills/refs/heads/main/.opencode/INSTALL.md
```

**Detailed docs:** [docs/README.opencode.md](docs/README.opencode.md)

Supports:
- Global install
- Project-level install via project `opencode.json`

### ClawHub / OpenClaw

Install from the published ClawHub package after release publication.

Install-time auth note:
- If you already have an Abel API key, write it to the OpenClaw skill config path `skills.entries.abel.apiKey` before restart.
- If you do not, make `abel-auth` your first action after restart so the key is persisted before normal live use.
- After auth is ready, bootstrap the default strategy workspace before normal strategy use: `abel-invest workspace bootstrap --path ./abel-invest-workspace`

## Try These Questions

- Help me search for a TSLA strategy.
- Find a few Abel-discovered candidates around semiconductor demand.
- Continue my TSLA strategy workspace.
- Give me an Abel read on what drives mortgage-rate-sensitive homebuilder stocks.

## For Maintainers

- Release documentation: [docs/releases.md](docs/releases.md)
- Branching and repository policy: `AGENTS.md`
- Maintainer endpoint rendering workflow: `maintainers/abel-ask/README.md`

Release builds publish from collection source into `dist/`. Do not commit generated ClawHub artifacts into the repository.
