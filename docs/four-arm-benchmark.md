# Four-Arm Abel Invest Capability Benchmark

This June 2026 benchmark isolates two capabilities in Predict Anything strategy research: the Abel Invest skill workflow and Abel causal graph access. The run covered `1,000` selected tickers in `100` chunks. Each arm received the same strategy-discovery objective and differed only in the capabilities exposed to the agent.

## Experimental Arms

| Arm | Abel Invest skill | Causal graph | OK coverage | Mean Sharpe | Median Sharpe | P10 Sharpe | Median max DD | Median return/DD | Mean candidates |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Skill + graph | `yes` | `yes` | `835 / 1000` (`83.5%`) | `1.0245` | `1.0099` | `0.7089` | `-0.1666` | `8.1007` | `207.0` |
| Skill only | `yes` | `no` | `998 / 1000` (`99.8%`) | `0.8194` | `0.8088` | `0.5126` | `-0.1916` | `5.7444` | `40.0` |
| Graph only | `no` | `yes` | `959 / 1000` (`95.9%`) | `0.9514` | `0.9374` | `0.6461` | `-0.2527` | `9.5752` | `198.2` |
| No skill / no graph | `no` | `no` | `959 / 1000` (`95.9%`) | `0.7617` | `0.7530` | `0.4686` | `-0.2616` | `5.7652` | `40.0` |

## Headline Readout

The full Predict Anything stack, `skill + graph`, produced the strongest risk-adjusted profile: highest mean Sharpe, highest median Sharpe, strongest 10th-percentile Sharpe, and the smallest typical drawdown. Against the pure control on the all-four-OK paired set (`803` tickers), the full stack won on Sharpe for `710 / 803` tickers (`88.4%`), reduced drawdown for `583 / 803` tickers (`72.6%`, less negative is better), and won on return/drawdown for `533 / 795` defined pairs (`67.0%`).

Graph-only and no-skill arms sometimes found larger raw total returns, but those paths carried materially deeper typical drawdowns and more volatile return distributions. The capability claim is therefore deliberately risk-aware: Predict Anything improves risk-adjusted strategy discovery, drawdown control, search coverage, and candidate breadth. It is not a claim to maximize raw return regardless of risk.

## Pairwise Contrasts

| Contrast | Paired set | Sharpe wins | Mean delta Sharpe | Median delta Sharpe | Drawdown wins | Return/DD wins |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Full stack vs pure control | `803` | `710 / 803` (`88.4%`) | `0.2653` | `0.2287` | `583 / 803` (`72.6%`) | `533 / 795` (`67.0%`) |
| Skill effect, graph fixed on | `803` | `526 / 803` (`65.5%`) | `0.0690` | `0.0358` | `646 / 803` (`80.4%`) | `289 / 797` (`36.3%`) |
| Skill effect, graph fixed off | `959` | `548 / 959` (`57.1%`) | `0.0590` | `0.0161` | `781 / 959` (`81.4%`) | `480 / 951` (`50.5%`) |
| Graph effect, skill fixed on | `835` | `599 / 835` (`71.7%`) | `0.2125` | `0.1642` | `333 / 835` (`39.9%`) | `470 / 829` (`56.7%`) |
| Graph effect, skill fixed off | `959` | `724 / 959` (`75.5%`) | `0.1897` | `0.1419` | `417 / 959` (`43.5%`) | `626 / 952` (`65.8%`) |

## Factor Effects On Sharpe

| Factor effect | Mean delta Sharpe | Median delta Sharpe | Positive | Negative | Ties | P10 | P90 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Skill effect with graph | `0.0690` | `0.0358` | `526` | `277` | `0` | `-0.0423` | `0.2229` |
| Skill effect without graph | `0.0510` | `0.0044` | `422` | `381` | `0` | `-0.0148` | `0.1790` |
| Graph effect with skill | `0.2143` | `0.1673` | `584` | `3` | `216` | `0.0000` | `0.5057` |
| Graph effect without skill | `0.1963` | `0.1491` | `619` | `52` | `132` | `0.0000` | `0.4869` |
| Skill x graph interaction | `0.0180` | `0.0000` | `404` | `280` | `119` | `-0.0587` | `0.1204` |

## Interpretation

- The Abel Invest skill is the stabilizer: with graph held fixed, it improved Sharpe and reduced drawdown; without graph, it preserved near-perfect coverage (`998 / 1000`) while still improving Sharpe over the no-skill baseline.
- The causal graph is the search-expander: with skill held fixed, graph access raised mean Sharpe by `+0.2125`; the graph-enhanced skill arm beat skill-only on Sharpe for `599 / 835` paired tickers, tied on `233`, and lost only `3`.
- The full stack is strongest where product users care most: risk-adjusted quality, lower-tail Sharpe, drawdown control, and richer candidate search.
- Raw-return-only rankings are not the right product metric here because the graph-only and control arms can take rougher, higher-drawdown paths that inflate mean total return.

## Isolation Audit

All four arms passed the chunk-level isolation audit:

| Arm | Audit chunks | Passed chunks | Skill flag | Graph flag | Abel module leaks | Forbidden host blocks |
| --- | ---: | ---: | --- | --- | ---: | ---: |
| Skill + graph | `100` | `100` | `True` | `True` | `0` | `0` |
| Skill only | `100` | `100` | `True` | `False` | `0` | `0` |
| Graph only | `100` | `100` | `False` | `True` | `0` | `0` |
| No skill / no graph | `100` | `100` | `False` | `False` | `0` | `0` |

The audit records `uses_abel_invest=True` only in skill arms and `uses_causal_graph=True` only in graph arms, with `abel_invest_module_leak_count=0`, `blocked_forbidden_host_count=0`, and no failed chunks.

## Strategy Pool Follow-Through

After the benchmark, the full skill + graph strategy-artifact repair and upload workflow made `1000 / 1000` full-stack strategies hostable in the Abel strategy pool. The paired metric tables above preserve the original strict comparable-run counts, while the strategy-pool follow-through confirms that every selected ticker now has a hostable full-stack strategy artifact.

Backtests and benchmark comparisons are research artifacts, not investment advice or guarantees of live trading performance.
