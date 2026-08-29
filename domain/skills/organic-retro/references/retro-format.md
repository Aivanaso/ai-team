# Retro Format

The template `organic-retro` (`retro` mode) fills in when composing the retro file at the
injected `report_destination` — convention `.ai-team/retros/YYYY-MM-DD-<slug>.md`, the same
slug as the task's Brief File at `.ai-team/briefs/YYYY-MM-DD-<slug>.md`. Every section is
evidence, not memory: a claim with no citable source (Brief File section, receipt/report
path, or `file:line`) does not go in.

## Header

```markdown
# Retro — {task title, from the Brief File frontmatter's `task:`}

**Date**: {current_iso_utc date}
**Route**: {Brief File frontmatter `mode:` gear — normal | fast-forward | unattended}
**Result**: {status: done | PROVISIONAL — task not yet closed} — {one-line outcome, from the
Brief File's `## Close` section: commit hash(es), totals}
```

When the Brief File's frontmatter `status` is not `done` (Decision Gates warning row), prefix
**Result** with `PROVISIONAL — task not yet closed` instead of reading `## Close` (it is not
written yet).

## What worked

- One item per grounded win — an envelope outcome, a receipt verdict, a specific catch (a
  scope-large gate that stopped a bad write, a review finding closed pre-commit, a
  construction-site sweep that found a live caller before it broke).
- 1 short paragraph each, citing its evidence: `Cost Ledger row N`, `.ai-team/reviews/<file>
  finding F-N`, or a named Task Brief element.
- No adjective without a citation — "worked well" is not a claim, "review-clear on the first
  pass, Cost Ledger row 3" is.

## Frictions

- **Equal or more space than "What worked" — never a token afterthought.** This section is
  where the retro earns its keep.
- Numbered (F1, F2, ...) so "Watch-items" can reference them.
- Each friction: what happened (cited to a Cost Ledger row, a receipt finding id, or
  `file:line`) → why it cost time or quality → one concrete proposal (a protocol change, a
  config default, a convention entry).

## Metrics

- Reproduce the Brief File's `## Cost Ledger` table **verbatim** — same columns (`#, agent,
  model, tokens, tool_uses, duration, outcome`). Never recompute or estimate a figure the
  ledger did not already record. When the Brief File's `.json` sidecar exists (`brief_file`
  with `.md` replaced by `.json`), source these figures from its `ledger`/`close` fields
  instead — the machine-validated copy (`_shared/result-envelope.md` → "Brief File Ledger JSON
  sidecar") — and render them into this same table shape; a Brief File with no sidecar (legacy)
  falls back to reading the `.md` table directly, unchanged from before.
- **Re-brief count**: count `outcome` cells that are a re-delegation for the same objective
  (a fresh `organic-implementer` row following a `review-blocked`/`needs_input`/`blocked`
  row), grouped by cause (review-blocked finding, needs_input, blocked/scope-large, infra-death, amendment
  request).
- **Inline-closure count**: when the Brief File's `.json` sidecar exists, source this figure
  from `close.inline_closures` (its entry count — `_shared/result-envelope.md` → "Brief File
  Ledger JSON sidecar"), the same machine-validated field the Metrics table above draws from.
  When no sidecar exists (legacy Brief File, written before this field existed), render the
  figure as "inline closures: not recorded in the ledger sidecar" and nothing else — never
  estimate it by counting mentions in the `.md` Brief File's `## Amendments` prose.
  `## Close` never prescribed recording inline closures, and neither did any protocol
  section, so a legacy Brief File's `## Amendments` narrative is prose, not a ledger figure —
  `organic-retro/SKILL.md`'s own rule against estimating applies here exactly as everywhere
  else in this file.
- **Plan size and completion**: when the sidecar carries `plan` (`_shared/result-envelope.md` →
  Brief File Ledger JSON sidecar), render "plan: N briefs, M done" from its entries; when the
  sidecar exists but has no `plan`, or no sidecar exists, render "plan: not recorded in the
  ledger sidecar" and nothing else — never estimate it from the `.md` `## Plan` prose.
- **Totals**: sum only the ledger's own token/duration/agent-count columns.

## Watch-items for the next task

- One line per item, phrased as a question the *next* retro should answer — mirrors "did F3
  happen again?" rather than a flat statement. Tie back to a friction number when applicable.
- Example: `"F2 — did the citation audit run this time, or did the reviewer return
  artifacts: [] again?"`

## Conventions proposed (drafted by `retro` mode when a friction yields a candidate)

One entry per candidate, same shape `conventions_proposed` returns in the envelope:

```markdown
### Proposed: {rule, one line}

**Why**: {one line — the friction or cost this closes}
**Good**: {evidence-cited example — a `file:line` or a hypothetical the project's own
conventions would produce}
**Bad**: {evidence-cited counter-example — what actually happened, cited to the friction}
**Target**: {file}#{section} — where this rule should land (e.g. `CLAUDE.md#Git`,
`AGENTS.md#Testing`)
```

Omit this section entirely when no friction yielded a reusable-convention candidate this run
(Decision Gates: `conventions_proposed: []`).

---

## Compact example

```markdown
# Retro — billing-export endpoint

**Date**: 2026-08-19
**Route**: normal
**Result**: done — commit a1b2c3d (Cost Ledger row 4, work-unit-commits)

## What worked

**1. The scope-large gate caught a cross-module leak before it landed.** The first
`organic-implementer` pass (Cost Ledger row 1) returned `status: blocked`,
`scope_report.kind: scope-large` when the export objective needed the tax module's rounding
helper — a file `expected_files` never declared. The orchestrator widened the brief instead of
letting the worker improvise (Cost Ledger row 1, `scope_report.target:
services/billing/tax.py`).

## Frictions

**F1 — the tier-1 review re-ran a check the acceptance_checks already covered.**
`organic-reviewer` (Cost Ledger row 3, 88,000 tokens) re-ran the full test suite even though
`acceptance_checks` already declared the same command — a redundant verification step folded
into that pass's own token count, not a separate delegation.
**Proposal**: `organic-reviewer`'s verification step should skip a re-run when
`acceptance_checks` already covers the same command verbatim (see
`organic-reviewer/SKILL.md` Step 4).

## Metrics

| # | agent | model | tokens | tool_uses | duration | outcome |
|---|---|---|---|---|---|---|
| 1 | organic-implementer | sonnet | 95,000 | 30 | 5m10s | blocked — scope-large |
| 2 | organic-implementer (re-brief) | sonnet | 110,000 | 38 | 6m40s | ok — 4 files, 2/2 checks |
| 3 | organic-reviewer (tier 1) | opus | 88,000 | 22 | 7m05s | review-clear — 0 findings |
| 4 | work-unit-commits | sonnet | 30,000 | 12 | 1m20s | ok — commit a1b2c3d |

Re-brief count: 1 (cause: scope-large, F1 not implicated).

## Watch-items for the next task

1. Does `organic-reviewer` still re-run a check `acceptance_checks` already covered (F1)?

## Conventions proposed

### Proposed: declare cross-module dependencies in the objective, not just expected_files

**Why**: the tax-module dependency was knowable at brief-authoring time (the export endpoint
always rounds via the shared helper) but only surfaced as a scope-large gate mid-run.
**Good**: `objective: "...export totals, rounding via services/billing/tax.py's shared
helper"` names the dependency up front.
**Bad**: the original brief's `objective` named only the endpoint; the rounding dependency
surfaced only in `scope_report.target` (Cost Ledger row 1).
**Target**: `orchestrator-protocol.md#Task Brief` — note under the objective element.
```
