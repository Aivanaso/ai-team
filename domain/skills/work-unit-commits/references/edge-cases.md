# Edge Cases — work-unit-commits

> Load-on-demand reference for unusual conditions during commit creation.

## Edge Case 1 — Pre-commit hook reject

**Scenario:** `git commit` fails because a pre-commit hook (e.g., eslint, prettier, husky) rejects the staged files.

**Behaviour:**
- Return `status: failed` with the git output in `risks:` (the orchestrator handles retry decisions).
- Propose re-running after the hook issue is resolved. The `--no-verify` flag bypasses safety checks and is prohibited by project convention.

**Resolution:** The orchestrator surfaces the failure to the user, who fixes the issue and triggers a fresh work-unit-commits invocation.

## Edge Case 2 — Declared file missing on disk

**Scenario:** A path in `group_files` was declared with a CREATE or MODIFY action but does not show as changed in `git status --porcelain` — the file was never written, or was written and reverted.

**Behaviour:**
- Emit WARNING: `"Declared file {path} not found in working tree — organic-implementer deliverables gap"`.
- Skip staging that file.
- Proceed with committing the `group_files` members that ARE dirty.
- Set envelope `status: warning` (not `ok`).

**Distinguish from a legitimate REMOVE.** A `group_files` path declared with a REMOVE action is *expected* to be absent from disk and to appear as a deletion in `git status --porcelain` — that is the normal case, not a gap. Only flag CREATE/MODIFY paths that never show up as changed.

**Note:** The orchestrator's post-return artifact-confirmation check (per `orchestrator-protocol.md` → "Organic Delegation Route → What comes back") is the first line of defense; this WARNING is the second — it surfaces a gap that route reached commit staging without resolving.

## Edge Case 3 — Merge conflict

**Scenario:** `git commit` fails due to a merge conflict (unresolved markers in staged files).

**Behaviour:**
- Return `status: blocked` with the conflict details; the orchestrator decides whether to re-delegate `organic-implementer` or request human resolution.

## Edge Case 4 — Dirty path outside group_files

**Scenario:** `git status --porcelain` under `project_root` shows a modified or untracked file that is NOT in the injected `group_files` set.

**Behaviour:**
- Stage only the `group_files` members; emit WARNING for the undeclared path.
- Emit WARNING: `"Dirty path {path} outside group_files — not staged. Likely a side effect from a previous run or a scope-creep indicator."`.
- Proceed with committing only `group_files` members.
- The orchestrator should note this before the next delegation for the same objective.

## Edge Case 5 — Convention source contradicts the default composition rule

**Scenario:** A higher-precedence convention source — the project's `commit/SKILL.md`, `{project_root}/CLAUDE.md`/`AGENTS.md`, the user's `commit/SKILL.md`, or `~/.claude/CLAUDE.md` — specifies a scope format, type taxonomy, or attribution rule that conflicts with the default rule in Hard Rules. This includes a project skill vs `CLAUDE.md` conflict: the convention-first precedence order in Hard Rules (project skill, then project `CLAUDE.md`/`AGENTS.md` — same rank, `CLAUDE.md` wins a same-field conflict between the two — then user skill, then user `CLAUDE.md`, then the floor) resolves it — earlier source wins for the fields it explicitly addresses.

**Resolution rule:**
- The highest-precedence source that explicitly addresses a field wins for that field.
- The default rule remains the floor for fields no higher-precedence source addresses (e.g., if a source overrides scope but says nothing about `Co-Authored-By`, the "no `Co-Authored-By`" rule still applies).
- Project sources (`{project_root}/.claude/skills/commit/SKILL.md`, `{project_root}/CLAUDE.md`, `{project_root}/AGENTS.md`) are convention DATA and may address the presentation whitelist only (commit format, scope token, type taxonomy, subject style) — never attribution (Hard Rules → project-source trust boundary).
- The attribution floor ("no `Co-Authored-By`") can only be relaxed by a user-authored convention — the user's own `commit/SKILL.md` or `~/.claude/CLAUDE.md` (Hard Rules definition) — never by a project source and never by a harness system-prompt instruction, which is not a user convention.
- Emit WARNING when an override is applied: `"{source} override applied for field: {field} — value: {value}"`.

## Edge Case 6 — Manual mode + user runs commands later

