# Graph Frontier Protocol

Use this reference after workspace preflight is complete.

## Purpose

The graph frontier answers one question:

Which causal graph nodes are currently known, and where can the agent widen the
search next?

It does not define the branch runtime by itself. Frontier expansion widens the
candidate node pool through CAP without pretending to pre-solve the strategy.

Live graph discovery is the normal session opening:

```bash
abel-invest init-session --ticker <TICKER> --exp-id <exp-id>
```

Use an explicit no-discovery fallback only when auth, service access, or
continuity constraints make live graph discovery unavailable:

```bash
abel-invest init-session --ticker <TICKER> --exp-id <exp-id> --no-discover
```

## Session Model

The session owns:

- `graph_frontier.json`: current graph node frontier and expansion provenance
- `readiness.json`: advisory coverage report
- `research_journal.md`: agent-owned research state
- `frontier.md`: factual exploration coverage

The branch then selects graph node inputs from that session context in
`branch.yaml`. The evidence ledger later records declared, prepared, and actual
graph node read facts.

## Priority Order

Graph-first is a research priority, not a mechanical quota:

1. causal graph structure and input hypotheses
2. strategy/mechanism variants
3. parameter, threshold, filter, sizing, and window refinement

Direct parents are an opening clue, not a guarantee that the final branch should
stay direct-only. If the first candidates look odd, do not discard them just
because they are obscure or low-attention; explain them before moving on.

CAP graph nodes are causal priors, not trading instructions. They do not give
the trading sign, lag, direction, or a monotone strength map. Depth matters:
deeper nodes should be treated as weaker or more indirect priors unless
recorded evidence or domain context justifies a deeper branch.

## Practical Expansion

Use this as a search prior, not a hard recipe:

1. direct parents
2. other Markov blanket nodes, with `parents > children > spouses/co-parents`
3. children-derived hop-2 candidates
4. sector, market, or crypto peers only when they add a real mechanism

When current evidence leaves a frontier question unresolved, expand the graph
itself before spending rounds on strategy variants:

```bash
abel-invest frontier status --session research/<ticker>/<exp_id>
abel-invest frontier expand --session research/<ticker>/<exp_id> --anchor <NODE_ID> --mode all --limit 20
```

Use `--mode parents`, `--mode mb`, or `--mode all` according to the causal
question. The result is new or updated nodes in `graph_frontier.json`, not a
recommendation to run a specific branch.

Good expansion reasons include a missing liquidity, supply-chain, market-state,
or demand-regime motif; current-frontier availability or input-realization
limits; or user/narrative context that names a plausible real-world mechanism
outside the current frontier. Weak reasons include "the last branch failed",
"graph breadth is always good", or "a local metric scan found one attractive
node, so expand around it until the result improves".

## Narrative Scout

Abel Ask and narrative context can improve exploration efficiency by generating
mechanism hypotheses before another branch cut or graph expansion. Use them to
ask what industry, demand, supply-chain, liquidity, macro, volume, or peer
mechanism could make a graph neighborhood matter.

Narrative scout work can suggest:

- a supplemental driver to test
- a graph expansion anchor
- a sign, lag, or regime question
- a reason to stop exploring a weak mechanism family

It is not validation evidence and it does not override CAP facts or Edge
results. If the narrative result is off-target or weak, record that plainly.

Efficient pattern:

```text
ledger/frontier facts -> narrative scout for mechanism context ->
frontier question -> optional CAP expansion or branch cut
```

Inefficient pattern:

```text
weak metric result -> expand graph broadly -> search new nodes for a metric win
```

## Branch Cut

When moving from discovery into a branch:

- choose a small explicit graph node input set
- write it into `branch.yaml` as structured `selected_inputs`
- use readiness to understand coverage, not to auto-ban ideas
- run `prepare-branch` before a recorded round
- after the round, check input realization facts before treating a declared
  graph-supported branch as graph-supported evidence

```yaml
selected_inputs:
  - node_id: AAPL.price
    role: graph_input
    source: frontier
  - node_id: SPY.volume
    role: control
    source: external
    source_reason: market-liquidity contrast outside the current frontier
```

Readiness is advisory. Do not collapse every branch onto the latest common start
unless the branch thesis truly requires strict overlap.
