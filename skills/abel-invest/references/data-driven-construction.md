# Data-Driven Construction

Use this reference for ordinary non-grandma alpha search, especially during
early candidate construction, after a simple baseline, or when the next idea is
another hand-written rule.

This is the default construction stance, not a separate workflow. Runtime
legality, honest search-width accounting, and validation still decide what can
be reported.

## Default Engine

Build candidates by empirical construction over a bounded current universe:

- target history and any validated baseline or catalog strategy
- live graph nodes and graph-derived feeds when available
- selected supplemental cross-asset, volume, liquidity, sector, or regime feeds
  when evidence or the user goal justifies them

The graph bounds and enriches the alpha universe. It does not prescribe one
tradable basket, and it is not satisfied by placing a few nodes into a simple
hand-written rule.

## Graph-Frontier Portfolio

For ordinary alpha search, the default early posture is a small portfolio of
materially different graph-derived candidate universes or extractors. Examples:

- direct frontier feature factory
- causal-role buckets such as parent, child, blanket, or local neighborhood
- graph-node subset, lag, sign, transformation, ratio, or spread search
- learned target+graph model such as linear, tree, GBDT, or hybrid
- unsupervised denoise or compression over target+graph features
- graph-as-regime, graph-as-risk filter, graph-as-sizing signal, or ensemble
  member search

This is a construction stance, not a branch quota. The point is to let graph
views compete before the search spends most of its budget polishing one lead.

## Serious Construction Moves

For normal alpha search, serious early construction can use these empirical
moves:

- deterministic feature factory over target + graph-derived fields
- weak-signal ensemble with diversity-aware member selection
- graph-node subset, lag, sign, transformation, ratio, spread, or rolling-window
  search
- model-family comparison such as linear, tree, GBDT, or hybrid models
- supervised target/graph model when label and horizon are temporally legal
- unsupervised denoise or compression such as PCA/ICA when temporally legal
- regime, sizing, or filter search layered on an otherwise plausible alpha

It does not have to use the whole frontier, and it should not expand the graph
just to look broad. Prefer the bounded feature universe most likely to improve
the user's objective.

## Earned Expansion

Graph expansion is allowed when current evidence points outside the current
view. Good triggers include:

- a useful node or role bucket that needs local neighborhood context
- an unavailable or thin input that needs a nearby substitute
- a missing liquidity, demand, market-state, supply, or risk motif
- a strong target-only or graph lead that needs graph overlay, diversification,
  or regime context
- a near-pass that appears limited by breadth rather than expression quality

Weak triggers include "more nodes are always better" and "graph-first means
expanding now." Before expansion, ask whether subset, lag, sign,
transformation, model family, denoise, regime, filter, sizing, or ensemble
search over the current graph-derived universe is the higher-information move.

When expansion is used, keep it local and named. Treat the added neighborhood as
a probe; if it does not improve information density, return to the strongest
current-view construction.

## Avoid Single-Lead Collapse

A strong early model or simple mechanism is a lead, not the whole search. Do not
spend the remaining budget on small refinements unless the result is already
near reportable quality and the next refinement is data-earned. Otherwise build
another materially different graph-derived view or run a target/baseline control
that clarifies graph contribution.

## What Simple Rules Are For

Simple target-only or graph-node rules are useful as:

- baselines and controls
- ablations against a richer candidate
- quick diagnostics of direction, sign, risk, or target-window difficulty
- refinements after an empirical construction finds a promising shape

They are not the default substitute for data-driven search. A branch can be
`graph_supported` because it reads prepared graph inputs and still be a narrow
hand-written mechanism.

## Search Accounting

If the submitted branch was selected from a scan, grid, model comparison, HPO
run, node-subset choice, or feature-factory screen, record the effective width
with `--selection-trials N` or the current candidate search metadata path.
`N` is this round's search width only, never the campaign total.

Do not report a raw search winner as robust until it clears the gauntlet with
honest width accounting.

## Failure Reading

A failed empirical construction says that expression failed. It does not prove
the graph is useless, and it does not prove target-only should take over. Read
metric shape and then choose whether to change model family, subset, lag/sign,
denoise, regime, sizing, another graph-derived view, earned graph expansion, or
target/control comparison.

Before claiming no edge, the ledger should show materially different empirical
search axes, not only a sequence of small hand-written mechanisms.
