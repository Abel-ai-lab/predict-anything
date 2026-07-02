# Proven Patterns - Candidate Shapes, Not Recipes

Use this reference as a compact pattern catalog during EXPLORE mode. These
patterns are evidence of what has worked on some assets, not instructions for
the current target.

Local data decides whether a pattern, parameter range, model family, graph-node
subset, lag, sign, transform, filter, or sizing rule deserves recorded
validation. If a pattern inspires a scan, record the effective search width for
the submitted candidate.

Runtime legality lives in `constraints.md`; loop sequencing and final-report
boundaries live in `experiment-loop.md`. Do not treat pattern-specific lags,
weights, metrics, or causal pairs as currently disclosed CAP fields.

## How To Use

- Start from the candidate shape, then adapt it to the current target and graph
  universe.
- Treat prior metrics as historical examples only.
- Keep all live features shifted before decision time.
- Use `debug-branch` before trusting any recorded round.
- Watch the validation triangle: high Sharpe without IC, DSR, or stability can
  be concentration or search-width gaming.

## Pattern Catalog

### Dual-Lag Xcorr

Average two shifted rolling cross-correlations instead of betting on one exact
lag. Useful when graph or scout evidence suggests a parent signal has multiple
temporal harmonics.

Trap: rolling correlation at index `i` can include target return `i`; shift the
finished correlation before using it. Thresholds such as expanding medians also
need to be shifted.

### Binary Threshold

Convert a continuous signal into a clear above/below-threshold exposure
multiplier. This can differentiate signal regimes more strongly than a smooth
z-score map.

Trap: the best raw Sharpe threshold can collapse IC or stability. Cap final
positions and validate the triangle, not only Sharpe.

### Simple Trend Filter

Use prior close versus prior SMA as a long/flat risk filter. The value is often
regularization: a simple fixed window can beat adaptive filters that add search
width and overfit.

Trap: compare `close.shift(1)` to `sma.shift(1)`, not today's close to today's
rolling mean.

### Position Persistence Penalty

Reduce exposure as a holding streak ages, using only yesterday's held position
to compute the streak. This can reduce serial PnL autocorrelation and improve
Lo-adjusted behavior.

Trap: using today's position to compute today's holding count is circular.

### RSI Contrarian Overlay

Use shifted RSI as a sizing overlay: reduce exposure after overbought streaks
and increase exposure after oversold conditions. It works best as an overlay,
not as a generic model feature.

Trap: RSI at index `i` includes close `i`; shift it before sizing.

### Multi-Horizon Model Ensemble

Train separate models for several forward-return horizons and combine them.
Each horizon can capture a different causal timescale.

Trap: targets may use `returns.shift(-H)` inside training, but all features
must be lagged by at least one bar. Re-search horizon weights per target; do
not copy another asset's weights.

### Cross-Asset Spread

Use relative momentum, spread, ratio, or sector/peer contrast when the graph,
market structure, or scout evidence suggests cross-asset information matters.
Treat it as a supplement unless graph realization and validation support a
stronger claim.

Trap: rolling peer returns include today's return unless shifted.

### Vote-Squared Sizing

For an ensemble, size by squared vote fraction so near-unanimous agreement gets
meaningfully more exposure and split votes stay small.

Trap: every component vote must be based on shifted features. One leaky member
can contaminate the amplified aggregate vote.

## Common Failure Modes

- Copying historical parameters instead of re-searching for the current target.
- Treating a graph read as proof that graph-derived search happened.
- Adding filters, model families, or ensemble members without accounting for
  the search width they introduced.
- Optimizing the scout's local metric while ignoring Edge execution semantics.
- Claiming that one failed expression disproves a graph node or pattern family.
