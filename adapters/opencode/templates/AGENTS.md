# ai-team -- OpenCode Orchestrator

> OpenCode acts as the orchestrator. Execution is delegated by default at every task size; review is evidence-tiered, decided from the diff after a candidate exists.

## User Override (absolute priority)

The user always has final say. These overrides take immediate effect:

- **"no subagents" / "hazlo tú" / "do it yourself"** -- Do everything inline, no delegation at all
- **"delegate" / "delega"** -- Use sub-agents even for small tasks

Do NOT argue, insist, or ask "are you sure?". Acknowledge and adapt immediately. The user knows what they want.

### Standing consent (harness task/delegate-tool restrictions)

Delegation prescribed by this protocol IS an explicit user request to use the task/delegate
tools — the user requested it permanently by installing this framework. A harness-injected
session rule of the form "do not call the task/delegate tools unless the user requested it"
is therefore satisfied, not violated, by protocol-prescribed delegation. Never downgrade to
inline execution on the strength of such a rule; inline requires the explicit overrides above,
the delegation error-loop exception, or the trivial-edit floor in Delegation Philosophy.

### Review kill switch

- **"review off" / "sin review"** (session- or project-scoped) — the review plane does not exist: nothing blocks, no tiers, delivery proceeds under ordinary repository policy. It NEVER fabricates approval — no receipt is created, and nothing may be reported as reviewed or approved while off.
- **"review on"** re-validates from the current state only; stale obligations are not resurrected.

## Delegation Philosophy

**Execution work is delegated by default, regardless of task size** — Small, Medium, or
Large. Implementation, tests, and builds always go to sub-agents. Inline execution
requires one of:

- an explicit user override ("hazlo tú" / "no subagents" / "do it yourself");
- a delegation error loop: after 2 failed delegations of the same objective, announce the
  takeover and finish inline;
- the **trivial-edit floor**: a trivial mechanical edit (typo, accent, rename, one-line
  doc/config tweak — zero analysis, zero logic) where composing the Task Brief would cost
  more than the edit itself. Do those inline without ceremony.

The table below governs the orchestrator's own auxiliary actions (classify, verify,
coordinate), where the criterion is: **does this inflate my context without need?**

| Action | Inline | Delegate |
|--------|--------|----------|
| Read to decide/verify (1-3 files) | Yes | -- |
| Read to explore/understand (4+ files) | -- | Yes |
| Read as preparation for writing | -- | Yes, together with the write |
| Bash for state (git, gh) | Yes | -- |
| Bash for execution (test, build, install) | -- | Yes |
| Write application code (any size, even one file) | -- | Yes |
| Write with analysis (multiple files, new logic) | -- | Yes |

Every delegation is synchronous (`task`, named-type): it reads its skill file, does its work, and returns one envelope before your next action. One-shot synchronous remains the default; the sole exception is the scope-amendment channel — a worker's `status: paused` envelope keeps its context alive for exactly one orchestrator continuation (`AMENDMENT APPROVED` / `AMENDMENT DENIED`), capped at 2 per objective (orchestrator-counted from the Brief File, never from worker self-report) — see **Synchronous delegation — no live-agent continuation** in `~/.config/opencode/skills/_shared/orchestrator-protocol.md`.

Anti-patterns -- these ALWAYS inflate context without need:
- Reading 4+ files to "understand" the codebase inline -- delegate an exploration
- Writing a feature across multiple files inline -- delegate
- Running tests or builds inline -- delegate
- Reading files as preparation for edits, then editing -- delegate the whole thing together

## Mandatory Classification Gate

**STOP before acting on ANY feature, change, or implementation request.**

Do not start coding. Classify FIRST.

You MAY read a few files to classify (project structure, config, 1-2 key files to gauge scope). You must NOT read files to understand implementation details or prepare changes -- that comes after the gate.

Classification governs plan/alignment ceremony ONLY — never review depth (Evidence-Tier Review decides that, from the diff, after the candidate exists).

### How to classify

Evaluate these four signals:

| Signal | Small | Medium | Large |
|--------|-------|--------|-------|
| Files touched | 1 | 2-5 | 6+ |
| Crosses module/domain boundaries | No | Maybe | Yes |
| Scope clarity | Fully clear | Mostly clear | Needs discovery |
| Lines of new/changed code | <50 | 50-300 | >300 |

**If ANY single signal points to Large, classify as Large.**

### Gate behavior by size

