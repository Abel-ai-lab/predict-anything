# Methodology

Use this optional reference when the user asks why the workflow is data-led,
why the causal graph still matters, why evidence labels are strict, or why
validation gates do not replace strategy search.

## Boundary

The product boundary is:

```text
framework = runtime legality, evidence facts, search-width accounting, validation
agent = candidate generation, strategy search, and research judgment
```

`abel-edge` owns runtime legality and validation metrics.
`abel-invest` owns branch declarations, evidence labels, candidate-universe
facts, search-width accounting, and the exploration path surface.

## Core Principles

**Data-led objective search.**
The job is to find a high-quality strategy for the user's objective, usually
high Sharpe, high return, or a constrained risk-return profile. Observed
results, failure modes, and metric shape should drive the next candidate family.
Mechanism stories organize and explain the search; they do not admit a strategy.

**Graph as default high-value candidate universe.**
Abel-discovered causal structure is a validated prior and should normally enter
candidate generation early. It expands the search beyond target-only price and
volume history. That does not mean the first serious candidate must use the
entire depth-1 frontier as one basket. The graph supplies a node universe; data
selects subsets, lags, transformations, model families, and roles such as alpha,
filter, sizing signal, or regime context.

**Target-only is baseline and competitor, not second-class evidence.**
Target-only candidates can be first-class strategies when they survive
validation. They also establish the benchmark for graph-derived marginal
contribution. A graph-enriched candidate should earn its place by improving the
objective or robustness relative to target/baseline behavior, not by graph
membership alone.

**Search is allowed when honestly accounted.**
Parameter search, model hyperparameter search, factor construction, graph-node
subset search, lag/sign search, and feature-factory screening are legitimate
ways to find strategies. The product should make search width visible and
K-accounted rather than pushing the agent to hide many experiments inside one
hand-written strategy.

**Gate validates; it does not throttle exploration.**
The gauntlet, DSR, leakage checks, walk-forward behavior, and promotion gate
decide what can be reported as robust. They should not prevent empirical
screening. A raw-metric winner is not a strategy success until it clears the
required validation with honest search-width accounting.

**Evidence entry; mechanism is post-hoc.**
A candidate enters on validation survival, not on the strength of its mechanism
story. Mechanism and graph-attribution notes are most useful after a pass or
meaningful near-pass, when there is evidence worth explaining.

**Runtime legality is non-negotiable.**
If a strategy reads information it could not have seen at decision time, the
backtest is invalid. The current authoring contract expresses legal reads
through `DecisionContext` and semantic preflight.

**Multi-dimensional validation beats single-metric reporting.**
The validation profile can evolve, but the principle is stable: avoid promoting
strategies from one attractive metric when other evidence says the signal is
fragile, concentrated, illegal, or not robust after K accounting.

**The exploration path is evidence-linked and concise.**
`exploration_path.md` preserves each recorded round's selected path, compact
reason, Edge feedback, and ledger/artifact references. It protects
visualization and replay completeness. It should not require a heavy mechanism
essay before the next candidate can run.

## Current Workflow Consequence

The branch-default path is:

1. resolve workspace and doctor readiness
2. check existing baselines or strategy catalog entries
3. start or resume a session; run live graph discovery when available
4. build a candidate universe from target/baseline features, graph nodes,
   available cross-assets, proven patterns, and user constraints
5. generate and screen candidates empirically, including graph-enriched feature
   factories, ensembles, node subsets, lag/sign searches, model-family
   comparisons, and simple target baselines
6. keep search width honest and avoid temporal leakage
7. declare enough candidate metadata for runtime and audit: objective, inputs,
   window, search width, and validation scope
8. prepare branch inputs
9. write `compute_decisions(self, ctx)` against `DecisionContext`
10. run semantic preflight
11. record selected candidates through Edge with the right `--selection-trials`
12. inspect ledger/frontier facts and metric failures
13. keep `exploration_path.md` covered before the next recorded round
14. explain mechanism and graph contribution after evidence, not before
