# Edge Cases — sdd-reviewer

## Edge Case 1: No Group Changes to Review

**Condition:** `group_files` is empty, or none of the declared files exist on disk (and `git diff HEAD -- <group_files>` also shows no changes to tracked files).

**Behavior:** Return `status: ok`, `verdict: review-clear`, `findings: []`. Note in executive summary: "no group changes to review for group {group_id} — gate passes with no findings". Set `suppressed_count: 0`.

Rationale: an empty change set is a valid state (e.g., files were declared in tasks.md but apply did not need to touch them, or the changes were reverted). The gate must not block on a clean slate.

## Edge Case 2: All Findings Below 80% Confidence

**Condition:** Every finding identified across all four correctness lenses has confidence ≤ 80%.

**Behavior:** Suppress all findings. Return `status: ok`, `verdict: review-clear`, `findings: []`. Set `suppressed_count` to the total number of suppressed findings. Note in executive summary: "All {N} candidate findings suppressed — confidence below threshold."

Rationale: false positives train users to override reflexively, defeating the gate's purpose. A clean report with a non-zero `suppressed_count` is an accurate signal that the review ran and found only low-confidence candidates.

## Edge Case 3: Missing group_files (not injectable, not derivable)

**Condition:** `group_files` is absent from injected context AND not derivable from `tasks.md` `Files:` blocks for `group_id` (e.g., tasks.md is also missing or the group has no File entries).

**Behavior:** Return `status: blocked`, executive summary names the missing field. Do NOT attempt to review a broader scope (e.g., all changed files). Wait for the orchestrator to re-inject the correct context.

Rationale: reviewing files outside the declared group scope would produce findings the orchestrator cannot route to the correct tasks, and could block a commit for a group that had no defects.

## Edge Case 4: Large File Set (read budget)

**Condition:** The union of `group_files` contains more files than can be read in one context window alongside 1-hop callers.

**Behavior:** Read files in declaration order from `tasks.md` `Files:` blocks until the budget is reached. Prioritise the CREATE files over MODIFY files (new code is more likely to have defects than lightly touched existing code). Note in the report's `## Diff Scope` section: "read budget reached after {N}/{total} files; {M} files not reviewed". Set `suppressed_count` to 0 for unreviewable files (they were not reviewed, not suppressed). Return the partial verdict.

Rationale: a partial review with a transparent scope note is more useful than a blocked run. The orchestrator can decide whether to retry with a narrower group.
