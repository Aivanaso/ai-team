# tasks.md Template

Use this template verbatim when writing `.ai-team/changes/{change-name}/tasks.md`.

---

```markdown
# Tasks: {Change Name}

> Implementation plan for {change summary}. {N} tasks across {M} groups.

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | {N} |
| Groups | {M} |
| New files | {count} |
| Modified files | {count} |
| Removed files | {count} |
| Requirements covered | {count} REQs across {N} domains |
| Acceptance criteria covered | {count}/{total} ACs |

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Features identified | {count} independent feature(s) |
| Cohesion risk | {Low | Medium | High} |
| PR slices suggested | {single PR | PR 1 → PR 2 → PR 3} |
| Estimated changed lines | {rough estimate per feature, e.g. "feature-A ~250, feature-B ~400"} |

The following plain-text lines are the **grep contract** that downstream guards (sdd-apply,
orchestrator) MUST be able to match literally. Keep them verbatim, in this exact order:

```text
Cohesion risk: Low|Medium|High
Independent PRs: <count> independent / <count> chained
Decision needed before apply: Yes|No
```

Optional fourth line, emitted **only** when a single feature exceeds ~800 estimated lines
(size smell, not auto-split):

```text
Size smell: <feature-name> (<N> lines)
```

Emit one `Size smell:` line per feature that crosses the threshold. Omit entirely when no
feature triggers it. `Decision needed before apply` is `Yes` when cohesion risk is High
and no slice plan is set, otherwise `No`.

### Suggested PR Slices

Omit this table when there is a single PR (one feature, no chained dependencies).

| Slice | Feature | Groups | Estimated lines |
|-------|---------|--------|-----------------|
| PR 1 | {feature name — independent deliverable} | Group 1 | {rough} |
| PR 2 | {feature name — independent deliverable} | Groups 2-3 | {rough} |

## Execution Order

| # | Task | Group | PR Slice | Files | Depends On | Status |
|---|------|-------|----------|-------|------------|--------|
| 1.1 | {task name} | {group name} | PR 1 | {count} | — | pending |
| 1.2 | {task name} | {group name} | PR 1 | {count} | — | pending |
| 2.1 | {task name} | {group name} | PR 2 | {count} | 1.1 | pending |
| ... | | | | | | |

When the change is a single independent feature (no chained PRs), the `PR Slice` column
may be filled with `single PR` for every row.

## Group 1: {Group Name}

> {One-line description of what this group accomplishes}
> **PR Slice**: PR 1 (or "shared with Group 2", or "single PR")

### Task 1.1: {Task Name}

**Files:**

| Action | Path |
|--------|------|
| CREATE | `{path/to/file.ts}` |
| CREATE | `{path/to/file.spec.ts}` |

**Description:**

{2-3 sentences describing what this task does and why it matters in the execution sequence.}

**Implementation Notes:**

{Key details from the design — interfaces, signatures, patterns to follow. Enough for
sdd-apply to implement without reading the full design.}

```{language}
// Key interface or type from design — signatures, not full implementation
{relevant type definition or method signature}
```

**Test Guidance:**

- {What to test from the design's Test Strategy}
- {Edge cases to cover}

**Requirements:** {REQ-DOMAIN-NNN}, {REQ-DOMAIN-NNN}
**ACs:** {AC-N}, {AC-M}
**Depends on:** —

**Verification:**

- [ ] Files compile without errors
- [ ] {Specific test or behavioral check}

---

### Task 1.2: {Next Task}

...

## Group 2: {Group Name}

> {One-line description}

...

## Traceability Matrix

| AC | Requirements | Tasks |
|----|-------------|-------|
| AC-01 | REQ-CLAIMS-001 | 1.1, 2.1, 3.1 |
| AC-02 | REQ-CLAIMS-002 | 2.1 |
| ... | | |

## AC↔Test Traceability

| REQ-ID | test_file | test_id |
|--------|-----------|---------|
| REQ-XXX-001 | path/to/test.spec.ts | "describe block name > it block name" |

## Manual Review Checklist

> Used only when `config.yaml.stack.testing: []` (meta-project path per REQ-TASKS-020).

| Criterion ID | REQ-ID covered | Bash command | Expected result | Maps to |
|---|---|---|---|---|
| C-001 | REQ-APPLY-021 | `grep -nE 'git [a-z]' domain/skills/sdd-apply/SKILL.md \| grep -vE 'git (diff --name-only\|status --porcelain)'` | exit 1 (zero matches) | COMPLIANT if exit 1; FAILING otherwise |

## Drift Warnings

{Any discrepancies found between the design and current codebase. Empty if none.}

- {Warning: file X referenced in design was modified since design phase}
- None.
```