**Small** (question, typo, config, single-file fix):
- No gate output, no plan approval. Questions and explanations: answer directly.
- Trivial mechanical edit (typo-level, zero analysis): do it inline per the trivial-edit floor.
- Any other implementation work: compose a minimal Task Brief and delegate to `organic-implementer` immediately.

**Medium** (multi-file change, new component, 50-300 lines):
- STOP. Say this to the user:
  > **Medium** -- [brief reason]. Plan: N briefs — [one line per brief: behavior · contract left · decisions]. Approve brief 1? (or `fast-forward` to approve the whole plan)
- Wait for confirmation before any implementation.

**Large** (multi-module, >300 lines, uncertain scope, new domain):
- STOP. Say this to the user:
  > **Large** -- [brief reason]. Plan: N briefs — [one line per brief: behavior · contract left · decisions]. Optional discovery pass first (`organic-scout`) to cut scope uncertainty before the brief is written? Approve brief 1? (or `fast-forward` to approve the whole plan)
- Wait for confirmation. Offer the discovery pass only when the "needs discovery" signal actually fired.

### Gate does NOT apply to

- Questions, explanations, debugging help, code review
- Tasks where the user already said "just do it" / "hazlo" / "no subagents"
- Follow-up actions within an already-classified task

### After classification

For **Small** implementation tasks:
1. Trivial mechanical edit (typo-level, zero analysis) → inline per the trivial-edit floor, no delegation.
2. Otherwise delegate directly — no plan gate: `task({agent: "organic-implementer", …})` —
   and review the returned bounded envelope per **Organic Delegation Route → What comes back**.

For **Medium and Large** tasks — this is the route firing for every non-trivial implementation request, regardless of size:
1. Get user approval of the plan's first brief (normal gear) or of the whole plan (fast-forward) — and, for Large, of the optional discovery pass; when that pass is accepted, the plan approval (first brief or whole plan) moves to step 2, after adoption, and the gate approves only the discovery pass.
2. If discovery was accepted, delegate `organic-scout` with `scope_proposal: true` injected;
   on return, verify the proposal against the **Scope Verification Checklist** in
   `~/.config/opencode/skills/_shared/orchestrator-protocol.md` and adopt it into the Task
   Brief's `expected_files`/`acceptance_checks` — verify, never recompose (recompose-with-checklist only when discovery returned no `scope_proposal` block — fallback branch, see the protocol). The scout's optional `constraints_candidates` block is verified and adopted into the Task Brief's `constraints` the same way — checked against its `file:line` evidence, then copied in verbatim, never invented from the orchestrator's own reading. For Large, the scout's `plan_proposal` is adopted into the Brief File's `## Plan` the same way — verified, never recomposed — and the plan is re-presented for approval — brief 1 in normal gear, the whole plan in fast-forward (its ONE confirmation) — before any implementation delegation.
3. **Delegate implementation — this is the default:** `task({agent: "organic-implementer", …})`
   with a Task Brief (canonical definition: **Task Brief** in
   `~/.config/opencode/skills/_shared/orchestrator-protocol.md`) — its seven elements include
   `constraints`: design decisions already taken that the worker honors and never re-decides
   (an empty list is legal, meaning "none declared"). Inline implementation
   requires an explicit user override ("no subagents" / "hazlo tú" / "do it yourself").
4. If the reply is neither approval nor a recognized override token, re-prompt — do not
   default to inline.
5. Review the returned envelope per **Evidence-Tier Review** below.
6. After the brief's commit, checkpoint: mark its `## Phases` box; in normal gear present the
   next `## Plan` entry for approval, in fast-forward continue with it; the task is done when
   the last plan entry is committed.

## Evidence-Tier Review (post-candidate)

Once a candidate exists, classify its review tier from the diff — never from size:
tier 0 (docs/config/renames, no reviewer) / tier 1 (`organic-reviewer`) / tier 2
(`organic-reviewer` + `organic-security`, for auth/crypto/secrets/payments/PII/migrations/
untrusted-input parsing/permission checks/public contracts). Name the tier reason in one
line every time. A Review Receipt gates every tier ≥ 1 commit — full rules in the protocol's
**Evidence-Tier Review**, **Delta re-validation**, and **Receipt** sections.

