---
name: organic-retro
description: "Trigger: orchestrator delegates retro mode after task close, or conventions mode on correction/friction input."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator delegates `organic-retro` after a task's Brief File flips to
`status: done` (Retro trigger, `orchestrator-protocol.md`), or on an explicit request for a
provisional retro against an `active`/`paused` Brief File. Two modes: **`retro`** reads the
injected `brief_file` — the sole delegated skill authorized to read a Brief File — and
composes a per-task retrospective at `report_destination`, grounded entirely in that file's
Plan, Cost Ledger, Phases, and Amendments plus any injected review-report paths; when its own
Frictions section yields a reusable-convention candidate, it also drafts a "Conventions
proposed" section in the same retro file. **`conventions`** is the standalone entry point: from
injected `source_material` (a user correction, or friction text with no Brief File in play) it
composes PROPOSED convention entries returned in the envelope only. Neither mode writes
application code, `CLAUDE.md`, `AGENTS.md`, or any config file — proposals are for the
orchestrator or the user to apply.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Named READ exception (`_shared/persistence-contract.md` → "Brief File ownership"): in `retro` mode, reads the injected `brief_file` — the sole delegated skill authorized to read a Brief File; never writes one, in either mode.
- Metrics are copied verbatim from the Brief File's Cost Ledger — never recomputed, never estimated; a figure the ledger does not already contain is omitted, not guessed.
- Frictions get equal or more space than "What worked" — no self-congratulation padding; every win cites the evidence that proves it (an envelope outcome, a receipt verdict, a specific catch), not an adjective.
- Every claim cites its source — a Brief File section, a `report_destination` path, a `file:line`, or, in `conventions` mode, the injected `source_material` itself — an uncited claim is dropped, not recorded on faith.
- Writes only its own retro file, at the injected `report_destination`, in `retro` mode only — `conventions` mode writes nothing, ever.
- `conventions_proposed` entries are proposals only — this skill NEVER writes `CLAUDE.md`, `AGENTS.md`, or any config file, in either mode; the orchestrator (trivial-floor edit) or the user applies an accepted proposal.
- Read-only auditor otherwise: MUST NOT run state-changing git commands (commit, add, push, reset, stash, rm). No `decisions[]` entry — none exists on this route.

## Decision Gates

| Condition | Action |
|---|---|
| `mode: retro` AND `brief_file` missing from injected context | `status: blocked`, name the missing field. |
| `mode: retro` AND the `brief_file` path is unreadable (does not exist / read fails) | `status: blocked`, cite the attempted path. |
| `mode: retro` AND a path in the injected `review_reports` list is unreadable | Proceed on the remaining evidence; note the unreadable path in `risks` (optional input, never a silent skip). |
| `mode: retro` AND `report_destination` missing from injected context | `status: blocked` — this skill's entire product is that file; there is no fallback record. |
| `mode: conventions` AND `source_material` is absent or empty | `status: needs_input`, ask for the correction text or the friction(s) to draw proposals from. |
| `mode: retro` AND the Brief File's frontmatter `status` is not `done` | `status: warning`; still compose the retro, header prefixed `PROVISIONAL — task not yet closed`. |
| `mode` not one of `retro` / `conventions` | `status: blocked`, "Invalid mode: '{value}'. Expected retro or conventions." |

## Execution Steps

1. Read `_shared/context-protocol.md` (startup sequence) and `_shared/persistence-contract.md` (write rules, plus the Brief File READ exception this skill alone carries — loaded per common-rules Principle 5). Identify `mode` (`retro` | `conventions`) from injected context; validate its required fields (`retro`: `brief_file` + `report_destination`; `conventions`: `source_material`) against the Decision Gates. Report `context_resolution`.
2. `retro`: read the injected `brief_file` in full — frontmatter (`status`, `mode`, dates), `## Plan`, every `## Task Brief` block, `## Phases`, `## Cost Ledger`, `## Amendments`, `## Close`. Missing or unreadable → the matching blocked gate. When a JSON sidecar exists alongside it (`brief_file` with `.md` replaced by `.json`), read the ledger/close figures for Metrics FROM that sidecar — it is the machine-validated source (`_shared/scripts/check-receipt.py ledger`, `orchestrator-protocol.md` → Task Brief → "Brief File structural check"); when it is absent (a legacy Brief File predating the sidecar), fall back to reproducing the `.md` file's `## Cost Ledger` table verbatim, unchanged from before.
3. `retro`: read every path in the injected `review_reports` list (the Cost Ledger's `organic-reviewer`/`organic-security` rows) — optional evidence that deepens "What worked"/"Frictions" citations beyond the ledger alone; a listed path that is unreadable is noted in `risks`, never silently skipped.
4. `retro`: draft the retro content per [references/retro-format.md](references/retro-format.md) — header (task, date, gear/route, result; `PROVISIONAL` prefix when Brief File `status` is not `done`), What worked, Frictions (numbered, equal-or-more space than What worked), Metrics (Cost Ledger reproduced verbatim; re-brief counts grouped by cause), Watch-items. Every claim cites its source.
5. `retro`: scan the drafted Frictions for a reusable-convention candidate — a friction whose proposal is a general rule, not a one-off protocol tweak. For each candidate, draft a `conventions_proposed` entry (rule, why, Good example, Bad example — both evidence-cited — target file+section) and a "Conventions proposed" section for the retro file. Zero candidates → `conventions_proposed: []`, no section drafted.
6. `conventions`: compose one `conventions_proposed` entry per distinct candidate in the injected `source_material` — same shape as step 5. This mode drafts no retro content and writes nothing.
7. `retro`: write the complete retro file (steps 4-5, one atomic write) to `report_destination` per [references/retro-format.md](references/retro-format.md).
8. Compose and return the envelope per Output Contract.

## Output Contract

Writes nothing in `conventions` mode; writes the retro file at the injected
`report_destination` (resolved relative to `project_root`) in `retro` mode only. Returns:

```yaml
status: ok | warning | needs_input | blocked
executive_summary: "1-3 sentences"
mode: retro | conventions
questions: []                    # needs_input only — the concrete questions blocking the pass
artifacts:                       # the retro file entry — present in `retro` mode only
  - { name: "retro", path: "<repo-relative path>" }
conventions_proposed:            # CAP 10 entries — [] when no candidate surfaced
  - { rule: "<one line>", why: "<one line>", good_example: "<evidence-cited>", bad_example: "<evidence-cited>", target: "<file#section>" }
proposals_omitted: 0             # >0 only when the cap was hit
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: self-loaded | fallback | none
```

## References

- [references/retro-format.md](references/retro-format.md) — full retro template (header/what-worked/frictions/metrics/watch-items) and the conventions-proposal shape, with a compact worked example; load when drafting either mode's output.
- [references/envelope-examples.md](references/envelope-examples.md) — envelope examples per mode (retro and conventions, success and non-happy-path); load when composing the result.
- `../_shared/context-protocol.md` — startup sequence; load first.
- `../_shared/persistence-contract.md` — write rules and the Brief File READ exception (loaded per common-rules Principle 5).
- `../_shared/common-rules.md` — consolidated principles (read-only, write-scope, envelope-always, seniority); load at startup.
- `../_shared/result-envelope.md` — base envelope field vocabulary.
- `../_shared/evidence-protocol.md` — Rule 1 (every claim backed by a citation).
- `../_shared/orchestrator-protocol.md` — naming exactly one section: **Retro trigger** (when/why this skill is delegated, and the `retro:` config semantics); load when the trigger context is unclear.
