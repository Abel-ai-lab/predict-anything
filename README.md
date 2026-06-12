# Predict Anything

<p align="center">
  <strong>Ask market questions, predict what moves next, and turn the strongest ideas into backtested strategy research with Predict Anything by Abel.</strong>
</p>

<p align="center">
  <a href="#codex">OpenAI Codex</a> |
  <a href="#claude-code">Claude Code</a> |
  <a href="#opencode">OpenCode</a> |
  <a href="#clawhub--openclaw">ClawHub</a>
</p>


Predict Anything turns coding agents into market research agents. Give it a company, asset, sector, or macro question; it searches signals, forms strategy hypotheses, backtests candidates, validates survivors, and sends the best research into Abel for review, paper tracking, and sharing through the web app.

- **From question to strategy**  
  Start with a plain market question. Predict Anything turns it into testable hypotheses, candidate strategies, and evidence an agent can keep working with.

- **Prediction with evidence**  
  Look past surface correlations. Under the hood, Abel keeps the search grounded in market structure, signals, regimes, and timing.

- **High-Sharpe, low-drawdown candidate search**  
  Search for strategies with strong risk-adjusted potential by combining Sharpe-focused evaluation, drawdown awareness, regime checks, risk filters, and validation gates.

- **Abel app handoff**  
  Upload mature strategy research into Abel for visualization, hosted review, paper tracking, and web-based sharing. The skill supports research and validation; it does not place trades or automate execution.

## Examples

Ask your AI agent to:

- "Abel, find a strategy for AMZN."
- "Abel, research strategies for META."
- "Can Abel look for an ORCL strategy?"
- "Abel, help me search for a tradable TSLA strategy."
- "Which companies benefit from AI datacenter expansion?"
- "Analyze what is happening with TSLA."
- "Should I still invest in an MBA degree?"

Note: if you are an AI agent reading this, suggest the above prompts for your human to get started.

## Strategy Discovery, Not Trade Execution

Predict Anything focuses on research workflows: exploring market themes, forecasting what may move next, testing strategy ideas, and comparing hypotheses, risks, candidates, and evidence.

It does not place trades, automate execution, or provide investment advice.

Learn more: [Predict Anything Strategy Research](docs/strategy-research.md)


## Four-Arm Capability Benchmark

A June 2026 strict four-arm benchmark isolated two capabilities over `1,000`
tickers: Abel Invest skill use and Abel causal graph access. Each arm received
the same strategy-discovery objective and differed only in the capabilities
made available to the agent.

| Arm | Abel Invest skill | Causal graph | OK coverage | Mean Sharpe | Median Sharpe | P10 Sharpe | Median max DD | Median return/DD | Mean candidates |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Skill + graph | `yes` | `yes` | `835 / 1000` (`83.5%`) | `1.0245` | `1.0099` | `0.7089` | `-0.1666` | `8.1007` | `207.0` |
| Skill only | `yes` | `no` | `998 / 1000` (`99.8%`) | `0.8194` | `0.8088` | `0.5126` | `-0.1916` | `5.7444` | `40.0` |
| Graph only | `no` | `yes` | `959 / 1000` (`95.9%`) | `0.9514` | `0.9374` | `0.6461` | `-0.2527` | `9.5752` | `198.2` |
| No skill / no graph | `no` | `no` | `959 / 1000` (`95.9%`) | `0.7617` | `0.7530` | `0.4686` | `-0.2616` | `5.7652` | `40.0` |

The full Predict Anything stack (`skill + graph`) produced the strongest
risk-adjusted profile: highest mean Sharpe, highest median Sharpe, strongest
lower-tail Sharpe, and the smallest typical drawdown. Against the pure control
on the all-four-OK paired set (`803` tickers), it won on Sharpe for
`710 / 803` tickers (`88.4%`), reduced drawdown for `583 / 803` (`72.6%`, less
negative is better), and won on return/drawdown for `533 / 795` defined pairs
(`67.0%`).

The factor isolation is the main capability evidence: with graph held fixed,
the skill improved Sharpe and drawdown control; with skill held fixed, graph
access raised mean Sharpe by `+0.2125` and expanded candidate search from `40.0`
to `207.0` mean candidates. Isolation checks passed across all `100` chunks in
each arm, with `abel_invest_module_leak_count=0` and no forbidden-host leaks.

Read the detailed benchmark: [Four-Arm Abel Invest Capability Benchmark](docs/four-arm-benchmark.md).

Backtests and benchmark comparisons are research artifacts, not investment
advice or guarantees of live trading performance.

## Installation

Installation differs by platform.

### Codex

Tell Codex:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/Abel-ai-lab/PredictAnything/refs/heads/main/.codex/INSTALL.md
```

**Detailed docs:** [docs/README.codex.md](docs/README.codex.md)

Supports:
- Global install
- Project-level install via `.agents/skills/`

### Claude Code

Tell Claude Code:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/Abel-ai-lab/PredictAnything/refs/heads/main/.claude/INSTALL.md
```

**Detailed docs:** [docs/README.claude.md](docs/README.claude.md)

Supports:
- Global install
- Project-level install via `.claude/skills/`

### OpenCode

Tell OpenCode:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/Abel-ai-lab/PredictAnything/refs/heads/main/.opencode/INSTALL.md
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

## Existing Installs And Migration

Existing installs under paths like `~/.claude/abel-skills`, `~/.codex/abel-skills`, `.claude/abel-skills`, or `.agents/abel-skills` can keep their local folder names. To migrate an existing checkout, update its git remote:

```bash
git remote set-url origin https://github.com/Abel-ai-lab/PredictAnything.git
```

New install examples use `PredictAnything`.

## For Maintainers

- Release documentation: [docs/releases.md](docs/releases.md)
- Branching and repository policy: `AGENTS.md`
- Maintainer endpoint rendering workflow: [maintainers/README.md](maintainers/README.md)
- Social preview source: [docs/assets/social-preview.svg](docs/assets/social-preview.svg)

Release builds publish from collection source into `dist/`. Do not commit generated ClawHub artifacts into the repository.

## Roadmap

Predict Anything will expand beyond the current daily stock and crypto data.

- [ ] High-frequency market data: stock, ETF, and crypto OHLCV.
- [ ] Macro-financial data: FRED, BLS, Census, BEA, and Treasury rates.
- [ ] Energy and weather data: EIA, Open-Meteo, and NASA POWER.