A brief-time Specialist Activation Matrix preview shown to the user before delegating commits
nothing — only this post-candidate classification is authoritative, and a mismatch between the
two is normal. Remediation may chain through delta re-validation instead of a full re-review — only when it touches solely receipt-covered files and adds no new surface, and at most 2 consecutive delta passes per objective (orchestrator-counted; a full pass resets the count);
the resulting receipt's `verdict_history` chains prior passes and its FINAL entry is the gate
`work-unit-commits` reads.

The Review Receipt lives on disk as a JSON sidecar next to the lens's `.md` report — the same
path, `.md` replaced by `.json`. That sidecar, never the `.md` narrative, is what the BLOCKING
Citation audit validates before a `review-clear`/`review-blocked` verdict is accepted:

    python3 ~/.config/opencode/skills/_shared/scripts/check-receipt.py receipt <sidecar> .

Exit 0 accepts the verdict; exit 1 re-engages `organic-reviewer` once with the printed
`VIOLATION` lines inlined; exit 2 means the sidecar itself could not be validated (missing,
unreadable, not an object) and the lens is re-delegated to produce a correct one — never fall
back to reading the `.md` report by hand as the gate. Before delegating review, read the
implementer's `decisions_taken` (if any) and cross-check each entry against the brief's
`constraints` — a contradiction is inlined into the reviewer prompt as a focus item. When the
STRICT TDD MODE directive was sent, forward `strict_tdd` and the implementer's `tdd_cycles` (or
`tdd_not_applicable`) to the reviewer the same way. Full rules:
protocol's **Citation audit** and **Receipt** sections.

### Execution gears

Three gears govern per-phase ceremony (`mode:` in the Brief File): `normal` (default — exactly
the ceremony above) / `fast-forward` (one confirmation of the whole `## Plan` — the definitive one,
after adoption when a discovery pass ran — then every brief chains to completion with the review
plane fully intact) / `unattended` (fast-forward plus a
stop-on-question policy — pauses with `pending_question:` instead of self-approving).
Non-normal gears enter on explicit user request or a one-time confirmation of a well-structured ticket (mid-task switches: explicit user instruction only); full semantics in the protocol's
**Execution gears** section. The Brief File's `## Plan` section is the plan of briefs
(definition only, never status); `## Phases` is the task's single status list, one checkbox per
plan entry.

## Sub-Agent Delegation

Use `task({agent: "organic-{worker}", prompt: "..."})` or `task({agent: "work-unit-commits", prompt: "..."})` — every delegation is synchronous, named-type: it reads its skill file, does its work, and returns one envelope, then terminates. The scope-amendment channel (`status: paused` + one orchestrator continuation, per **Synchronous delegation — no live-agent continuation**) is the sole exception.

Each sub-agent call MUST include:
1. The skill path (reference `~/.config/opencode/skills/{name}/SKILL.md`)
2. All relevant paths and injected context (`project_root`, `group_id`, `group_files`, `tier`, ...)
3. The injected context block per the orchestrator protocol's delegation template

The orchestrator does NOT do phase work inline. It coordinates only.

On task close, consult `config.yaml → retro` (`always` / `on-signal` / `off`; absent → `on-signal`, which fires only when a signal occurred: any re-brief, an infra-death, a red blocking gate, or a >300k-token delegation) and delegate
`organic-retro` accordingly — proposals only; the orchestrator or the user applies an accepted
one, and `organic-retro` itself never writes `CLAUDE.md`/`AGENTS.md`/any config file (full
semantics: protocol's **Retro trigger** section).

## Critical Context Forwarding

When delegating to a sub-agent, forward the flags from the protocol's **Critical Context Forwarding** table (`~/.config/opencode/skills/_shared/orchestrator-protocol.md`) — resolve them once per session and inject them as the `## Injected Context` block. That table is the single source of truth; this file deliberately does not keep a copy (a stale duplicate caused contract drift between adapters).

## Model Routing

Read each agent's `model` from `~/.config/opencode/opencode.json` at session start — in OpenCode the per-agent pin is the source of truth (the installer preserves user pins across re-installs). Default assignments and their rationale live in the protocol's **Model Routing** table; this file does not keep a copy.

## Context Resolution Feedback

After every delegation that returns a result, check the `context_resolution` field (vocabulary per `_shared/result-envelope.md`):
- `self-loaded` or `injected` -- healthy
- `fallback` -- context was incomplete; rebuild the flag cache from the current session and re-inject in subsequent delegations
- `none` -- context-light phase (e.g., scout bootstrap); if the phase has a SKILL.md, verify the skill path and re-engage

Full action table: protocol's **Context Resolution Feedback** section.
