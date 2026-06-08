# trade-anything — Rebrand + SEO/GEO Proposal

Branch: `feat/trade-anything-rebrand` (cut from `develop` per `AGENTS.md`).
Constraint honored: **all numbers and facts unchanged** — only framing, structure, and metadata changed. No version bumps, no CHANGELOG edits (feature-branch policy).

## Positioning decision

`trade anything` names **a capability the user wields** — point an AI agent at any market, any ticker, any thesis and get back a researched, Sharpe-screened strategy. It is **not** a claim that the software places orders for you. So the brand leads at full confidence; the accurate scope ("researches/validates and hands off for paper tracking; does not place trades, automate execution, or provide a backtesting engine; directional evidence, not investment advice") lives as **one plain line + one FAQ answer**, never as a caveat banner.

**Category noun:** *Causal Trading-Strategy Research Engine for AI Agents* (names the job, not the architecture; survives LLM paraphrase; front-loads target queries).

## What changed on this branch (already written, uncommitted)

| File | Change |
| --- | --- |
| `README.md` | Full GTM rewrite: keyword-front-loaded H1, capability opening, benchmark surfaced high as the hero proof, question-shaped section headings, a real FAQ, entity/skill table with versions. Benchmark table + scope line + install commands spliced **verbatim** (URLs repointed to `trade-anything`). |
| `llms.txt` (new) | GEO crawler record (emerging standard): one-line summary, what-it-is, scope, supported agents, four-skill entity rows w/ versions, full benchmark w/ inline dates + scope clause, canonical links. |
| `skills/abel-invest/pyproject.toml` | `description` + `keywords` enriched for package/PyPI discovery (no version change). |
| `skills/abel/SKILL.md`, `skills/abel-ask/SKILL.md` | `metadata.openclaw.homepage` URL repointed to `trade-anything`. (Routing `description` fields deliberately untouched.) |

## SEO surface (GitHub search + Google)

**GitHub "About" blurb** (set in repo settings; 349/350 chars):
> AI agent skills for causal trading-strategy research. Point Claude Code, Codex, OpenCode, or ClawHub at any ticker or market question — discover causal alpha drivers, generate strategy hypotheses, screen for high Sharpe & low drawdown, validate through Abel Edge gates. Benchmarked at 3.57x mean Sharpe vs an LLM-only workflow across 1,000 tickers (directional evidence). Research + paper tracking, not order execution.

**GitHub Topics** (20, set in repo settings):
`ai-trading`, `trading-strategy`, `causal-ai`, `quant`, `algorithmic-trading`, `claude-code`, `claude-skills`, `openai-codex`, `ai-agent`, `llm-agent`, `agentic-ai`, `agentic-quant`, `sharpe-ratio`, `alpha-research`, `causal-graph`, `causal-inference`, `strategy-discovery`, `quantitative-finance`, `opencode`, `investment-research`

> Deliberately **dropped** `mcp` (zero MCP refs in repo) and `backtesting`/`trading-bot` (docs state "not a backtesting engine" and the brand must not imply order execution) — tagging those would be a self-contradicted discoverability claim.

Other SEO levers in the README: query-shaped H2s ("How is it different from a normal LLM picking stocks?"), image alt text on badges, internal anchor links, brand + category tokens in the first 100 words.

## GEO surface (LLM / AI-search citation — ChatGPT, Claude, Perplexity, AI Overviews)

- `llms.txt` gives crawlers a clean, un-styled entity record.
- FAQ entries are phrased as the exact questions users type; each answer is self-contained.
- Every liftable statistic carries its scope clause **in the same sentence** ("directional capability evidence, not investment advice" / "1,000-ticker window") so a truncating summarizer can never cite a bare `3.57x` as a performance guarantee.
- Clean entity definitions (trade-anything vs Abel vs the four skills) and a dedicated FAQ that keeps the *Sharpe>2 aspirational target* distinct from the *0.8245 realized benchmark mean*.

## Social preview (regenerate `docs/assets/social-preview.{svg,png}`)

- Headline: **"trade anything. Point an AI agent at any ticker, get a Sharpe-screened strategy."**
- Subhead: "Causal trading-strategy research engine for AI agents — 3.57x mean Sharpe vs an LLM-only workflow across 1,000 tickers (directional evidence, not investment advice). Claude Code · Codex · OpenCode · ClawHub."

## Actions only you can take (GitHub-side)

1. Rename the repo from the previous slug to `trade-anything` (Settings → General). GitHub auto-redirects old web/git/raw URLs.
2. Paste the **About** blurb above into the repo description.
3. Add the 20 **Topics** above.
4. Regenerate and upload the **social preview** image with the new headline/subhead.

## Remaining in-repo rename sweep (NOT yet done — needs a coordinated pass + test run)

These still reference the old slug/name and should be updated in a follow-up (some are functional pipeline files and tests that must pass after the change):

- **Install docs / URLs:** `.claude/INSTALL.md`, `.codex/INSTALL.md`, `.opencode/INSTALL.md`, `docs/README.claude.md`, `docs/README.codex.md`, `docs/README.opencode.md` (raw.githubusercontent URLs + display name).
- **Docs:** `docs/strategy-research.md`, `docs/releases.md`, `docs/developer-builds.md`, `docs/collection-migration/inventory.md`, `clawhub/README.md`, `CONTRIBUTING.md`, `SECURITY.md`.
- **Build/release pipeline (verify tests after):** `scripts/build_clawhub_release.py`, `scripts/check_pr_release_policy.py`, `tests/test_build_clawhub_release.py`, `tests/test_publish_clawhub_release.py`.
- **Policy:** `AGENTS.md` (one slug reference).
- **Asset source:** `docs/assets/social-preview.svg` (display name text).

> The README + llms.txt historical "Formerly..." / migration references to the old slug are **intentional** (entity-continuity for SEO/GEO + migration), and should stay.

## Verbatim-preserved facts (audited byte-identical)

Benchmark table (all 8 rows + coverage), the both-OK win-rates (98.3% / 84.7% / 79.3% / 92.0%), 10th-pct Sharpe (+0.5174 vs −0.2719), the directional-evidence disclaimer, all install commands, the migration command, and skill versions (abel 1.4.3, abel-ask 1.1.6, abel-invest 3.7.2, abel-edge ≥0.8.9,<0.9.0; abel-auth unversioned).
