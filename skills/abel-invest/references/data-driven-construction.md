# Data-Driven Construction

Use this reference for ordinary non-grandma alpha search, especially before the
first serious candidate lane, after a simple baseline, or when the next idea is
another hand-written rule.

This is the default construction stance, not a separate workflow. Runtime
legality, honest search-width accounting, and validation still decide what can
be reported.

## Default Engine

Build candidates by empirical construction over a bounded universe:

- target history and any validated baseline or catalog strategy
- live graph nodes and graph-derived feeds when available
- selected supplemental cross-asset, volume, liquidity, sector, or regime feeds
  when evidence or the user goal justifies them

The graph bounds and enriches the alpha universe. It does not prescribe one
tradable basket, and it is not satisfied by placing a few nodes into a simple
hand-written rule.

## First Serious Lane

For normal alpha search, the first serious lane should be one of these empirical
constructions:

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
denoise, regime, sizing, graph expansion, or target/control comparison.

Before claiming no edge, the ledger should show materially different empirical
search axes, not only a sequence of small hand-written mechanisms.
