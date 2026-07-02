# Graph-Informed Alpha Context

Use this reference after workspace preflight when live graph discovery,
graph-derived feeds, or frontier expansion are relevant.

The graph frontier answers one product question: which causal graph nodes are
currently known, and how can they enrich the alpha universe? It is a feature
universe and provenance surface, not a branch recommendation or a requirement
to trade the whole frontier as one basket.

## Session Opening

Live graph discovery is the normal session opening:

```bash
<command_prefix> init-session --ticker <TICKER> --exp-id <exp-id>
```

Use an explicit no-discovery fallback only when auth, service access, or
continuity constraints make live discovery unavailable:

```bash
<command_prefix> init-session --ticker <TICKER> --exp-id <exp-id> --no-discover
```

## Session Artifacts

- `graph_frontier.json`: graph node universe and expansion provenance
- `readiness.json`: advisory coverage report
- `frontier.md`: compact factual search-context coverage
- `exploration_path.md`: chosen path, reason, and Edge feedback log

Branches select inputs from this session context in `branch.yaml`. The evidence
ledger later records declared, prepared, and actual graph node read facts.

## CAP Role Interpretation

CAP graph nodes are model-supported causal priors, not trading instructions.
Trust that they may carry target-relevant information, but do not infer
disclosed weight, exact lag, signed effect, or tradable direction from the role.

CAP graph roles expose causal-flow orientation when specific enough:

- `parent`: upstream of the target, `parent -> target`
- `child`: downstream of the target, `target -> child`
- `blanket`: Markov-blanket discovery bucket/provenance label; not synonymous
  with `spouse` and not a single causal-flow direction by itself

The underlying graph is temporal, so treat relevance as lag-mediated rather
than contemporaneous by default. Candidate search can test lag, sign,
transformation, model family, filter, sizing, and ensemble roles.

## Practical Use

Graph context can shape:

- feature factories over target plus graph feeds
- graph node subset search
- lag, sign, ratio, spread, rolling-window, volatility, and regime transforms
- linear, tree, ensemble, learned, or hybrid model comparisons
- alpha core, confirmation, filter, sizing, or regime roles
- diverse weak signals inside an ensemble

Target-only candidates remain useful baselines, seeds, ablations, and
competitors. They should make graph-derived marginal contribution visible, not
replace graph search when live candidates exist.

## Frontier Expansion

Do not expand the graph merely to satisfy coverage. Expand when it helps the
empirical search question:

```bash
<command_prefix> frontier status --session research/<ticker>/<exp_id>
<command_prefix> frontier expand --session research/<ticker>/<exp_id> --anchor <NODE_ID> --mode all --limit 20
```

Use `--mode parents`, `--mode blanket`, or `--mode all` according to the
candidate-universe question. The result is updated graph context, not a
recommendation to run a specific branch.

Good expansion reasons:

- missing motifs or driver families
- availability or input-realization limits
- user context that points to an external driver
- evidence that the current frontier has been usefully exhausted

Weak reasons:

- more graph nodes are always better
- the product expects graph coverage
- a single failed graph expression means the current frontier is empty

Before expanding farther, ask whether current graph nodes still have useful
subset, lag, sign, transform, model-family, regime, or sizing search left.

## Narrative Scout

Narrative context can improve search efficiency by suggesting candidate
features, supplemental drivers, expansion anchors, or interpretation. It is not
validation evidence and does not override CAP facts or Edge results.

Efficient pattern:

```text
ledger/frontier facts -> candidate universe question -> optional narrative scout -> branch/search
```

Avoid expanding broadly after a weak metric result only because coverage feels
thin.

## Branch Cut

When moving from graph context into a branch:

- choose inputs that match the candidate search question
- write selected runtime inputs into `branch.yaml`
- keep graph attribution lightweight before validation unless making a specific
  graph claim
- use readiness as coverage context, not an automatic veto
- run `prepare-branch` before recorded evidence
- check input realization before treating declared `graph_supported` evidence
  as graph-derived evidence

```yaml
selected_inputs:
  - node_id: AAPL.price
    role: graph_input
    source: frontier
  - node_id: SPY.volume
    role: supplement
    source: external
    source_reason: market-liquidity contrast outside the current frontier
```

Do not collapse every branch onto the latest common start unless the candidate
expression truly requires strict overlap.
