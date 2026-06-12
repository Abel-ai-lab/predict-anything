# Predict Anything Strategy Research

Predict Anything is an AI agent skill collection for prediction-first strategy research with Abel: ask market questions, test strategy ideas, validate candidates, and track the evidence.

## Strategy Discovery, Not Trade Execution

These skills are designed for research workflows:

- exploring market themes
- forecasting what may move next
- developing investment strategy hypotheses
- comparing evidence, risks, and candidates
- preparing next research steps

They do not place trades, automate execution, or provide a backtesting engine.

## Common Workflows

### Explore A Market Theme

Ask an agent to explore a natural-language market question, such as semiconductor demand, power demand from data centers, mortgage-rate-sensitive sectors, or AI infrastructure supply chains.

### Develop An Investment Strategy

Use Abel to turn a company, sector, or market theme into a strategy thesis with signals, risks, and evidence.

### Continue Strategy Research

Resume prior Abel research, inspect recorded signals and risks, and decide the next research step.

### Analyze Market Drivers

Analyze companies, sectors, themes, and market drivers before deciding whether a strategy idea deserves deeper research.

### Prepare Research Next Steps

Organize hypotheses, candidates, open risks, missing evidence, and follow-up questions for an analyst or agent workflow.

## Benchmark Evidence

The June 2026 four-arm benchmark isolates Abel Invest skill use and Abel causal
graph access across `1,000` selected tickers. The full Predict Anything stack
(`skill + graph`) delivered the strongest risk-adjusted profile: highest mean
Sharpe, highest median Sharpe, strongest 10th-percentile Sharpe, and the
smallest typical drawdown.

Read the detailed results: [Four-Arm Abel Invest Capability Benchmark](four-arm-benchmark.md).

## Main Skills

- `abel`: routes strategy discovery, market analysis, investment research, and auth recovery
- `abel-invest`: core strategy discovery and investment research skill
- `abel-ask`: analysis of market drivers, candidate lists, and decisions
- `abel-auth`: Abel authentication setup and repair
