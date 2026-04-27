# Discovery Protocol

This document assumes the workspace root has already been identified correctly:

- if `./alpha.workspace.yaml` exists, the current directory is already the workspace root
- else if `./abel-alpha-workspace/alpha.workspace.yaml` exists, reuse that child workspace
- only if neither manifest exists should you bootstrap a new workspace

Do not infer "missing workspace" by checking only for `./abel-alpha-workspace/`.

## Purpose

Discovery answers one question only:

Which causal candidates are worth considering for this session?

It does not define the branch runtime by itself.
Direct parents are the default opening, not a guarantee that the final branch
should stay direct-only.
Discovery should widen the search space without pretending to pre-solve the
strategy.
Live discovery is the normal session opening. Use an explicit no-discovery
fallback only when auth, service access, or continuity constraints make live
graph discovery unavailable.

## Session Model

After live discovery, the session owns:

- `discovery.json`: candidate snapshot
- `readiness.json`: advisory coverage report

The branch then selects from that session context in `branch.yaml`.

## Practical Search Order

Use this as a priority order, not a hard formula:

1. direct parents
2. other Markov blanket nodes, with `parents > children > spouses/co-parents`
3. children-derived hop-2 candidates
4. sector or market peers only when they add a real mechanism

The spirit is simple: start close to the target, then widen only when the
branch thesis earns that extra breadth.
If the first candidates look odd, do not discard them just because they are
small, obscure, or low-attention. Strange parents are often the point of causal
discovery.

## Branch Cut

When moving from session discovery into a branch:

- choose a small initial driver set
- write it explicitly into `branch.yaml`
- use readiness to understand coverage, not to auto-ban ideas
- run `prepare-branch` before a recorded round

## Readiness Role

Readiness is advisory.

Use it to answer:

- how early target data is observed
- which discovery tickers have partial or stronger coverage
- whether strict overlap is likely expensive
- whether the session default start and a branch's explicit start are meaningfully different

Do not use it to collapse every branch onto the latest common start unless the
branch really depends on strict overlap.

## Optional Expansion Heuristics

Discovery should stay open-ended, but the branch cut should stay small.

- start from direct parents and the strongest blanket nodes
- if the first branch feels too narrow, expand through children-derived hop-2 candidates
- add sector, market, or crypto peers only when you can explain the transmission mechanism
- treat peers as supplements, not as a replacement for causal candidates
- do not confuse "more candidates" with "more evidence"; the job is to surface promising mechanisms, not to collect a giant static universe

These are research heuristics. They do not change the session artifact contract,
and they do not mean every branch should use all tiers.

## Cache Role

Discovery does not own market data.

Prepared branch inputs should resolve through the edge-owned cache path, not
through ad hoc branch-local fetching conventions.
