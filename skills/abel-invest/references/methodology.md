# Methodology

Use this optional reference when the user asks why Abel Invest is data-driven,
why the causal graph still matters, why search is allowed, or why validation
gates do not replace strategy search. It is a principles note, not a loop
checklist; `SKILL.md` and `experiment-loop.md` own ordinary execution flow.

## Boundary

Abel Invest is an alpha-search product.

```text
framework = temporal legality, evidence facts, search-width accounting, reportability
agent = candidate generation, empirical search, and strategy judgment
```

`abel-edge` owns runtime legality and validation metrics. `abel-invest` owns
branch declarations, evidence labels, candidate-universe facts, search-width
accounting, and the exploration path surface. The agent owns what to try next.

## Core Stance

**Search hard, then explain.**
The job is to find a high-quality strategy for the user's objective, usually
high Sharpe, high return, or a constrained risk-return profile. The default
objective is defined in `SKILL.md` and `experiment-loop.md`. Mechanism stories
organize results after evidence appears; they should not slow the first useful
empirical test.

**Empirical construction by default.**
For ordinary alpha search, the default posture is empirical
construction over target and graph-derived data. Feature factories, model
families, denoise, subsets, ensembles, regimes, filters, and sizing are
degrees of freedom. Simple rules can benchmark, diagnose, ablate, or refine an
empirical lead, but they are not the default search engine.

**Graph as alpha universe.**
Abel-discovered causal structure is a validated prior and should normally enter
candidate generation early. It expands the search beyond target-only price and
volume history. The graph supplies a rich node universe; data selects subsets,
lags, signs, transformations, model families, interaction terms, filters,
sizing signals, and regime roles.

**Target-only as benchmark, seed, and competitor.**
Target-only candidates are useful baselines, simple seeds, ablations, and
competing strategies. They should not become the default hiding place when live
graph candidates are available. Their main product role is to reveal whether
graph-derived information improves the objective or robustness.

**Empirical search is normal.**
Feature construction, model-family comparison, HPO, graph-node subset search,
lag/sign search, ensembles, regime filters, and sizing search are legitimate
exploration. Make the search width visible; do not pretend a selected winner
came from one isolated hand-written idea.

**Graph-supported is not enough.**
Runtime graph reads prove input realization. They do not by themselves prove the
agent searched the graph as data. Abel Invest should mine the graph-derived
universe for subsets, lags, transformations, models, regimes, filters, sizing
signals, and ensemble roles.

**Validation estimates reliability; it does not throttle search.**
Gates, DSR, leakage checks, walk-forward behavior, and promotion checks decide
how confidently a candidate can be reported. They should not prevent empirical
screening. Passing more gates makes a high-Sharpe/high-return candidate more
reliable; a raw-metric winner is not robust until required validation and honest
search-width accounting support that claim.

**Artifact completeness stays hard.**
`exploration_path.md` preserves each recorded round's selected path, compact
reason, Edge feedback, and ledger/artifact refs. It protects visualization and
replay completeness. Keep it short and evidence-linked; do not turn it into a
mechanism essay.

`experiment-loop.md` owns the runtime path, and
`data-driven-construction.md` owns the construction catalog. This file only
explains why strategy judgment stays with the agent while the framework owns
legality, evidence facts, search-width accounting, and reportability.