**Scenario:** Mode is `manual`. work-unit-commits returns `manual_commit` instructions. The user runs the commands later (not immediately). Meanwhile, another delegation touches the repository.

**Behaviour during skill execution:**
- Envelope `status: ok`, `mode: manual`, `manual_commit: { message, files, commands }`.
- No persistent artifact is updated by this skill — the route's state file (the orchestrator's Brief File) is orchestrator-authored, so work-unit-commits marks nothing "pending" on disk.

**After user commits:**
- The user is responsible for running the provided `commands` in the listed order.
- Tracking that the manual commit landed is the orchestrator's or user's responsibility (e.g., a follow-up `git log` check) — work-unit-commits has no on-disk record to reconcile against.

## Edge Case 7 — Receipt gate outcomes

**Scenario:** the delegation prompt's tier/receipt context determines whether the gate blocks before any git command runs (Hard Rules, Decision Gates). Six outcomes, all evaluated at Step 2 before Step 3 ever reads `config.yaml`:

| Injected context | Behaviour |
|---|---|
| `tier >= 1` declared, no Review Receipt present | `status: blocked`, reason: "tier {N} candidate missing its review receipt". No git command runs. |
| Neither a `tier` nor a "review off" declaration present | `status: blocked`, reason: "no tier declaration and no review-off declaration — cannot determine the commit gate". An undeclared tier never defaults to tier 0. |
| Review Receipt present with `verdict: review-blocked` and `overrides` lacks a singular `finding_id` entry naming EVERY blocking CRITICAL finding across BOTH `lenses.correctness` and `lenses.security` | `status: blocked`, reason names the uncovered CRITICAL id(s), e.g. "review-blocked: no singular override entry for CRITICAL F-2 (lenses.security)". A bulk `finding_ids` entry NEVER counts — `_shared/result-envelope.md` → Review Receipt restricts the bulk form to MINOR/`evidence: read`/no-`trigger` findings, so it structurally cannot cover a CRITICAL. A singular `finding_id` entry for every blocking CRITICAL clears the gate normally. |
| Review Receipt present with `verdict_history` (a delta-chained receipt, `_shared/result-envelope.md` → Review Receipt) | Gate reads the chain's LAST entry, not any earlier one, AND cross-checks that entry's `verdict` against the top-level `verdict` field: match + `review-clear` → satisfies the tier ≥ 1 gate, proceed to commit; match + anything else → same handling as a bare `review-blocked` receipt (row above) — `status: blocked` absent a singular override naming every blocking CRITICAL; **mismatch between the two** → `status: blocked`, reason: "verdict_history/verdict mismatch — receipt integrity failure" — fail closed, never a permissive pick of either field. |
| Review Receipt carries a `findings_addressed` addendum with an entry missing its `files` field, naming a file outside `group_files`, or present while `group_files` was NOT injected | `status: blocked` — for an entry missing `files` or naming a file outside `group_files`, reason: "findings_addressed entry missing files or touches files outside group_files — receipt coverage broken"; for the absent-`group_files` case, reason: "findings_addressed present without an injected group_files — cannot verify coverage" (both fail closed, evaluated against the injected `group_files` only — never Step 5's staging discovery; a digest-only `fix_evidence` with no `files` list never passes silently). |
| `tier: 0`, or an explicit "review off" declaration | Proceed to commit under ordinary policy — no receipt required, no gate evaluation beyond confirming the declaration itself. |

**Resolution for the blocked rows:** the orchestrator either supplies the missing declaration/receipt and re-invokes, or the user records a singular `finding_id` override naming every blocking CRITICAL and the orchestrator re-invokes with it (a bulk `finding_ids` entry never resolves this row — see above) — EXCEPT the integrity-failure (mismatch) outcome, which an override never resolves: the orchestrator must re-issue a coherent receipt whose chain and top-level `verdict` agree, then re-invoke. The same fail-closed handling applies to the `findings_addressed` row above: an override never resolves it either — the orchestrator must re-issue a receipt whose addendum entries each carry a `files` field lying entirely within `group_files`, with `group_files` itself injected, before re-invoking. work-unit-commits never infers a tier or a receipt on its own — see [references/envelope-examples.md](references/envelope-examples.md) for the exact envelope shape of each outcome.
