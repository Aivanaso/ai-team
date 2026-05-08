# Edge Cases — sdd-tasks

## Trivial Change

If the design has fewer than 5 components and all are straightforward:

- Still produce tasks.md, but with a single group.
- Tasks can be as few as 2-3.
- Omit the Traceability Matrix if there are fewer than 3 ACs.
- Set result envelope note: "Minimal task plan — change is straightforward."

## Massive Change (20+ Tasks)

If the task count exceeds 20:

- Flag a risk in the result envelope: "Large task plan ({N} tasks). Consider whether the
  proposal should be split into smaller changes."
- Group aggressively — merge small tasks where compilability allows.
- Still produce the full plan (do not block — the user decides).

## Design Without Delta Specs

If delta specs don't exist (design ran in parallel with spec, or spec was skipped):

- Proceed using the proposal's ACs directly for traceability.
- Note in the Traceability Matrix header: "Traced to ACs directly — delta specs not available."
- Map tasks to ACs instead of REQs.
- This is valid but produces weaker traceability.

## Design Drift Detected

If Step 2 reveals that files have changed since the design:

- **Minor drift** (cosmetic changes, new unrelated files): Note in Drift Warnings, proceed
  normally.
- **Moderate drift** (file renamed, method signature changed): Note in Drift Warnings, adjust
  task description to match current code.
- **Severe drift** (file deleted, module restructured): Return `status: warning` with risk
  explaining what changed. Still produce tasks for non-affected parts if possible.

## No Test Strategy in Design

If the design omits a Test Strategy section:

- Do NOT invent a test strategy.
- Each task gets "Files compile without errors" as the minimum verification criterion.
- Add a risk to the result envelope: "Design has no test strategy — tasks lack test guidance."

## Circular Dependencies Between Tasks

If task A needs code from task B, and task B needs code from task A:

- This usually means the grouping is wrong. Try merging the tasks.
- If they are genuinely separate concerns, create a shared types/interfaces task that both
  depend on.
- Never leave a circular dependency in the task plan — sdd-apply processes sequentially.
