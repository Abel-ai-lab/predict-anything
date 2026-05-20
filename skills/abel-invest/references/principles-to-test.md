# Empirical Alpha Construction Notes

Use this reference when the current candidate search needs broader empirical
construction rather than another single hand-designed rule.

These notes are not a separate workflow. They describe normal Abel Invest alpha
search moves. Runtime legality, honest search-width accounting, and final
validation still own what can be reported.

## Feature-Factory And Ensemble Search

Abel Invest should treat machine feature factories, heterogeneous ensembles, and
strong empirical ML practice as first-class tools.

Useful search moves include:

- deterministic feature factories over target and graph-derived fields
- lag, sign, transformation, ratio, difference, and rolling-window generation
- graph-node subset search instead of mandatory full-frontier baskets
- weak standalone signals retained as possible ensemble members
- diversity-aware member selection
- model-family comparison, including linear, tree, GBDT, and hybrid models
- supervised target/graph hybrid models when the label and horizon are legal
- unsupervised denoise such as PCA/ICA/autoencoder-style compression when it is
  temporally legal and width-accounted
- HPO or parameter search when the submitted candidate records the effective
  search width
- regime, sizing, and filter search layered on otherwise weak alpha signals

Why this matters:

- the graph supplies a high-value feature universe, but the tradable expression
  may live in a subset, lag, transformation, regime, or ensemble interaction
- target-only baselines can be strong, so graph-derived candidates should be
  judged by their marginal contribution rather than by graph membership alone
- target-only should still remain a benchmark, seed, or ablation rather than the
  default substitute for live graph search
- a single hand-written mechanism can miss weak but durable combined signals

Guardrails:

- do not use information unavailable at decision time
- do not search an unbounded feature universe unless the user explicitly asks
  for that scope
- do not report a raw search winner as robust until it clears the gauntlet
- record search width through `--selection-trials` or the current candidate
  search metadata path
- keep graph role explanations provisional until a candidate has evidence worth
  explaining
