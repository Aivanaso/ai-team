# Verification Report Format — sdd-verify

> Load when writing `verification-report.md`. This is the full report template.

````markdown
# Verification Report: {Change Name}

> Verified on {YYYY-MM-DD}. Verdict: **{PASS / PASS WITH WARNINGS / FAIL}**.

## Summary

| Check | Verdict | Details |
|-------|---------|---------|
| File inventory | {verdict} | {N}/{total} files verified |
| Compilation | {verdict} | {summary} |
| Lint | {verdict} | {summary} |
| New tests | {verdict} | {passed}/{total} |
| Regression check | {verdict} | {summary} |
| Task criteria | {verdict} | {met}/{total} criteria |
| Static correctness | {verdict} | {N}/{total} requirements structurally verified |
| Design coherence | {verdict} | {N}/{total} decisions followed |
| Behavioral compliance | {verdict} | {N}/{total} scenarios compliant |
| Drift summary | {verdict} | {N} approved decisions, {M} unaccounted files |
| AC coverage | {verdict} | {covered}/{total} ACs |

## File Inventory

| Task | File | Expected | Actual | Verdict |
|------|------|----------|--------|---------|
| 1.1 | `path/to/file.ts` | CREATE | exists | PASS |
| 2.1 | `path/to/old.ts` | REMOVE | removed | PASS |

### Scope Creep

{Files changed outside task plan, or "None detected."}

## Build

### Compilation

```
{command}
{output or "Exit 0 -- no errors"}
```

### Lint

```
{command}
{output or "Exit 0 -- clean" or "SKIP -- no lint configured"}
```

## Tests

### New Tests

| File | Tests | Passed | Failed |
|------|-------|--------|--------|
| `path/to/new.spec.ts` | 4 | 4 | 0 |

### Regressions

{Failing tests with error output, or "None -- all existing tests pass."}

## Task Criteria

### Task 1.1: {Name}

- [x] Files compile without errors -- `tsc exited 0`
- [x] {criterion} -- {evidence}
- [ ] {criterion} -- **{reason for failure}**

## Static Correctness

| Requirement | Status | Evidence |
|-------------|--------|----------|
| REQ-{DOMAIN}-{NNN}: {title} | Implemented | `file.ts:functionName` handles all scenarios |
| REQ-{DOMAIN}-{NNN}: {title} | Partial | {what's missing} |
| REQ-{DOMAIN}-{NNN}: {title} | Missing | {not found in codebase} |

## Design Coherence

| Decision | Followed? | Notes |
|----------|-----------|-------|
| {Decision from design.md} | Yes | |
| {Decision from design.md} | Deviated | {how and why} |

## Behavioral Compliance

### REQ-{DOMAIN}-{NNN}: {Title}

| Scenario | Test | Result |
|----------|------|--------|
| Given X, When Y, Then Z | `test-file.spec.ts > test name` | COMPLIANT |
| Given A, When B, Then C | (none found) | UNTESTED |
| Given D, When E, Then F | `test-file.spec.ts > test name` | FAILING |

**Compliance summary**: {N}/{total} scenarios compliant, {N} partial, {N} untested, {N} failing

## Spec Compliance Matrix

> Produced per logical group when tasks.md has >1 group (REQ-VERIFY-006).

### Group G1: {Group Name}

| REQ-ID | Scenario | State | Evidence |
|--------|----------|-------|---------|
| REQ-FOO-001 | Given … When … Then … | COMPLIANT | "describe > it" PASS |
| REQ-FOO-002 | Given … When … Then … | FAILING | "describe > it" FAIL |
| REQ-BAR-001 | Given … When … Then … | UNTESTED | no test found |

## Drift Summary

### Approved Drift (from `state.yaml` `decisions:`)

| Phase | Task ref | Decision | Reason | Evidence | Commits |
|-------|----------|----------|--------|----------|---------|
| {phase} | {task_ref} | {one-line decision} | {one-line reason} | {evidence ref} | {SHAs} |

{Or: "No mid-flight decisions logged."}

### Unaccounted Drift

{List of files in `git diff` that are NEITHER in any task's file list NOR referenced by any `decisions:` entry. One line per file with recommendation: add retroactive entry, or revert. Or: "None -- all changes either match the task plan or are logged as approved drift."}

### Absorbed Checks Summary

| Check | Status | Finding |
|-------|--------|---------|
| Check 1 — Diff vs declared scope | PASS / WARNING / CRITICAL | {count} undeclared files or "clean" |
| Check 2 — Resolution coverage | PASS / WARNING | {count} unresolved decision keywords or "clean" |
| Check 3 — Audit-trail completeness | PASS / CRITICAL | {count} fix commits vs decisions[] entries or "clean" |
| Check 4 — Test discovery sanity | PASS / WARNING / SKIPPED | {note} |

## AC Coverage

| AC | Status | Evidence |
|----|--------|----------|
| AC-01 | COVERED | REQ-X-001 Implemented + Compliant |
| AC-02 | PARTIAL | REQ-Y-001 Partial -- scenario 3 untested |

## Issues

### CRITICAL (must fix before archive)

{Numbered list, or "None."}

1. {description} -- affects {task/req}

### WARNING (should fix)

{Numbered list, or "None."}

1. {description} -- affects {task/req}

### SUGGESTION (nice to have)

{Numbered list, or "None."}

1. {description}

## Verdict

**{PASS / PASS WITH WARNINGS / FAIL}**

{1-2 sentence justification.}

**Recommendation:** {Proceed to archive / Re-run apply for tasks {IDs} / Review issues with user}

## Re-engage Routing Hint

**failure_class:** `implementation` | `test_contract` | `spec_gap` | null
**failed_groups:** [`G1`, `G2`]
**Rationale:** {one sentence explaining the dominant failure cause}

Orchestrator routing: implementation → re-engage sdd-apply; test_contract → re-engage sdd-tasks; spec_gap → escalate to user.
````
