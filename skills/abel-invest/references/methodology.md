# Methodology

Use this optional reference when the user asks why the workflow is graph-first,
why evidence labels are strict, or why the framework refuses to recommend the
next strategy route.

## Boundary

The product boundary is:

```text
framework = evidence validity and exploration-shape facts
agent = strategy judgment and research insight
```

`abel-edge` owns runtime legality and validation metrics.
`abel-invest` owns branch declarations, evidence labels, frontier
facts, and the research journal surface.

## Core Principles

**Causal graph first.**
Use Abel-discovered causal structure as the default search prior because it
reduces blind search and is more likely to survive regime change. Correlation
signals can still be useful, but they enter as supplements or controls unless
the branch declares and validates a stronger claim.

CAP graph nodes are causal priors, not trading instructions. They do not provide
the trading sign, lag, or a monotone strength map; deeper nodes are weaker or
more indirect priors unless recorded evidence or domain context justifies them.

Graph-first means using the graph to form input and mechanism hypotheses. Expand
the graph when a frontier question remains after reading current evidence. Do
not expand just because a few branches failed or because a local metric scan
found one attractive node.

**Mechanism-led discovery beats metric-led search.**
Standard discovery chooses a branch from graph context, mechanism reasoning,
recorded evidence, or a control/ablation purpose before metric search. Local
parameter, threshold, window, filter, sizing, driver, or asset sweeps are
optimization behavior unless the user explicitly requests them.

`--selection-trials` audits accidental or explicitly requested search width. It
does not make brute-force candidate selection part of standard discovery.

**Narrative scout is context, not evidence.**
Abel Ask and narrative context can generate mechanism hypotheses, supplement
driver ideas, and graph expansion questions. Treat them as domain-context scout
work: stronger than free association, weaker than CAP graph facts, and never a
substitute for Edge validation.

**Evidence labels are not strategy advice.**
Candidate/control/diagnostic/blocker labels say what kind of research evidence a
run produced. They do not choose the next driver, model, threshold, or mechanism.

**Runtime legality is non-negotiable.**
If a strategy reads information it could not have seen at decision time, the
backtest is invalid. The current authoring contract expresses legal reads
through `DecisionContext` and semantic preflight.

**Multi-dimensional validation beats single-metric selection.**
The validation profile can evolve, but the principle is stable: avoid promoting
strategies from one attractive metric when other evidence says the signal is
fragile, concentrated, or illegal.

**Serial compounding beats static grids.**
Each round should update the agent's understanding. Static parameter grids can
hide whether the search is learning or just overfitting a neighborhood.

**The journal is agent-owned.**
`research_journal.md` preserves hypotheses, observations, pivots, and stop/keep
reasoning between turns. Evidence references make journal insights durable, but
the journal itself is not evidence truth.

## Current Workflow Consequence

The branch-default path is:

1. resolve workspace and doctor readiness
2. start or resume a graph-first session
3. read ledger, frontier, and journal facts
4. use narrative scout only when it helps form a mechanism or frontier question
5. expand `graph_frontier.json` only when current evidence leaves a frontier
   question unresolved
6. declare branch hypothesis and selected graph inputs
7. prepare branch inputs
8. write `compute_decisions(self, ctx)`
9. run semantic preflight
10. record evidence
11. inspect ledger/frontier facts
12. update the research journal before deep local refinement
