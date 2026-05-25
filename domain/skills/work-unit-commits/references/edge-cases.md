# Edge Cases — work-unit-commits

> Load-on-demand reference for unusual conditions during commit creation.

## Edge Case 1 — Pre-commit hook reject

**Scenario:** `git commit` fails because a pre-commit hook (e.g., eslint, prettier, husky) rejects the staged files.

**Behaviour:**
- Return `status: failed` with the git output in `risks:` (the orchestrator handles retry decisions, per REQ-WUC-003).
- Propose re-running after the hook issue is resolved. The `--no-verify` flag bypasses safety checks and is prohibited by project convention.

**Resolution:** The orchestrator surfaces the failure to the user, who fixes the issue and triggers a fresh work-unit-commits invocation.

## Edge Case 2 — File missing on disk (apply deliverables audit gap)

**Scenario:** A file listed in a task's `Files:` block was supposed to be created by sdd-apply but does not exist on disk.

**Behaviour:**
- Emit WARNING: `"Declared file {path} not found on disk — sdd-apply deliverables audit gap"`.
- Skip staging that file.
- Proceed with committing the files that do exist.
- Set envelope `status: warning` (not `ok`).

**Note:** This condition indicates sdd-apply had a partial delivery. The warning propagates to sdd-verify for authoritative ruling.

## Edge Case 3 — Merge conflict

**Scenario:** `git commit` fails due to a merge conflict (unresolved markers in staged files).

**Behaviour:**
- Return `status: blocked` with the conflict details; the orchestrator decides whether to re-engage sdd-apply or request human resolution.

## Edge Case 4 — Undeclared file in working tree

**Scenario:** `git diff --name-only HEAD` shows a modified file that is NOT in any task's `Files:` block for this group.

**Behaviour:**
- Stage only the declared files; emit WARNING for the undeclared file with its path (REQ-WUC-006).
- Emit WARNING: `"Undeclared file {path} in working tree diff — not staged. Likely a side effect from a previous group or a scope creep indicator."`.
- Proceed with committing only declared files.
- Orchestrator should note this for Post-Apply Audit (REQ-ORCHESTRATOR-009 Check 1).

## Edge Case 5 — Project skill contradicts REQ-WUC-005 defaults

**Scenario:** The project's `commit/SKILL.md` specifies a scope format or type taxonomy that conflicts with REQ-WUC-005 defaults.

**Resolution rule (REQ-WUC-008):**
- Project skill wins for the fields it explicitly addresses.
- REQ-WUC-005 remains the floor for fields the project skill does not address (e.g., if project skill overrides scope but says nothing about Co-Authored-By, the REQ-WUC-005 "no Co-Authored-By" rule still applies).
- Emit WARNING when an override is applied: `"Project commit skill override applied for field: {field} — value: {value}"`.

## Edge Case 6 — Manual mode + user runs commands later

**Scenario:** Mode is `manual`. work-unit-commits returns `manual_commit` instructions. The user runs the commands later (not immediately). Meanwhile, another SDD or operation touches the repository.

**Behaviour during skill execution:**
- skill sets `state.yaml.phases.apply.commits[{group_id}] = "manual-pending"`.
- Envelope `status: ok`, `mode: manual`, `manual_commit: { message, files, commands }`.
- The `decisions[]` backfill for this group's tasks is NOT done (no SHA yet).

**After user commits:**
- The user is responsible for running the provided `commands` in the listed order.
- `state.yaml` remains `"manual-pending"` until the orchestrator or user updates it with the actual SHA.
- sdd-verify will detect `"manual-pending"` and note it as informational (not a blocker) since verify's scope is content compliance, not commit mechanics.
