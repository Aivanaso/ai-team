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

## Edge Case 5 — Project skill contradicts the default composition rule

**Scenario:** The project's `commit/SKILL.md` specifies a scope format or type taxonomy that conflicts with the default rule in Hard Rules.

**Resolution rule:**
- Project skill wins for the fields it explicitly addresses.
- The default rule remains the floor for fields the project skill does not address (e.g., if the project skill overrides scope but says nothing about `Co-Authored-By`, the "no `Co-Authored-By`" rule still applies).
- Emit WARNING when an override is applied: `"Project commit skill override applied for field: {field} — value: {value}"`.

## Edge Case 6 — Manual mode + user runs commands later

**Scenario:** Mode is `manual`. work-unit-commits returns `manual_commit` instructions. The user runs the commands later (not immediately). Meanwhile, another delegation touches the repository.

**Behaviour during skill execution:**
- Envelope `status: ok`, `mode: manual`, `manual_commit: { message, files, commands }`.
- No persistent artifact is updated by this skill — the route's state file (the orchestrator's Brief File) is orchestrator-authored, so work-unit-commits marks nothing "pending" on disk.

**After user commits:**
- The user is responsible for running the provided `commands` in the listed order.
- Tracking that the manual commit landed is the orchestrator's or user's responsibility (e.g., a follow-up `git log` check) — work-unit-commits has no on-disk record to reconcile against.

## Edge Case 7 — Receipt gate outcomes

**Scenario:** the delegation prompt's tier/receipt context determines whether the gate blocks before any git command runs (Hard Rules, Decision Gates). Four outcomes, all evaluated at Step 2 before Step 3 ever reads `config.yaml`:

| Injected context | Behaviour |
|---|---|
| `tier >= 1` declared, no Review Receipt present | `status: blocked`, reason: "tier {N} candidate missing its review receipt". No git command runs. |
| Neither a `tier` nor a "review off" declaration present | `status: blocked`, reason: "no tier declaration and no review-off declaration — cannot determine the commit gate". An undeclared tier never defaults to tier 0. |
| Review Receipt present with `verdict: review-blocked` and no entry in `overrides` | `status: blocked`, reason: "review-blocked with no recorded override". A receipt with a recorded override clears the gate normally. |
| `tier: 0`, or an explicit "review off" declaration | Proceed to commit under ordinary policy — no receipt required, no gate evaluation beyond confirming the declaration itself. |

**Resolution for the three blocked rows:** the orchestrator either supplies the missing declaration/receipt and re-invokes, or the user records an override in the receipt and the orchestrator re-invokes with it. work-unit-commits never infers a tier or a receipt on its own — see [references/envelope-examples.md](references/envelope-examples.md) for the exact envelope shape of each outcome.
